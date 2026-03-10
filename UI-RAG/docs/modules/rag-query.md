# RAG Query Engine Module

## Overview

The RAG (Retrieval-Augmented Generation) module retrieves relevant document chunks and generates answers to specification questions using GPT-4.

**Module:** `rag_query.py`

**Key Components:**
- Vector indexing (FAISS)
- Keyword search (BM25)
- Hybrid retrieval
- Cross-Encoder reranking
- GPT-4 answer generation

## Hybrid Search Strategy

```
Query
  ├─ Vector Search (60%)
  │   └─ Embeddings similarity
  ├─ BM25 Search (40%)
  │   └─ Keyword matching
  └─ Hybrid Score = 0.6*vector + 0.4*bm25
      ↓
    Top 20 Chunks
      ↓
    Cross-Encoder Reranking
      ↓
    Top 10 Chunks (context)
      ↓
    GPT-4 Answer Generation
```

## API Reference

### Core Classes

#### FAISSVectorStore

Manages vector indexing:

```python
from rag_query import FAISSVectorStore

# Create or load
store = FAISSVectorStore(
    index_path="indexes/project_index.faiss",
    metadata_path="metadata/project_metadata.pkl"
)

# Add chunks
store.add_chunks(chunks)

# Search
results = store.search(query_embedding, k=20)
```

#### RAGPipeline

Main class for queries:

```python
from rag_query import RAGPipeline

pipeline = RAGPipeline(project_name="Energinet_onshore")

# Query hardcoded questions
answers = pipeline.query_hardcoded_questions()

# Custom query
answer = pipeline.query_custom(question="What is the rated voltage?")
```

### Key Methods

#### `create_embeddings(texts: List[str]) → np.ndarray`

Generate embeddings for texts:

```python
texts = ["Rated voltage: 110 kV", "Frequency: 50 Hz"]
embeddings = pipeline.create_embeddings(texts)
# Returns: (2, 3072) array
```

**Model:** `text-embedding-3-large` (3072 dimensions)

#### `build_indexes(chunks: List[Dict])`

Build FAISS and BM25 indexes:

```python
chunks = [...]  # from chunking module
pipeline.build_indexes(chunks)

# Saves to:
# faiss-indexes/{project}_index.faiss
# faiss-metadata/{project}_metadata.pkl
```

#### `hybrid_search(query: str, k: int = 20) → List[Dict]`

Retrieve relevant chunks:

```python
results = pipeline.hybrid_search("voltage specifications", k=20)

for result in results:
    print(f"Score: {result['score']:.3f}")
    print(f"Content: {result['content'][:100]}...")
```

**Returns:** Sorted list of chunks with:
- `score` - Combined hybrid score (0-1)
- `content` - Chunk text
- `metadata` - Source info
- `vector_score` - Semantic similarity
- `bm25_score` - Keyword relevance

#### `query_hardcoded_questions() → Dict[str, str]`

Get answers to predefined questions:

```python
answers = pipeline.query_hardcoded_questions()

print(answers)
# {
#   "question_1": "answer_1",
#   "question_2": "answer_2",
#   ...
# }
```

**Questions are hardcoded in `rag_query.py`** - typically:
- Rated voltage
- Rated power
- Frequency
- Connection type
- etc.

#### `query_custom(question: str) → str`

Answer a custom question:

```python
answer = pipeline.query_custom("What cooling system is used?")
```

**Returns:** Single answer string

## Configuration Parameters

### Search Weights

```python
BM25_WEIGHT = 0.4      # Keyword relevance importance
VECTOR_WEIGHT = 0.6    # Semantic similarity importance
```

**Adjust for:**
- **Keyword-heavy docs:** Increase BM25_WEIGHT to 0.5-0.6
- **Semantic docs:** Increase VECTOR_WEIGHT to 0.7-0.8

### Retrieval Counts

```python
RETRIEVAL_K = 20           # Initial chunks to retrieve
RERANK_TOP_K = 10          # Final chunks after reranking

DEEP_DIVE_RETRIEVAL_K = 25 # Retry retrieval count
DEEP_DIVE_RERANK_TOP_K = 15
```

**Adjust for:**
- **Speed priority:** Lower RETRIEVAL_K (15-20)
- **Accuracy priority:** Higher RETRIEVAL_K (25-30)

### Batch Processing

```python
BATCH_SIZE = 6  # Questions per GPT call
```

**Process 6 questions in one API call** → Cost optimization

### Deep-Dive Weights (Null-Value Recovery)

```python
DEEP_DIVE_BM25_WEIGHT = 0.3
DEEP_DIVE_VECTOR_WEIGHT = 0.7
```

When initial answer is null, retry with **more semantic weight**.

## Usage Examples

### Basic Query

