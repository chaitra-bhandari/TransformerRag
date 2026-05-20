
"""
RAG Query Engine - Hybrid Retrieval & Parameter Extraction

A sophisticated system for extracting transformer specifications from documents using
Retrieval-Augmented Generation (RAG) with hybrid search combining vector and keyword-based
retrieval methods.

Features:
    - Hybrid search combining BM25 (keyword) and vector search (semantic)
    - FAISS vector indexing for semantic similarity search
    - CrossEncoder re-ranking for improved relevance
    - Azure OpenAI integration for LLM-based parameter extraction
    - Deep-dive search that automatically searches for null values with different weights
    - Batch processing of questions for efficient extraction
    - ThreadPoolExecutor for parallel processing of multiple questions
    - Source attribution and confidence scoring

Usage:
    >>> from rag_query import extract_json, extract_with_deep_dive
    >>> results = extract_json(questions, project_name)
    >>> results_with_deepdive = extract_with_deep_dive(questions, project_name)

Configuration:
    Environment variables required:
    - OPENAI_KEY: Azure OpenAI API key
    - OPENAI_ENDPOINT: Azure OpenAI endpoint URL
    - CHAT_MODEL: LLM model name (default: gpt-4o)
    - EMBEDDING_MODEL: Embedding model name (default: text-embedding-3-large)
    - AZURE_STORAGE_CONNECTION_STRING: Azure Blob Storage connection
    - BLOB_INDEX_CONTAINER: Container for FAISS indexes
    - BLOB_CHUNK_CONTAINER: Container for chunked documents

Search Weights:
    Regular Search:
        - BM25: 40% (exact keyword matching)
        - Vector: 60% (semantic similarity)
    
    Deep Dive Search (for null values):
        - BM25: 30% (less emphasis on exact match)
        - Vector: 70% (more emphasis on semantics)
"""
import json
import os
import pickle
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import sys
import faiss
import numpy as np
from openai import AzureOpenAI
from rank_bm25 import BM25Okapi
from sentence_transformers import CrossEncoder


#Configuration - .env
OPENAI_KEY = os.getenv("OPENAI_KEY", "")
OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT", "")
CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")

#Regular search weights
BM25_WEIGHT = 0.4
VECTOR_WEIGHT = 0.6

#Deep dive search weights, for the null value re-check
DEEP_DIVE_BM25_WEIGHT = 0.3
DEEP_DIVE_VECTOR_WEIGHT = 0.7

RETRIEVAL_K = 20
RERANK_TOP_K = 10

#Set of 6 questions are sent to each gpt calls
BATCH_SIZE = 6

#Deep Dive triggered automatically for any null value after first pass
DEEP_DIVE_RETRIEVAL_K = 25
DEEP_DIVE_RERANK_TOP_K = 15

#Azure blob setup
client = AzureOpenAI(
    api_key=OPENAI_KEY, api_version="2024-02-15-preview", azure_endpoint=OPENAI_ENDPOINT
)

from azure.storage.blob import BlobServiceClient

blob_client = BlobServiceClient.from_connection_string(
    os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
)
index_container = blob_client.get_container_client(
    os.getenv("BLOB_INDEX_CONTAINER", "faiss-indexes")
)
metadata_container = blob_client.get_container_client(
    os.getenv("BLOB_METADATA_CONTAINER", "faiss-metadata")
)

