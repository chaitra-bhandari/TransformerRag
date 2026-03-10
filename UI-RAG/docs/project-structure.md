# Project Structure

## Directory Layout

Here's the actual project structure:

```
UI-COMPLETE/
├── .env                              # Environment variables (credentials)
├── .venv/                            # Python virtual environment
├── app.py                            # FastAPI backend
├── chunk_by_title_semantic_blob.py   # Semantic chunking module
├── doc_extraction_using_di.py        # Azure DI extraction
├── doc_filling_blob.py               # Document template filling
├── rag_query.py                      # RAG query engine
├── Docflow_chatui.jsx                # React chat UI component
│
├── static/                           # Static files (served by FastAPI)
│   └── Index.HTML                    # Web interface
│
├── temp_uploads/                     # Temporary upload directory
│   └── (transient files)
│
├── extracted_json/                   # DI extraction outputs (local cache)
│   └── (JSON files from Document Intelligence)
│
├── UI-complete/                      # Frontend build output
│   └── (React build files)
│
├── myenv/                            # Alternative virtual environment
├── myenv1/                           # Another virtual environment
├── __pycache__/                      # Python cache files
│
└── (Azure Blob Storage containers - cloud)
    ├── input-document-center         # Raw uploads
    ├── output-of-di                  # DI results
    ├── chunked-output                # Document chunks
    ├── faiss-indexes                 # Vector indexes
    ├── faiss-metadata                # Index metadata
    ├── order-templates               # Order templates
    └── order-design-documents        # Generated documents
```

## Core Python Modules

### 1. app.py
**FastAPI Backend & Orchestrator**
- REST API endpoints
- Request handling
- Background task processing
- Static file serving
- CORS middleware

**Key endpoints:**
- `POST /upload` - Upload documents
- `GET /status/{project}` - Check progress
- `GET /results/{project}` - Get answers
- `GET /download/{project}/{file}` - Download documents

### 2. doc_extraction_using_di.py
**Azure Document Intelligence**
- Extract text from PDFs/DOCX/XLSX
- Table extraction
- Page detection
- Duplicate file detection
- Saves JSON results to Azure Blob

**Main class:** `TransformerDocumentProcessor`

### 3. chunk_by_title_semantic_blob.py
**Semantic Chunking Engine**
- Split DI output into chunks
- Remove document noise
- Identify section headings
- Extract tables
- Token-aware splitting

**Main class:** `DocumentChunker`

### 4. rag_query.py
**RAG Query Engine**
- Build FAISS vector indexes
- BM25 keyword search
- Hybrid retrieval (60% semantic, 40% keyword)
- Cross-Encoder reranking
- GPT-4 answer generation

**Main class:** `RAGPipeline`

### 5. doc_filling_blob.py
**Document Filling & Generation**
- Load DOCX templates
- Find placeholders
- Fill with RAG answers
- Save generated documents

**Main class:** `DocumentFiller`

### 6. Docflow_chatui.jsx
**React Chat UI Component**
- Document upload interface
- Project management
- Query chat interface
- Results display
- Language selection

**Integrated into:** `static/Index.HTML`

## Frontend Files

### static/Index.HTML
**Web Interface**
- Contains React app
- Chat UI component (Docflow_chatui.jsx)
- Project management
- Document viewer
- Results display

**Served by:** FastAPI at `http://localhost:8000/`

## Local Storage Directories

### temp_uploads/
**Temporary files during processing**
- Downloaded PDFs (before DI)
- DI results (before chunking)
- FAISS indexes (during building)
- Automatically cleaned up

**Note:** Transient - files don't persist between sessions

### extracted_json/
**Local cache of DI results**
- JSON outputs from Document Intelligence
- Used for debugging
- Can be cleaned periodically

**Location:** Local filesystem (not Azure)

### UI-complete/
**React build output**
- Built frontend files
- Static assets
- Served by FastAPI's `StaticFiles` middleware

## Environment Setup

### .env File
**Contains all credentials** (KEEP SECRET!)

```env
# Azure
AZURE_DI_ENDPOINT=...
AZURE_DI_API_KEY=...
AZURE_STORAGE_CONNECTION_STRING=...
OPENAI_ENDPOINT=...
OPENAI_KEY=...

# App
API_KEY=...
API_PORT=8000

# Models
CHAT_MODEL=gpt-4o
EMBEDDING_MODEL=text-embedding-3-large
```