```python
from rag_query import RAGPipeline

# Initialize for a project
pipeline = RAGPipeline(project_name="Energinet_onshore")

# Get answers to hardcoded questions
answers = pipeline.query_hardcoded_questions()

# Save results
import json
with open("answers.json", "w") as f:
    json.dump(answers, f, indent=2)
```

### Build Indexes

```python
from rag_query import RAGPipeline
import json

# Load chunks from previous stage
with open("all_chunks.json") as f:
    chunks = json.load(f)

# Build indexes for a project
pipeline = RAGPipeline(project_name="MyProject")
pipeline.build_indexes(chunks)

print("✓ Indexes built")
```

### Custom Query

```python
pipeline = RAGPipeline(project_name="Energinet_onshore")

# Answer one question
question = "What is the oil type used in the transformer?"
answer = pipeline.query_custom(question)

print(f"Q: {question}")
print(f"A: {answer}")
```

### Batch Processing Multiple Projects

```python
from rag_query import RAGPipeline
import json

projects = ["Project1", "Project2", "Project3"]

for project in projects:
    print(f"\nProcessing {project}...")
    
    pipeline = RAGPipeline(project_name=project)
    answers = pipeline.query_hardcoded_questions()
    
    # Save
    with open(f"results/{project}_answers.json", "w") as f:
        json.dump(answers, f)
    
    print(f"✓ {len(answers)} questions answered")
```

## Output Format

### Answers JSON

```json
{
  "question_1": "110 kV",
  "question_2": "250 MVA",
  "question_3": "50 Hz",
  "question_4": "On-load tap changer",
  "question_5": "ONAN",
  ...
}
```

**Null value handling:**
- First pass: Standard retrieval
- If answer is "null" → Deep-dive pass
- If still null → Output "Not found"

## Advanced Topics

### Language Detection

Automatically detects German/English:

```python
# Checks first 10 chunks for language indicators
language = pipeline.detect_language(chunks[:10])
# Returns: "de" or "en"

# Responses generated in same language
```

### Cross-Encoder Reranking

Uses sentence-transformers for final ranking:

```python
# After hybrid search: Top 20 chunks
# Cross-Encoder scores: All 20
# Final selection: Top 10 by CE score
```

Improves answer quality ~15-20%

### FAISS Index Details

Vector search uses:
- **FAISS type:** IVF (Inverted Vector File)
- **Dimension:** 3072 (text-embedding-3-large)
- **Metric:** L2 (Euclidean distance)

### BM25 Index

Keyword search uses:
- **Tokenization:** Whitespace + stopword removal
- **Scoring:** TF-IDF with saturation (k1=1.5, b=0.75)

## Performance

### Typical Times

| Operation | Time |
|-----------|------|
| Embedding generation | 1-2s per query |
| Vector search (top 20) | <0.5s |
| BM25 search | <0.1s |
| Reranking (top 10) | ~1s |
| GPT-4 generation | 2-5s |
| **Total per question** | **4-8s** |

### Batch Times

- **6 questions in one call:** 10-15s total
- **Per question:** 1.6-2.5s average

## Optimization Tips

### Faster Queries
```python
RETRIEVAL_K = 10           # Fewer chunks
RERANK_TOP_K = 5           # Less reranking
BM25_WEIGHT = 0.5          # Skip some vector calc
```

### Better Answers
```python
RETRIEVAL_K = 30           # More context
RERANK_TOP_K = 15          # Thorough reranking
VECTOR_WEIGHT = 0.8        # Prioritize semantic
```

### Lower Costs
```python
BATCH_SIZE = 10            # More questions per call
# Use gpt-4-turbo instead of gpt-4
EMBEDDING_MODEL = "text-embedding-3-small"  # Cheaper
```

## Troubleshooting

### "Index not found"

**Problem:** FAISS index missing

**Solution:**
```python
pipeline.build_indexes(chunks)  # Rebuild
```

### Low Answer Quality

**Problem:** Wrong or incomplete answers

**Solutions:**
1. Increase `RETRIEVAL_K` to 25-30
2. Adjust `BM25_WEIGHT` / `VECTOR_WEIGHT`
3. Check if chunks are too small
4. Try rephrasing question

### "Null" for Every Question

**Problem:** Not finding relevant chunks

**Solutions:**
1. Check chunks are indexed (verify JSON files)
2. Verify chunks have good content (not just noise)
3. Lower `RERANK_TOP_K` threshold
4. Check language matches documents

### Embedding API Errors

**Problem:** "Could not connect to embeddings service"

**Solution:**
```bash
# Verify credentials
echo $OPENAI_KEY
echo $OPENAI_ENDPOINT

# Check Azure service is running
# Increase API timeout in code
```

### OOM (Out of Memory) with Large Indexes

**Problem:** FAISS index too large for RAM

**Solutions:**
1. Use FAISS on GPU: `faiss-gpu`
2. Split project into smaller chunks
3. Increase server RAM
4. Use FAISS quantization

---

**Next:** [Document Filling](doc-filling.md) → Fill templates with answers