#Document language detection while filling the document( end product) in the same language either german or english
def detect_document_language(db, project_name: str) -> str:
    if not hasattr(db, "metadata") or not db.metadata:
        return "en"

    sample_chunks = db.metadata[: min(10, len(db.metadata))]

    german_indicators = [
        "Nennspannung", "Nennfrequenz", "Ausrüstung", "Kühlungsart",
        "Stufenschalter", "Schaltgruppe", "Impedanz", "Durchführung",
        "Korrosionsschutz", "Prüföl", "Kessel", "Armaturen",
        "Schaltstoßspannung", "Blitzstoßspannung", "Kurzschlussstrom",
        "Wicklung", "Leistung", "MVA", "Transformator",
        "Das ist", "die", "der", "und", "oder", "für", "mit", "von", "des", "dem"
    ]

    english_indicators = [
        "rated voltage", "frequency Hz", "cooling", "tap changer",
        "vector group", "impedance", "bushing", "corrosion",
        "test oil", "tank", "valves", "applied voltage",
        "short circuit", "winding", "power", "MVA", "transformer",
        "This is", "the", "and", "or", "for", "with", "of", "the", "is"
    ]

    german_count = 0
    english_count = 0

    for chunk in sample_chunks:
        content = chunk.get("content", "").lower() if isinstance(chunk, dict) else str(chunk).lower()

        for indicator in german_indicators:
            if indicator.lower() in content:
                german_count += 1

        for indicator in english_indicators:
            if indicator.lower() in content:
                english_count += 1

    if german_count > english_count:
        return "de"
    return "en"

#List of questions should be answered by the gpt in JSON format, to fill the documents (German)
def build_parameter_registry(p: str, language: str = "en") -> dict:
    """
    Build parameter registry with language-specific questions.
    language: "en" (English) or "de" (German)
    Returns: Dictionary with parameters and appropriate language questions
    """

    if language == "de":
        return {
            "frequency": {
    "question": "Welche Nennfrequenz (Hz) order BEMESSUNGSFREQUENZ ist für Projekt {p} angegeben?",
    "aliases": ["Nennfrequenz", "frequency", "Frequenz Hz", "50Hz", "60Hz", "BEMESSUNGSFREQUENZ", "fn"]
  },

  "network_conditions": {
    "question": "Welche Nennspannung oder Bemessungsspannung ist für Projekt {p} angegeben?",
    "aliases": ["Nennspannung", "rated voltage", "Um", "Ur", "Un", "kV", "Umax", "Bemessungsspannung"]
  },


        
        }
    else:
        #List of questions should be answered by the gpt in JSON format, to fill the documents (English)
        return {
            "frequency": {
                "question": f"What is the rated frequency or frequency mentioned for project {p}?",
                "aliases": ["rated frequency", "Nennfrequenz", "frequency Hz", "50Hz", "60Hz", "fn"],
            },
            "network_conditions": {
                "question": f"What is the nominal voltage or system volage mentioned for project {p}?",
                "aliases": ["nominal voltage", "Nennspannung", "rated voltage", "Um", "Ur", "Un", "kV", "Umax"],
            },

        }


