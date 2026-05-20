"""
Complete RAGAS Evaluation with APIs
Uses Azure OpenAI for BOTH Judge and Embeddings
"""

import json
import sys
from datetime import datetime
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    context_recall,
    context_precision,
    faithfulness,
    answer_correctness
)

# ==========================================
# CONFIGURATION - EDIT THIS SECTION
# ==========================================

INPUT_FILE = "manual_test_cases.json"  # Your input file

# Azure OpenAI credentials (REQUIRED)
OPENAI_KEY = ""
OPENAI_ENDPOINT = ""
CHAT_MODEL = "gpt-4o-mini"  # Judge model
EMBEDDING_MODEL = "text-embedding-3-large"  # Embedding model

# ==========================================
# UTILITY FUNCTIONS
# ==========================================

""" Normalizes any value (None / list / string) into a clean, stripped string.
    Lists are joined with the given separator so RAGAS receives a single answer string.
"""
def convert_to_string(value, separator="\n"):
    """Convert array to string or keep as string"""
    if value is None:
        return ""
    
    if isinstance(value, list):
        return separator.join(str(item).strip() for item in value if item)
    
    return str(value).strip()


"""
Checks one test-case dict for required fields (question, contexts, answer, ground_truth)
and returns a normalized copy. Returns (is_valid, cleaned_item, error_message).
"""

def validate_item(item):
    """Validate and convert item"""
    param_name = item.get("param_name", "unknown")
    
    if not item.get("question"):
        return False, None, f"{param_name}: missing question"
    
    contexts = item.get("contexts", [])
    if not contexts or not isinstance(contexts, list):
        return False, None, f"{param_name}: missing contexts"
    
    # Convert list-form answers to a single string for RAGAS
    answer = convert_to_string(item.get("answer"))
    if not answer:
        return False, None, f"{param_name}: missing answer"
    
    # Same normalization for the reference (ground truth) answer
    ground_truth = convert_to_string(item.get("ground_truth"))
    if not ground_truth:
        return False, None, f"{param_name}: missing ground_truth"
    
    converted = {
        "param_name": param_name,
        "question": item.get("question"),
        "contexts": contexts,
        "answer": answer,
        "ground_truth": ground_truth
    }
    
    return True, converted, None




 """
 Orchestrates the full 8-step evaluation pipeline:
 validate creds -> load JSON -> validate items -> build Dataset ->
 init Azure judge & embeddings -> run RAGAS -> display -> save reports.
 """
