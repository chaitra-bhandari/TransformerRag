# Modules Overview

## Module Structure

Transformer Spec RAG consists of 6 core modules that work together in a pipeline:

```
Input Documents
    ↓
[1] doc_extraction_using_di.py    ← Azure Document Intelligence
    ↓
[2] chunk_by_title_semantic_blob.py ← Smart document chunking
    ↓
[3] rag_query.py (indexing phase)  ← Vector & keyword indexing
    ↓
[4] rag_query.py (query phase)     ← RAG retrieval & generation
    ↓
[5] doc_filling_blob.py            ← Document template filling
    ↓
Output Documents
```

## Module Dependency Map

```
app.py (Orchestrator)
│
├─→ doc_extraction_using_di.py
│   └─→ Azure Document Intelligence API
│
├─→ chunk_by_title_semantic_blob.py
│   └─→ Requires: DI output (JSON)
│
├─→ rag_query.py
│   ├─→ FAISS (vector search)
│   ├─→ BM25 (keyword search)
│   ├─→ Sentence-Transformers (embeddings)
│   ├─→ CrossEncoder (reranking)
│   └─→ Azure OpenAI (GPT-4)
│
└─→ doc_filling_blob.py
    ├─→ python-docx (DOCX manipulation)
    └─→ Requires: RAG answers + templates
```

## Module Details

### 1. Document Extraction (doc_extraction_using_di.py)

**Purpose:** Extract structured data from raw documents using Azure Document Intelligence

**Key Class:** `TransformerDocumentProcessor`

**Input:** PDF, DOCX, XLSX files from Azure Blob Storage

**Output:** JSON with extracted text, tables, and metadata

**Main Features:**
- Automatic page number normalization
- Table extraction with cell structure
- Duplicate file detection (MD5)
- Image-heavy page detection
- Multi-document batch processing

**Flow:**
```
Raw Doc → Download → Duplicate Check → Image Detection → DI API → Upload JSON
```

[Full Documentation →](doc-extraction.md)

### 2. Semantic Chunking (chunk_by_title_semantic_blob.py)

**Purpose:** Split DI output into intelligently sized chunks for RAG

**Key Class:** `DocumentChunker`

**Input:** JSON files from `output-of-di/`

**Output:** `all_chunks.json` with metadata

**Main Features:**
- Noise removal (headers, footers, page numbers)
- By-title semantic splitting
- Hierarchical section context
- Token-aware splitting (tiktoken)
- Table extraction

**Flow:**
```
DI JSON → Parse → Remove Noise → Identify Headings → Split Content → Extract Tables → Save Chunks
```

[Full Documentation →](chunking.md)

### 3. RAG Query Engine (rag_query.py)

**Purpose:** Index documents and retrieve/generate answers to queries

**Key Classes:**
- `FAISSVectorStore` - Vector indexing
- `RAGPipeline` - Query processing
- `HybridRetriever` - BM25 + Vector search

**Input:** Document chunks + hardcoded questions

**Output:** Answers to all questions with confidence scores

**Main Features:**
- Hybrid search (60% semantic, 40% keyword)
- Cross-Encoder reranking
- Language detection (EN/DE)
- Null-value deep-dive recovery
- Batch processing

**Flow:**
```
Chunks → Embedding → FAISS Index + BM25 Index → Query → Retrieve Top 20 
         → Rerank Top 10 → GPT-4 Generation → Output Answers
```

[Full Documentation →](rag-query.md)

### 4. Document Filling (doc_filling_blob.py)

**Purpose:** Fill order document templates with extracted specifications

**Key Class:** `DocumentFiller`

**Input:** DOCX templates + RAG answers (JSON)

**Output:** Filled DOCX documents

**Main Features:**
- Placeholder detection and replacement
- Metadata injection
- Language-aware formatting
- Batch document generation
- Error handling

**Flow:**
```
Template DOCX → Find Placeholders → Map RAG Data → Replace → Generate Output DOCX
```