class HybridVectorDB:
    def __init__(self, index_file="docs.index", meta_file="docs.pkl"):
        self.index_file = index_file
        self.meta_file = meta_file
        self.index = None
        self.metadata = []
        self.bm25 = None
        self.tokenized = []

    @staticmethod
    def _tokenize(text: str) -> list:
        return re.findall(r"[a-zA-Z0-9]+(?:[.\-/_][a-zA-Z0-9]+)*", text.lower())
    
    #Loading faiss index and metadata from blob(stored in blob)
    def load(self):
        
        try:
            # Download FAISS index from blob
            index_blob = index_container.get_blob_client(self.index_file)
            index_data = index_blob.download_blob().readall()

            # Write temporarily to disk (FAISS requires file path)
            import tempfile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".index") as tmp:
                tmp.write(index_data)
                tmp_path = tmp.name

            # Load from temporary file
            self.index = faiss.read_index(tmp_path)

            # Clean up temp file
            import os as os_module
            os_module.remove(tmp_path)

        except Exception as e:
            # Silent error handling
            return False

        try:
            # Download metadata from blob
            metadata_blob = metadata_container.get_blob_client(self.meta_file)
            metadata_data = metadata_blob.download_blob().readall()

            # Load pickle from bytes
            import io
            self.metadata = pickle.load(io.BytesIO(metadata_data))

        except Exception as e:
            # Silent error handling
            return False

        # Build BM25 index
        tokenized_corpus = [self._tokenize(c.get("content", "")) for c in self.metadata]
        self.bm25 = BM25Okapi(tokenized_corpus)

        return True
    
    #Extract project_name from chunk metadata
    def _get_project_name(self, chunk: dict) -> str:
        if isinstance(chunk, dict) and "metadata" in chunk:
            return chunk["metadata"].get("project_name", "").strip().lower()
        return chunk.get("project_name", "").strip().lower()
    
    
    #Filter chunks and BM25 index for a specific project"
    def prepare_project(self, project_name: str):
        indices = []
        for i, chunk in enumerate(self.metadata):
            if self._get_project_name(chunk) == project_name.strip().lower():
                indices.append(i)

        if not indices:
            return [], None

        #Build project-specific BM25
        project_chunks = [self.metadata[i] for i in indices]
        project_tokenized = [self._tokenize(c.get("content", "")) for c in project_chunks]
        project_bm25 = BM25Okapi(project_tokenized)

        return indices, project_bm25
    
    #Search for chunks filtered by project_name and  Returns top k chunks for the specific project.
    def search(self, question: str, aliases: list, project_name: str, k=10, q_vec=None):
        indices, project_bm25 = self.prepare_project(project_name)

        if not indices:
            return []

        #Get embedding for question if not provided
        if q_vec is None:
            try:
                res = client.embeddings.create(input=[question], model=EMBEDDING_MODEL)
                q_vec = np.array(res.data[0].embedding, dtype=np.float32)
            except:
                return []

        #Vector search
        q_vec_norm = q_vec / (np.linalg.norm(q_vec) + 1e-10)
        D, I = self.index.search(q_vec_norm.reshape(1, -1), min(k * 3, len(indices)))

        #Filter to project indices
        valid_indices = []
        for idx in I[0]:
            if idx < len(self.metadata) and idx in indices:
                valid_indices.append(idx)

        #BM25 search
        keywords = aliases if aliases else [question]
        bm25_scores = project_bm25.get_scores(keywords)
        bm25_indices = sorted(
            enumerate(bm25_scores), key=lambda x: x[1], reverse=True
        )[:k]

        #Combine results
        combined = {}
        for rank, (idx, score) in enumerate([(i, bm25_scores[i]) for i, _ in bm25_indices if i in indices]):
            combined[idx] = combined.get(idx, 0) + (k - rank) * VECTOR_WEIGHT

        for rank, idx in enumerate(valid_indices[:k]):
            combined[idx] = combined.get(idx, 0) + (k - rank) * BM25_WEIGHT

        #Sort and return
        sorted_indices = sorted(combined.keys(), key=lambda x: combined[x], reverse=True)[:k]
        return [
            {
                "chunk_id": i,
                "content": self.metadata[i].get("content", ""),
                "metadata": self.metadata[i].get("metadata", {}),
            }
            for i in sorted_indices
        ]

    # Search using keywords for a specific project
    def search_with_keywords(self, keywords: list, project_name: str, k=10):
        indices, project_bm25 = self.prepare_project(project_name)

        if not indices:
            return []

        bm25_scores = project_bm25.get_scores(keywords)
        sorted_indices = sorted(
            enumerate(bm25_scores), key=lambda x: x[1], reverse=True
        )[:k]

        return [
            {
                "chunk_id": indices[idx] if idx < len(indices) else idx,
                "content": self.metadata[indices[idx]].get("content", "") if idx < len(indices) else "",
                "metadata": self.metadata[indices[idx]].get("metadata", {}) if idx < len(indices) else {},
            }
            for idx, _ in sorted_indices
        ]