def main():
    """Main evaluation function"""
    
    print("\n" + "="*80)
    print("RAGAS EVALUATION - WITH AZURE OPENAI APIs")
    print("="*80 + "\n")
    
    # ==========================================
    # STEP 1: VALIDATE CREDENTIALS
    # ==========================================
    
    print("STEP 1: VALIDATING AZURE CREDENTIALS")
    print("-" * 80)
    
    # Hard-fail early if Azure credentials weren't filled in at the top of the file
    if not OPENAI_KEY or not OPENAI_ENDPOINT:
        print("✗ ERROR: Azure credentials not set!")
        print("\nEdit the script and add your Azure credentials:")
        print("  OPENAI_KEY = 'your-azure-key'")
        print("  OPENAI_ENDPOINT = 'https://your-resource.openai.azure.com/'")
        print("\nFind them at: https://portal.azure.com → Your OpenAI Resource → Keys and Endpoint\n")
        sys.exit(1)
    
    print("✓ Azure credentials found")
    print(f"  Endpoint: {OPENAI_ENDPOINT[:50]}...")
    print(f"  Key: {OPENAI_KEY[:10]}...\n")
    
    # ==========================================
    # STEP 2: LOAD DATA
    # ==========================================
    
    print("STEP 2: LOADING INPUT FILE")
    print("-" * 80)
    print(f"File: {INPUT_FILE}\n")
    
    try:
        # Read and parse the test cases JSON file
        with open(INPUT_FILE, encoding="utf-8") as f:
            raw_data = json.load(f)
    except FileNotFoundError:
        print(f"✗ File not found: {INPUT_FILE}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"✗ Invalid JSON: {e}")
        sys.exit(1)
    
    # Top-level structure must be a JSON array (list of test-case dicts)
    if not isinstance(raw_data, list):
        print(f"✗ Expected list, got {type(raw_data).__name__}")
        sys.exit(1)
    
    print(f"✓ Loaded {len(raw_data)} items\n")
    
    # ==========================================
    # STEP 3: CONVERT & VALIDATE
    # ==========================================
    
    print("STEP 3: CONVERTING & VALIDATING DATA")
    print("-" * 80)
    print("Converting arrays to strings...")
    print("Validating fields...\n")
    
    prepared = []
    skipped = []
    
    # Run validate_item on every test case; collect valid ones, track skipped ones with reasons
    for item in raw_data:
        is_valid, converted_item, error_msg = validate_item(item)
        if is_valid:
            prepared.append(converted_item)
        else:
            skipped.append(error_msg)
    
    print(f"✓ Converted {len(prepared)} items")
    if skipped:
        # Show first 5 reasons items were skipped, plus a count of the rest
        print(f"⚠ Skipped {len(skipped)} items:")
        for skip in skipped[:5]:
            print(f"   - {skip}")
        if len(skipped) > 5:
            print(f"   ... and {len(skipped)-5} more\n")
    else:
        print()
    
    # Abort if nothing survived validation — RAGAS needs at least one valid sample
    if not prepared:
        print("✗ No valid items!")
        sys.exit(1)
    
    # ==========================================
    # STEP 4: CREATE DATASET
    # ==========================================
    
    print("STEP 4: CREATING RAGAS DATASET")
    print("-" * 80)
    
    # Build the HuggingFace Dataset object RAGAS expects:
    # one row per test case with exactly these four fields
    dataset = Dataset.from_list([
        {
            "question": item["question"],
            "contexts": item["contexts"],
            "answer": item["answer"],
            "ground_truth": item["ground_truth"]
        }
        for item in prepared
    ])
    
    print(f"✓ Dataset: {len(dataset)} samples")
    print(f"  Fields: question, contexts, answer, ground_truth\n")
    
    # ==========================================
    # STEP 5: INITIALIZE AZURE COMPONENTS
    # ==========================================
    
    print("STEP 5: INITIALIZING AZURE OPENAI COMPONENTS")
    print("-" * 80)
    
    judge_llm = None
    embeddings = None
    
    try:
        # langchain-openai provides the Azure-compatible wrappers RAGAS uses
        from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
        
        # Build the judge LLM — temperature=0 for deterministic scoring
        print(f"Initializing judge LLM ({CHAT_MODEL})...")
        judge_llm = AzureChatOpenAI(
            azure_endpoint=OPENAI_ENDPOINT,
            api_key=OPENAI_KEY,
            api_version="2024-02-15-preview",
            model=CHAT_MODEL,
            temperature=0
        )
        print(f"✓ Judge LLM initialized")
        
        # Build the embeddings client — used by context_precision/recall for similarity
        print(f"Initializing embeddings ({EMBEDDING_MODEL})...")
        embeddings = AzureOpenAIEmbeddings(
            azure_endpoint=OPENAI_ENDPOINT,
            api_key=OPENAI_KEY,
            api_version="2024-02-15-preview",
            model=EMBEDDING_MODEL
        )
        print(f"✓ Embeddings initialized\n")
        
    except ImportError:
        print("✗ ERROR: langchain_openai not installed")
        print("  Install: pip install langchain-openai")
        sys.exit(1)
    
    except Exception as e:
        print(f"✗ ERROR: Initialization failed")
        print(f"  {str(e)}")
        print("\nMake sure your Azure credentials are correct:")
        print("  - OPENAI_KEY: Valid Azure API key")
        print("  - OPENAI_ENDPOINT: Valid Azure endpoint URL")
        sys.exit(1)
    
    # ==========================================
    # STEP 6: RUN EVALUATION
    # ==========================================
    
    print("STEP 6: RUNNING RAGAS EVALUATION")
    print("-" * 80)
    print("Metrics:")
    print("  1. context_recall - Are all relevant chunks in contexts?")
    print("  2. context_precision - Are all chunks relevant?")
    print("  3. faithfulness - Is answer grounded in contexts?")
    print("  4. answer_correctness - Does answer match ground truth?")
    print(f"\nJudge: {CHAT_MODEL}")
    print(f"Embeddings: {EMBEDDING_MODEL}")
    print("Status: Running...\n")
    
    try:
        # Core RAGAS call — runs all four metrics across every sample.
        # Each sample triggers multiple LLM calls (one per metric), so this can take a while.
        result = evaluate(
            dataset=dataset,
            metrics=[
                context_recall,
                context_precision,
                faithfulness,
                answer_correctness,
            ],
            llm=judge_llm,  # Azure judge
            embeddings=embeddings  # Azure embeddings
        )
        print("✓ Evaluation complete!\n")
    
    except Exception as e:
        print(f"✗ Evaluation failed!")
        print(f"  Error: {str(e)}")
        print("\nTroubleshooting:")
        print("  - Check Azure credentials are correct")
        print("  - Check API quota not exceeded")
        print("  - Check internet connection")
        # Print full stack trace so the actual root cause is visible
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # ==========================================
    # STEP 7: DISPLAY RESULTS
    # ==========================================
    
    print("STEP 7: RESULTS")
    print("-" * 80)
    print("\nOVERALL SCORES:\n")
    print(result)
    
    # Turn the RAGAS result into a pandas DataFrame so we can sort, filter, and save it
    df = result.to_pandas()
    # Re-attach param_name from the original prepared items (RAGAS drops it)
    df["param_name"] = [item["param_name"] for item in prepared]
    
    # Drop unused columns and put param_name first for readability
    cols = ["param_name", "answer_correctness", "context_recall", 
            "context_precision", "faithfulness"]
    df = df[[c for c in cols if c in df.columns]]
    
    # Print one row per test case in a fixed-width table
    print(f"\n\nPER-PARAMETER BREAKDOWN:")
    print("-" * 80)
    print(f"{'Parameter':<30} {'AC':<12} {'Recall':<12} {'Precision':<12} {'Faith':<12}")
    print("-" * 80)
    
    for idx, row in df.iterrows():
        param = str(row["param_name"])[:29]
        ac = f"{row['answer_correctness']:.4f}"
        recall = f"{row['context_recall']:.4f}"
        prec = f"{row['context_precision']:.4f}"
        faith = f"{row['faithfulness']:.4f}"
        
        print(f"{param:<30} {ac:<12} {recall:<12} {prec:<12} {faith:<12}")
    
    # Flag any test cases that scored poorly so the operator can investigate
    low_scores = df[df["answer_correctness"] < 0.7]
    if len(low_scores) > 0:
        print(f"\n\nLOW SCORING (answer_correctness < 0.7):")
        print("-" * 80)
        for idx, row in low_scores.iterrows():
            print(f"  ✗ {row['param_name']}: {row['answer_correctness']:.4f}")
    else:
        print(f"\n\n✓ All parameters have good scores!")
    
    # ==========================================
    # STEP 8: SAVE RESULTS
    # ==========================================
    
    print(f"\n\nSTEP 8: SAVING RESULTS")
    print("-" * 80 + "\n")
    
    # Single timestamp shared by all three output files so they group together
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save CSV — easiest format for Excel / data analysis
    csv_file = f"ragas_evaluation_detailed_{timestamp}.csv"
    df.to_csv(csv_file, index=False)
    print(f"✓ CSV → {csv_file}")
    
    # Save JSON — machine-readable with run metadata + aggregate stats + per-row scores
    json_file = f"ragas_results_{timestamp}.json"
    results_dict = {
        "timestamp": timestamp,
        "input_file": INPUT_FILE,
        "judge_model": CHAT_MODEL,
        "embedding_model": EMBEDDING_MODEL,
        "items_evaluated": len(prepared),
        "items_skipped": len(skipped),
        # Per-metric summary: mean / min / max across all evaluated items
        "metrics_summary": {
            "answer_correctness": {
                "mean": float(df["answer_correctness"].mean()),
                "min": float(df["answer_correctness"].min()),
                "max": float(df["answer_correctness"].max())
            },
            "context_recall": {
                "mean": float(df["context_recall"].mean()),
                "min": float(df["context_recall"].min()),
                "max": float(df["context_recall"].max())
            },
            "context_precision": {
                "mean": float(df["context_precision"].mean()),
                "min": float(df["context_precision"].min()),
                "max": float(df["context_precision"].max())
            },
            "faithfulness": {
                "mean": float(df["faithfulness"].mean()),
                "min": float(df["faithfulness"].min()),
                "max": float(df["faithfulness"].max())
            }
        },
        # Per-parameter scores, one entry per test case
        "per_parameter": [
            {
                "parameter": row["param_name"],
                "answer_correctness": float(row["answer_correctness"]),
                "context_recall": float(row["context_recall"]),
                "context_precision": float(row["context_precision"]),
                "faithfulness": float(row["faithfulness"])
            }
            for idx, row in df.iterrows()
        ]
    }
    
    # Write the JSON report to disk (indented for readability)
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(results_dict, f, indent=2)
    print(f"✓ JSON → {json_file}")
    
    # Save a human-readable text summary suitable for pasting into reports or chat
    summary_file = f"ragas_summary_{timestamp}.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        # Header block: run metadata
        f.write("RAGAS EVALUATION SUMMARY\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Input File: {INPUT_FILE}\n")
        f.write(f"Judge Model: {CHAT_MODEL}\n")
        f.write(f"Embedding Model: {EMBEDDING_MODEL}\n")
        f.write(f"Items Evaluated: {len(prepared)}\n")
        f.write(f"Items Skipped: {len(skipped)}\n")
        f.write(f"Timestamp: {timestamp}\n\n")
        
        # Aggregate metric stats (same as JSON, but formatted for humans)
        f.write("OVERALL METRICS:\n")
        f.write("-" * 80 + "\n")
        f.write(f"answer_correctness:  {df['answer_correctness'].mean():.4f} (min: {df['answer_correctness'].min():.4f}, max: {df['answer_correctness'].max():.4f})\n")
        f.write(f"context_recall:      {df['context_recall'].mean():.4f} (min: {df['context_recall'].min():.4f}, max: {df['context_recall'].max():.4f})\n")
        f.write(f"context_precision:   {df['context_precision'].mean():.4f} (min: {df['context_precision'].min():.4f}, max: {df['context_precision'].max():.4f})\n")
        f.write(f"faithfulness:        {df['faithfulness'].mean():.4f} (min: {df['faithfulness'].min():.4f}, max: {df['faithfulness'].max():.4f})\n\n")
        
        # Per-parameter answer_correctness as a quick scan list
        f.write("PER-PARAMETER:\n")
        f.write("-" * 80 + "\n")
        for idx, row in df.iterrows():
            f.write(f"{row['param_name']}: {row['answer_correctness']:.4f}\n")
    
    print(f"✓ Summary → {summary_file}")
    
    # ==========================================
    # FINAL SUMMARY
    # ==========================================
    
    print(f"\n" + "="*80)
    print("EVALUATION COMPLETE")
    print("="*80)
    print(f"\nOutput files:")
    print(f"  1. {csv_file}")
    print(f"  2. {json_file}")
    print(f"  3. {summary_file}")
    print(f"\nOpen CSV in Excel for detailed analysis\n")


# Entry point — only runs main() when the script is executed directly,
# not when imported as a module.
if __name__ == "__main__":
    main()