[Full Documentation →](doc-filling.md)

### 5. FastAPI Backend (app.py)

**Purpose:** REST API and pipeline orchestration

**Key Routes:**
- `POST /upload` - Trigger full pipeline
- `GET /status/{project}` - Check processing status
- `GET /results/{project}` - Get results
- `GET /files/{project}` - List project files

**Features:**
- Background task processing
- CORS middleware
- Request validation
- Error handling & logging
- Static file serving (frontend)

**Flow:**
```
HTTP Request → Validate → Stage 1-6 Pipeline → HTTP Response
             ↓ (async)
        Background Tasks
```

[Full Documentation →](app.md)

### 6. React Chat UI (Docflow_chatui.jsx)

**Purpose:** Frontend interface for document upload and querying

**Features:**
- Document upload interface
- Project management
- Query chat interface
- Results display
- Language selection

**Integration:** Connects to FastAPI backend via HTTP/WebSocket

[Not fully documented in backend docs - refer to frontend files]

---

## How to Use Each Module

### Individual Module Usage

#### Document Extraction Only

```python
from doc_extraction_using_di import TransformerDocumentProcessor

processor = TransformerDocumentProcessor()
processor.process_project("MyProject_onshore_offshore")
```

#### Chunking Only

```python
from chunk_by_title_semantic_blob import DocumentChunker

chunker = DocumentChunker(max_characters=4000)
chunks = chunker.process_all_projects()
chunker.save_chunks()
```

#### RAG Query Only

```python
from rag_query import RAGPipeline

rag = RAGPipeline()
answers = rag.query_hardcoded_questions(project_name="MyProject")
```

#### Document Filling Only

```python
from doc_filling_blob import DocumentFiller

filler = DocumentFiller()
filler.fill_and_save(project_name="MyProject", answers={...})
```

### Full Pipeline via API

```bash
# Start backend
uvicorn app:app --reload

# Upload documents (triggers full pipeline)
curl -X POST http://localhost:8000/upload \
  -H "X-API-Key: your_key" \
  -F "files=@spec1.pdf" \
  -F "files=@spec2.pdf" \
  -F "project_name=MyProject_onshore_offshore"
```

---

## Module Comparison Table

| Module | Input | Output | Processing Time | Parallelizable |
|--------|-------|--------|-----------------|-----------------|
| **DI** | Raw PDFs | JSON | 5-10s/page | Yes |
| **Chunking** | DI JSON | Chunks JSON | 100MB/min | No |
| **RAG Indexing** | Chunks | FAISS/BM25 | 1-5s | Yes |
| **RAG Query** | Index + Questions | Answers | 2-5s | Yes |
| **Doc Filling** | Template + Answers | DOCX | <1s | Yes |

---

## Error Handling by Module

| Module | Common Errors | Recovery |
|--------|--------------|----------|
| **DI** | API timeout | Retry with backoff |
| **Chunking** | Invalid JSON | Skip file, log error |
| **RAG** | Embedding fails | Fall back to BM25 |
| **Filling** | Template not found | Use default template |

---

## Performance Optimization Tips

### DI Module
- Batch process documents
- Compress PDFs before upload
- Use smaller document sizes

### Chunking Module
- Increase `max_characters` for faster splitting
- Reduce `min_tokens` for more granular chunks
- Skip images with `process_images=False`

### RAG Module
- Reduce `RETRIEVAL_K` for faster queries
- Cache embeddings between runs
- Use smaller model for testing

### Filling Module
- Pre-compile templates
- Batch fill multiple documents
- Cache placeholder mappings

---

## Next Steps

- [Document Extraction](doc-extraction.md) - Deep dive into DI
- [Semantic Chunking](chunking.md) - Understand chunking strategies
- [RAG Query Engine](rag-query.md) - Learn retrieval & generation
- [Document Filling](doc-filling.md) - Template filling guide
- [FastAPI Backend](app.md) - REST API reference