class CrossEncoderReranker:
    #cross-encoder/mmarco-mMiniLMv2-L12-H384
    #BAAI/bge-reranker-large
    def __init__(self, model_name: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384"):
        try:
            self.model = CrossEncoder(model_name)
        except:
            self.model = None
     
    #Rerank candidates using crossencode
    def rerank(self, question: str, candidates: list, top_k: int = 10) -> list:
        if not self.model or not candidates:
            return candidates[:top_k]

        try:
            pairs = [[question, c.get("content", "")] for c in candidates]
            scores = self.model.predict(pairs)
            ranked = sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)
            return [c for c, _ in ranked[:top_k]]
        except:
            return candidates[:top_k]

#Normalize GPT response to ensure correct structure
def normalize_gpt_response(result: dict, param_name: str) -> dict:
    if param_name not in result:
        return {"value": None, "source_document": "none", "page": "none"}

    param_result = result[param_name]

    if isinstance(param_result, dict) and all(k in param_result for k in ["value", "source_document", "page"]):
        return param_result

    if isinstance(param_result, dict):
        value = param_result.get("value")
        source_doc = param_result.get("source_document", "none")
        page = param_result.get("page", "none")

        if value is None:
            source_doc = "none"
            page = "none"

        return {
            "value": value,
            "source_document": source_doc,
            "page": page
        }

    return {"value": None, "source_document": "none", "page": "none"}

#Call GPT for a batch of parameters
def call_gpt_for_cluster(cluster_name: str, cluster_params: dict,
                          parameter_contexts: dict, parameter_sources: dict, project: str) -> dict:
  
    context_block = ""
    for param in cluster_params:
        context_block += f"\n\n### CONTEXT FOR [{param}]:\n{parameter_contexts[param]}"

    template = {param: {"value": None, "source_document": None, "page": None} for param in cluster_params}
    questions = "\n".join([
        f'  "{p}": <answer to: {cluster_params[p]["question"]}>'
        for p in cluster_params
    ])

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0.2,
        max_tokens=3000,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a technical extraction assistant for power transformer design documents. "
                    "RETURN ONLY VALID JSON. NO OTHER TEXT.\n\n"
                    "CRITICAL INSTRUCTIONS:\n"
                   
                    "1. Each parameter MUST have exactly THREE fields: 'value', 'source_document', and 'page'\n"
                    "8. Extract the answer to each question from its labelled context only and try to keep the answer as much as asked in each question. "
                    "2. 'source_document' = the EXACT document name from [Source: ...] tags (e.g., 'Appendix 1A - Insurance exhibit (CAR)_di_result')\n"
                    "3. 'page' = the EXACT page number from [Source: ...] tags as an INTEGER (e.g., 3 or 18)\n"
                    "4. If value NOT found: value=null, source_document='none', page='none'\n"
                    "5. If value IS found: here value might be multiple field answers list them like parameter wise, long answers also the source_document and page must NEVER be 'none'\n"
                    "6. Do NOT create 'reference' field. Do NOT create any other fields.\n"
                    "7. Never make up information. Extract exactly what you see.\n\n"
                    "EXAMPLES OF CORRECT OUTPUT:\n"
                    '  {"bushings": {"value": "Type A specification", "source_document": "Appendix 1A - Insurance exhibit (CAR)_di_result", "page": 3}}\n'
                    '  {"cooling_types": {"value": "ONAN", "source_document": "Technical Specification Sheet", "page": 15}}\n\n'
                    "WRONG OUTPUT EXAMPLES (DO NOT DO THIS):\n"
                    '  {"bushings": "Type A specification"}  ← MISSING source_document and page\n'
                    '  {"bushings": {"value": "Type A", "reference": "Page 3"}}  ← WRONG: has reference instead of source_document and page\n'
                    
                )
            },
            {
                "role": "user",
                "content": (
                    f"Here are {len(cluster_params)} parameters to extract.\n\n"
                    f"{context_block}\n\n"
                    f"Return this JSON structure:\n{json.dumps(template, indent=2)}\n\n"
                    f"Questions:\n{questions}"
                )
            }
        ]
    )

    try:
        result = json.loads(response.choices[0].message.content)
        normalized = {}
        for param in result:
            normalized[param] = normalize_gpt_response(result, param)
        return normalized
    except:
        return {param: {"value": None, "source_document": "none", "page": "none"} for param in cluster_params}

