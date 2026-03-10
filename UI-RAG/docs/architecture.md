# System Architecture

## Overview

Transformer Spec RAG is a **5-stage pipeline** that transforms raw documents into structured specifications and generates order documents automatically.

## Pipeline Stages

### Stage 1: Document Upload & Input
```
Input Container (Azure Blob)
├── ProjectName_onshore/
│   ├── spec1.pdf
│   ├── spec2.docx
│   └── data.xlsx
└── ProjectName_offshore/
    └── spec3.pdf
```

**Input formats supported:**
- PDF
- DOCX (Word)
- XLSX (Excel)

### Stage 2: Document Intelligence (DI) Extraction

**Module:** `doc_extraction_using_di.py`

```
Raw Document
    ↓
[Azure Document Intelligence API]
    ↓ Extract:
    ├── Paragraphs with roles (title, sectionHeading, etc.)
    ├── Tables with cell content
    ├── Bounding regions & page numbers
    └── Metadata
    ↓
Output Container: output-of-di/
└── ProjectName_onshore/
    ├── spec1_di_result.json
    ├── spec2_di_result.json
    └── data_di_result.json
```

**Features:**
- Automatic page number normalization (0-based → 1-based)
- Duplicate file detection (MD5 hashing)
- Image-heavy page detection
- Error handling & retry logic

### Stage 3: Semantic Chunking

**Module:** `chunk_by_title_semantic_blob.py`

```
DI JSON Result
    ↓
[Semantic Chunker]
    ↓ Process:
    ├── Remove noise (headers, footers, page numbers)
    ├── Identify section headings (numbered, role-based)
    ├── Group content under headings
    ├── Split by token count & character limit
    └── Extract tables as separate chunks
    ↓
Chunks Container: chunked-output/
└── all_chunks.json
```

**Smart Chunking:**
- By-title semantic chunking
- Hierarchical section context
- Token-aware splitting (tiktoken)
- Configurable sizes:
  - Min: 10 tokens
  - Max: 4000 characters
  - New chunk after: 3800 characters

### Stage 4: Vector Indexing & Search

**Module:** `rag_query.py` (indexing phase)

```
Document Chunks
    ↓
[Vectorization]
    ├── OpenAI Embeddings (text-embedding-3-large)
    └── FAISS Index (Approximate Nearest Neighbor)
    ↓
[BM25 Index]
    └── Keyword-based ranking
    ↓
Storage:
├── faiss-indexes/
│   └── {project}_index.faiss
└── faiss-metadata/
    └── {project}_metadata.pkl
```

**Hybrid Search Strategy:**
- **Vector Search (60%):** Semantic similarity via embeddings
- **BM25 (40%):** Keyword matching

### Stage 5: RAG Query & Answer Generation

**Module:** `rag_query.py` (query phase)

```
User Query
    ↓
[Retrieval]
├── Vector search (top 20 results)
├── BM25 keyword search
└── Hybrid ranking: 0.6*vector + 0.4*bm25
    ↓
[Reranking]
└── Cross-Encoder: Top 10 from above
    ↓
[Context + Prompt]
├── Retrieved chunks (context)
├── User query
├── Hardcoded questions list
└── System instructions
    ↓
[Azure OpenAI (GPT-4o)]
    ↓ Generate:
    ├── Answers to all questions
    ├── Language-aware (DE/EN)
    └── Null/Not Found detection
    ↓
Output JSON:
└── {
      "question_1": "answer_1",
      "question_2": "answer_2",
      ...
    }
```

### Stage 6: Document Filling & Generation

**Module:** `doc_filling_blob.py`

```
RAG Output (Extracted Data)
    ↓
[Document Filler]
├── Load template: order-templates/Order_A.docx
├── Find placeholders: {{SPEC_VOLTAGE}}, {{SPEC_POWER}}, etc.
├── Map RAG answers to placeholders
└── Generate filled document
    ↓
Output Container: order-design-documents/
└── ProjectName_onshore_offshore/
    ├── Order_A.docx (filled)
    └── Order_B.docx (filled)
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   User Uploads Project                   │
│              (PDFs, DOCX, XLSX files)                   │
│         input-document-center/{project}/                │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ↓
        ┌──────────────────────────────┐
        │  STAGE 1: UPLOAD & VALIDATION │
        │ - List project files          │
        │ - Check for duplicates        │
        │ - Validate formats            │
        └──────────────┬────────────────┘
                       │
                       ↓
      ┌────────────────────────────────────┐
      │  STAGE 2: DOCUMENT INTELLIGENCE    │
      │ - Extract text & structure         │
      │ - Extract tables                   │
      │ - Detect image pages               │
      │ - Save JSON results                │
      │   output-of-di/{project}/          │
      └──────────────┬─────────────────────┘
                     │
                     ↓
        ┌──────────────────────────────┐
        │ STAGE 3: SEMANTIC CHUNKING   │
        │ - Remove noise                │
        │ - Identify headings           │
        │ - Smart text splitting        │
        │ - Extract tables              │
        │ - Output: all_chunks.json     │
        └──────────────┬────────────────┘
                       │
                       ↓
       ┌───────────────────────────────────┐
       │  STAGE 4: VECTOR INDEXING        │
       │ - Generate embeddings             │
       │ - Build FAISS index               │
       │ - Build BM25 index                │
       │ - Save indexes & metadata         │
       │   faiss-indexes/                  │
       │   faiss-metadata/                 │
       └──────────────┬──────────────────┘
                      │
                      ↓
      ┌───────────────────────────────────┐
      │  STAGE 5: RAG QUERY ENGINE        │
      │ - Receive hardcoded questions      │
      │ - Retrieve relevant chunks         │
      │ - Rerank top candidates            │
      │ - Generate answers with GPT-4      │
      │ - Detect language (DE/EN)          │
      │ - Output: answers.json             │
      └──────────────┬──────────────────┘
                     │
                     ↓
      ┌───────────────────────────────────┐
      │  STAGE 6: DOCUMENT GENERATION     │
      │ - Load templates                   │
      │ - Find placeholders                │
      │ - Map answers to fields            │
      │ - Generate DOCX files              │
      │ - order-design-documents/{proj}/   │
      └───────────────────────────────────┘
```