**Location:** Root directory (`UI-COMPLETE/.env`)

### Virtual Environments
**Multiple Python environments:**
- `.venv/` - Primary environment (use this one)
- `myenv/` - Alternative
- `myenv1/` - Another alternative

**Use:** `.venv` for consistency

## Cloud Storage (Azure Blob)

### Input Container
```
input-document-center/
├── ProjectName_onshore/
│   ├── spec1.pdf
│   └── spec2.docx
└── ProjectName_offshore/
    └── spec.pdf
```

### Output Containers
```
output-of-di/
├── ProjectName_onshore/
│   ├── spec1_di_result.json
│   └── spec2_di_result.json
└── ProjectName_offshore/
    └── spec_di_result.json

chunked-output/
└── all_chunks.json

faiss-indexes/
├── ProjectName_onshore_index.faiss
└── ProjectName_offshore_index.faiss

faiss-metadata/
├── ProjectName_onshore_metadata.pkl
└── ProjectName_offshore_metadata.pkl

order-templates/
├── Order_A.docx
└── Order_B.docx

order-design-documents/
├── ProjectName_onshore_offshore/
│   ├── Order_A.docx
│   └── Order_B.docx
└── (more projects...)
```

## File Sizes & Cleanup

### Safe to Delete
- `temp_uploads/` - Recreated automatically
- `extracted_json/` - Cached, can rebuild
- `__pycache__/` - Recreated on import
- `myenv/`, `myenv1/` - Not used

### Keep
- `.env` - Your credentials
- All `.py` files - Source code
- `static/Index.HTML` - Frontend
- `.venv/` - Active environment

## Typical Workflow

```
1. User uploads files
   ↓
2. app.py receives POST /upload
   ↓
3. Files → temp_uploads/ (temporary)
   ↓
4. app.py calls doc_extraction_using_di.py
   ↓
5. Files processed, moved to Azure Blob
   ↓
6. DI results → extracted_json/ (local cache) & output-of-di/ (Azure)
   ↓
7. app.py calls chunk_by_title_semantic_blob.py
   ↓
8. Chunks → chunked-output/ (Azure)
   ↓
9. app.py calls rag_query.py (builds indexes)
   ↓
10. Indexes → faiss-indexes/ & faiss-metadata/ (Azure)
    ↓
11. app.py calls rag_query.py (query)
    ↓
12. Answers → results JSON
    ↓
13. app.py calls doc_filling_blob.py
    ↓
14. Filled docs → order-design-documents/ (Azure)
    ↓
15. User downloads results
    ↓
16. temp_uploads/ cleaned up (optional)
```

## Quick Reference

| What | Where | Type |
|------|-------|------|
| Backend | app.py | Python |
| DI Module | doc_extraction_using_di.py | Python |
| Chunking | chunk_by_title_semantic_blob.py | Python |
| RAG | rag_query.py | Python |
| Filling | doc_filling_blob.py | Python |
| Frontend | Docflow_chatui.jsx | React |
| Web UI | static/Index.HTML | HTML |
| Credentials | .env | Config |
| Temp files | temp_uploads/ | Local |
| Cache | extracted_json/ | Local |
| Environment | .venv/ | Virtual |

## How to Organize for Deployment

**For GitHub & ReadTheDocs:**

```
UI-COMPLETE/
├── .env                    # Added to .gitignore!
├── .gitignore             # Ignore: .venv, myenv, temp_uploads, __pycache__
├── README.md
├── requirements.txt       # List all pip packages
├── mkdocs.yml            # (for documentation)
├── docs/                 # (your documentation)
├── app.py
├── chunk_by_title_semantic_blob.py
├── doc_extraction_using_di.py
├── doc_filling_blob.py
├── rag_query.py
├── Docflow_chatui.jsx
├── static/
│   └── Index.HTML
└── .readthedocs.yml      # (for ReadTheDocs)
```

### Create .gitignore

```
# Virtual environments
.venv/
myenv/
myenv1/
venv/

# Cache
__pycache__/
*.pyc
*.pyo

# Temporary files
temp_uploads/
extracted_json/
*.log

# Secrets
.env

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
```

---

**Next:** [Getting Started](getting-started.md) with your actual project structure