#Search again for null parameter
def deep_dive_single(param: str, meta: dict, db: HybridVectorDB,
                     reranker: CrossEncoderReranker, project: str):
    """Single parameter deep dive re-extraction"""
    keywords = meta.get("aliases", [])
    if not keywords:
        return param, {"value": None, "source_document": "none", "page": "none"}

    candidates = db.search_with_keywords(
        keywords=keywords,
        project_name=project,
        k=DEEP_DIVE_RETRIEVAL_K
    )

    top_chunks = reranker.rerank(meta["question"], candidates, top_k=DEEP_DIVE_RERANK_TOP_K)

    context_parts = []
    for chunk in top_chunks:
        source_doc = chunk.get("metadata", {}).get("source_document", "unknown")
        page = chunk.get("metadata", {}).get("page", "N/A")
        content = chunk.get("content", "")
        context_parts.append(f"[Source: {source_doc}, Page: {page}]\n{content}")

    context = "\n\n".join(context_parts)

    response = client.chat.completions.create(
        model=CHAT_MODEL,
        temperature=0.2,
        max_tokens=3000,
        response_format={"type": "json_object"},
        messages=[
            {
                 "role": "system",
                "content": (
                    "You are a technical extraction assistant. RETURN ONLY VALID JSON. NO OTHER TEXT.\n\n"
                    f"CRITICAL: Extract parameter '{param}'\n\n"
                    "REQUIRED JSON STRUCTURE (you must return EXACTLY this format):\n"
                    '{"value": <extracted_value_or_null_or multiple fields>, "source_document": "<exact_doc_name_or_none>", "page": <page_number_or_none>}\n\n'
                    "RULES:\n"
                    "0. Extract the answer to each question from its labelled context only and try to keep the answer as much as asked in each question. "
                    "1. 'source_document' = EXACT document name from [Source: ...] tags (NOT 'none' if value found)\n"
                    "2. 'page' = EXACT page number as INTEGER from [Source: ...] tags (NOT 'none' if value found)\n"
                    "3. If value NOT found: {\"value\": null, \"source_document\": \"none\", \"page\": \"none\"}\n"
                    "4. Do NOT create 'reference' field\n"
                    "5. Do NOT add any fields besides value, source_document, page\n"
                    "6. Extract exactly what you see. Never make up information.\n\n"
                    f"Question: {meta['question']}"
                )
            },
            {
                "role": "user",
                "content": f"Context:\n{context}"
            }
        ]
    )

    try:
        result = json.loads(response.choices[0].message.content)
        normalized = normalize_gpt_response(result, param) if param in result else {"value": None, "source_document": "none", "page": "none"}
        return param, normalized
    except:
        return param, {"value": None, "source_document": "none", "page": "none"}