## Component Interactions

### FastAPI Backend (app.py)

**Role:** Orchestrator & REST API

```python
# Upload endpoint triggers pipeline
POST /upload
    ├── Call: doc_extraction_using_di.TransformerDocumentProcessor
    ├── Call: chunk_by_title_semantic_blob.DocumentChunker
    ├── Call: rag_query.process_queries()
    └── Call: doc_filling_blob.DocumentFiller
```

### Module Dependencies

```
app.py (Orchestrator)
├── doc_extraction_using_di.py
│   └── Azure Form Recognizer API
│
├── chunk_by_title_semantic_blob.py
│   └── Needs: DI JSON output
│
├── rag_query.py
│   ├── FAISS (vector search)
│   ├── BM25 (keyword search)
│   ├── OpenAI Embeddings
│   ├── CrossEncoder (reranking)
│   └── Azure OpenAI (GPT-4)
│
└── doc_filling_blob.py
    └── Needs: RAG answers + templates
```

## Azure Services Integration

### Storage Containers

| Container | Purpose | Input | Output |
|-----------|---------|-------|--------|
| `input-document-center` | Raw documents | User uploads | - |
| `output-of-di` | DI extraction results | from Stage 2 | `.json` files |
| `chunked-output` | Document chunks | from Stage 3 | `all_chunks.json` |
| `faiss-indexes` | Vector indexes | from Stage 4 | `.faiss` files |
| `faiss-metadata` | Index metadata | from Stage 4 | `.pkl` files |
| `order-templates` | Template documents | Admin upload | - |
| `order-design-documents` | Generated documents | from Stage 6 | `.docx` files |

### Cognitive Services

| Service | Usage | Stage |
|---------|-------|-------|
| **Document Intelligence** | Extract text, tables, layout | Stage 2 |
| **OpenAI Embeddings** | Convert text to vectors | Stage 4 |
| **OpenAI GPT-4** | Generate answers from context | Stage 5 |
| **AI Search** (optional) | Advanced semantic search | Stage 4-5 |

## Configuration & Parameters

### Document Intelligence
```python
model = "prebuilt-layout"  # Azure DI model
```

### Chunking
```python
min_tokens = 10
max_characters = 4000
new_after_n_chars = 3800
combine_text_under_n_chars = 2000
```

### Vector Search
```python
RETRIEVAL_K = 20              # Initial retrieval
RERANK_TOP_K = 10             # After reranking
BM25_WEIGHT = 0.4
VECTOR_WEIGHT = 0.6

DEEP_DIVE_RETRIEVAL_K = 25    # For null-value retry
DEEP_DIVE_RERANK_TOP_K = 15
DEEP_DIVE_BM25_WEIGHT = 0.3
DEEP_DIVE_VECTOR_WEIGHT = 0.7
```

### RAG
```python
BATCH_SIZE = 6                # Questions per GPT call
CHAT_MODEL = "gpt-4o"
EMBEDDING_MODEL = "text-embedding-3-large"
```

## Error Handling & Resilience

### Duplicate Detection
- MD5 hash of each file
- Within-run deduplication
- Prevents re-processing identical documents

### Already-Processed Skip
- Checks `output-of-di/{project}` for existing outputs
- Skips entire project if found
- Prevents redundant processing

### Image Page Detection
- Pixel variance analysis (>1000 variance threshold)
- Text extraction fallback
- Flags image-heavy pages for manual review

### RAG Null-Value Recovery
- First pass: Standard retrieval weights
- If answer is null → Deep dive pass
- Increased retrieval count (20→25 chunks)
- Adjusted weights (60/40 → 70/30)

## Performance Characteristics

| Operation | Time | Bottleneck |
|-----------|------|-----------|
| Document upload | <1s | Network |
| DI extraction | 5-10s/page | Azure API |
| Chunking | 100MB/min | CPU |
| Indexing | 1-5s | Embedding API |
| Query retrieval | 1-2s | FAISS lookup |
| Reranking | 1s | Model inference |
| GPT generation | 2-5s | Azure OpenAI |
| Document filling | <1s | Template rendering |

## Scalability Considerations

### Horizontal Scaling
- Stateless FastAPI backend
- Process multiple projects in parallel
- Queue-based job management (future)

### Vertical Scaling
- FAISS indexes fit in memory
- Batch processing for large projects
- Incremental indexing support

### Cost Optimization
- Cache embeddings (FAISS)
- Reuse indexes across queries
- Batch DI processing
- Off-peak processing schedules

## Security & Data Privacy

- Azure Storage encryption at rest
- Encryption in transit (HTTPS/TLS)
- API key management via .env
- No data retention in logs (configurable)
- CORS middleware for frontend access

---

**Next:** [Configuration Guide](configuration.md) → Learn how to set up all services