#Batch embed all parameter questions,  Parallel retrieval with cached embeddings, Batch GPT calls and Deep dive on nulls
def extract_from_project(project_name: str):
    t_start = time.time()

    # Initialize DB - SINGLE common index for all projects
    db = HybridVectorDB(
        index_file="docs.index",
        meta_file="docs.pkl"
    )
    success = db.load()
    if not success:
        return None

    # Detect language for parameter registry
    language = detect_document_language(db, project_name)

    # Build registry with language-specific questions
    registry = build_parameter_registry(project_name, language)

    # Initialize reranker
    reranker = CrossEncoderReranker()

    # STEP 1A: Batch embed all parameter questions
    questions = [meta.get("question", param) for param, meta in registry.items()]

    try:
        embedding_response = client.embeddings.create(
            input=questions,
            model=EMBEDDING_MODEL
        )
        embeddings_cache = {
            param: embedding_response.data[i].embedding
            for i, (param, _) in enumerate(registry.items())
        }
    except:
        embeddings_cache = {}

    # STEP 1B: Parallel retrieval
    parameter_contexts = {}
    parameter_sources = {}

    def retrieve_param_with_embedding(param_meta_tuple):
        param, meta = param_meta_tuple
        question = meta.get("question", param)

        # Use cached embedding
        try:
            q_vec = np.array(embeddings_cache[param], dtype=np.float32)
        except:
            q_vec = None

        candidates = db.search(
            question=question,
            aliases=meta.get("aliases", []),
            project_name=project_name,
            k=RETRIEVAL_K,
            q_vec=q_vec
        )

        top_chunks = reranker.rerank(question, candidates, top_k=RERANK_TOP_K)

        context_parts = []
        chunk_metadata_list = []

        for chunk in top_chunks:
            source_doc = chunk.get("metadata", {}).get("source_document", "unknown")
            page = chunk.get("metadata", {}).get("page", "N/A")
            content = chunk.get("content", "")
            context_parts.append(f"[Source: {source_doc}, Page: {page}]\n{content}")
            chunk_metadata_list.append({
                "source_document": source_doc,
                "page": page
            })

        context = "\n\n".join(context_parts) if context_parts else ""
        return param, context, chunk_metadata_list

    with ThreadPoolExecutor(max_workers=12) as executor:
        retrieval_futures = {
            executor.submit(retrieve_param_with_embedding, item): item[0]
            for item in registry.items()
        }
        for future in as_completed(retrieval_futures):
            param, context, chunk_metadata_list = future.result()
            parameter_contexts[param] = context
            parameter_sources[param] = chunk_metadata_list

    # STEP 2: Batch GPT calls
    all_params = list(registry.items())
    batches = [
        dict(all_params[i : i + BATCH_SIZE])
        for i in range(0, len(all_params), BATCH_SIZE)
    ]

    batch_results = {}

    with ThreadPoolExecutor(max_workers=len(batches)) as executor:
        futures = {
            executor.submit(
                call_gpt_for_cluster,
                f"batch_{idx+1}",
                batch,
                parameter_contexts,
                parameter_sources,
                project_name
            ): idx
            for idx, batch in enumerate(batches)
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                batch_results[idx] = future.result()
            except:
                batch_results[idx] = {}

    # STEP 3: Merge results
    result = {"project_name": project_name}
    for idx in sorted(batch_results):
        result.update(batch_results[idx])

    # STEP 4: Deep dive on nulls
    null_params = [
        k for k, v in result.items()
        if k != "project_name" and (
            (isinstance(v, dict) and v.get("value") is None) or
            (v is None)
        )
    ]

    if null_params:
        with ThreadPoolExecutor(max_workers=min(len(null_params), 8)) as executor:
            dd_futures = {
                executor.submit(
                    deep_dive_single, param, registry[param], db, reranker, project_name
                ): param
                for param in null_params
            }
            for future in as_completed(dd_futures):
                param, return_value = future.result()
                if return_value.get("value") is not None:
                    result[param] = return_value
                else:
                    result[param] = {
                        "value": None,
                        "source_document": "none",
                        "page": "none"
                    }

    t_end = time.time()

    return result




#Main entry point- extracts parameters for a given project using the common FAISS index.
def query_rag(query: str, project_name: str, transformer_type: str = "power") -> str:
    result = extract_from_project(project_name)
    if result is None:
        return json.dumps({"error": "Failed to load FAISS index"})
    return json.dumps(result, indent=2)

#For local testing
if __name__ == "__main__":
    
    project_name = input("Enter project name: ") if len(os.sys.argv) < 2 else os.sys.argv[1]
    result = extract_from_project(project_name)
    if result:
        print(json.dumps(result, indent=2))
        
        output_file = f"output_{project_name}_{int(time.time())}.json"
        abs_path = os.path.abspath(output_file)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        if os.path.exists(output_file):
            print(f"File saved!")
            print(f"Path: {abs_path}")
        else:
            print(f"File creation failed!")
            
        import traceback
        traceback.print_exc()
