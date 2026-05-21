============
Architecture
============

Transformer Spec RAG is built on a modular, cloud-native architecture designed for scalability and maintainability.

System Overview
===============

The system consists of four main layers:

.. code-block:: text

    ┌─────────────────────────────────────────────────────────────┐
    │                        Frontend Layer                        │
    │              React Web UI + Chat Interface                  │
    │        (Docflow_chatui.jsx + Index.HTML)                    │
    └──────────────────────────┬──────────────────────────────────┘
                               │ HTTP/WebSocket
    ┌──────────────────────────▼──────────────────────────────────┐
    │                      Backend Layer                          │
    │                    FastAPI Application                      │
    │  (Document Processing, RAG, API Endpoints)                  │
    └──────────────────────────┬──────────────────────────────────┘
                               │
            ┌──────────────────┼──────────────────┐
            ▼                  ▼                  ▼
    ┌──────────────────┐ ┌───────────────────┐ ┌────────────────┐
    │ Azure Services   │ │ Vector Database   │ │ Storage Layer  │
    │ - DI (Extract)   │ │  - FAISS (Local)  │ │ - Blob Storage │
    │ - OpenAI (RAG)   │ │  - BM25 (Keyword) │ │ - Containers   │
    └──────────────────┘ └───────────────────┘ └────────────────┘

    ───────────────── Offline Quality Layer ─────────────────
    ┌─────────────────────────────────────────────────────────────┐
    │              evaluate_with_ragas.py (Standalone)            │
    │  RAGAS metrics · Azure OpenAI judge LLM · Azure embeddings  │
    │  Input: manual_test_cases.json → Output: CSV / JSON / TXT   │
    └─────────────────────────────────────────────────────────────┘

Core Processing Pipeline
=========================

**1. Document Ingestion**

When a user uploads documents:

.. code-block:: text

    Upload File (PDF)
             ↓
    FastAPI Endpoint validates
             ↓
    Save to temporary storage
             ↓
    Upload to Azure Blob Storage

**File Validation:**
- Extension check (.pdf)
- Size validation (max 100 MB)
- Content type verification
- Duplicate detection (MD5 hash)

**2. Document Extraction** (``doc_extraction_using_di.py``)

Azure Document Intelligence extracts structure:

.. code-block:: text

    Raw Document
         ↓
    Azure Document Intelligence (Prebuilt Layout)
         ↓
    Structural Analysis:
    - Page detection
    - Paragraph extraction
    - Table identification
    - Role classification (heading, text, etc.)
         ↓
    DI Result JSON
         ↓
    Saved to output-of-di container

**Key Outputs:**
- ``pages``: Page metadata and numbering
- ``paragraphs``: Text content with roles and positions
- ``tables``: Structured table data with cells
- ``bounding_regions``: Spatial coordinates

**3. Semantic Chunking** (``chunk_by_title_semantic_blob.py``)

Intelligently splits documents while preserving structure:

.. code-block:: text

    DI Output
         ↓
    Noise Removal:
    - Strip headers/footers
    - Remove page numbers
    - Filter document metadata
         ↓
    Structure Analysis:
    - Identify section headings (numbered and by role)
    - Build hierarchical context
    - Track heading levels (1-4)
         ↓
    Smart Chunking:
    - Group text under headings
    - Respect max size (4000 chars)
    - Create new chunk after 3800 chars
    - Merge small chunks (< 2000 chars)
         ↓
    Chunk Objects:
    {
      "chunk_id": "doc_p3_t123",
      "content": "Section heading: paragraph text...",
      "metadata": {
        "source_document": "specification.pdf",
        "project_name": "Transformer_A",
        "page": 3
      }
    }

**Chunking Strategy:**

.. code-block:: text

    Section 1: Transformer Basics (500 chars)
    ├─ Chunk 1: "Transformer Basics: These devices... ratings..."
    │
    Section 2: Technical Specifications (3500 chars)
    ├─ Chunk 2: "Technical Specifications: Voltage... capacity..."
    ├─ Chunk 3: "...thermal limits... efficiency measurements..."
    │
    Section 3: Operating Parameters (1500 chars)
    └─ Chunk 3: "Operating Parameters: (merged with previous)..."

**Noise Patterns Removed:**
- Page numbers: "1/7", "page 5 of 12"
- Document IDs: "22/10231-12"
- Revision markers: "Revision 2.1"
- Company headers: "ENERGINET"
- Footer text: "taking power further"

**4. Vector Embedding & FAISS Indexing** (``rag_query.py``)

Converts chunks to semantic vectors and stores in FAISS:

.. code-block:: text

    Chunks (text)
         ↓
    OpenAI Embeddings API
    (text-embedding-3-large, 3072 dimensions)
         ↓
    Vector representations
    (numerical vectors capturing semantic meaning)
         ↓
    FAISS Index Creation
    (Fast Approximate Nearest Neighbor Search)
         ↓
    Stored in Azure Blob Storage
         ↓
    Ready for semantic search queries

**Embedding Process:**

.. code-block:: python

    chunk_text = "Technical Specifications: Voltage 400 kV, capacity 100 MVA..."

    # Convert to vector (3072 dimensions)
    vector = openai_embeddings.embed_query(chunk_text)

    # Store in index
    search_index.upload_documents([{
        'id': 'chunk_123',
        'content': chunk_text,
        'content_vector': vector,
        'metadata': {...}
    }])

**FAISS Storage:**

- Index file (``.index``) → fast approximate nearest neighbor search
- Metadata pickle (``.pkl``) → chunk lookup by id
- Both stored in Azure Blob Storage for persistence

**5. Query Processing** (``rag_query.py`` - Core Module)

When user asks a question:

.. code-block:: text

    User Question: "Generate order design documents"
         ↓
    Convert to embedding (same model as chunks)
         ↓
    Hybrid Search:
    - FAISS vector search (top-K = 20)
    - BM25 keyword search
    - Weighted combination (vector 0.6 / BM25 0.4)
    - CrossEncoder reranking → top 10
         ↓
    Retrieved Chunks:
    [
      {chunk1: "...rated voltage 400 kV..."},
      {chunk2: "...operating voltage range..."},
      {chunk3: "...voltage regulation..."}
    ]
         ↓
    Pass to RAG model

**6. RAG Generation**

Uses OpenAI GPT-4 to synthesize answer:

.. code-block:: text

    Retrieved Chunks (Context)
         ↓
    Construct Prompt:
    System: "You are a transformer specification expert..."
    Context: "[Retrieved chunk 1]\n[Retrieved chunk 2]..."
    Question: "What is the transformer voltage?"
         ↓
    OpenAI GPT-4 Processing
         ↓
    Generated results as JSON
         ↓
    JSON used to fill documents
         ↓
    Return to user

**Temperature & Sampling:**
- Low temperature (0.3) for factual extraction
- Higher temperature (0.7) for synthesis tasks
- Top-p sampling for diversity control

**7. Document Generation** (``doc_filling_blob.py``)

Creates output .docx files:

.. code-block:: text

    Generated Specifications + Templates
         ↓
    Parameter Extraction:
    - Parse specifications
    - Extract key values
    - Map to template fields
         ↓
    Template Filling:
    - Load Order_A.docx or Order_B.docx template
    - Replace placeholders with extracted values
    - Maintain formatting
         ↓
    Document Generation:
    - Create output document
    - Validate content
    - Upload to blob storage
         ↓
    User Download:
    order-design-documents/Order_A_filled.docx

**Template Processing:**

.. code-block:: text

    Template: "{{TRANSFORMER_NAME}}: {{RATED_VOLTAGE}} kV"
    Parameters: {
      "TRANSFORMER_NAME": "Unit-01",
      "RATED_VOLTAGE": "400"
    }
    Output: "Unit-01: 400 kV"

**8. Quality Evaluation** (``evaluate_with_ragas.py``)

Runs offline, separate from the live request path. Measures how well the RAG
system retrieves relevant contexts and generates correct answers.

.. code-block:: text

    manual_test_cases.json
       (question, contexts, answer, ground_truth)
            ↓
    Validate & normalize each test case
       (skip items missing required fields)
            ↓
    Build RAGAS Dataset
            ↓
    Initialize Azure OpenAI components:
       ├─ Judge LLM (gpt-4o-mini, temperature=0)
       └─ Embeddings (text-embedding-3-large)
            ↓
    Run four RAGAS metrics:
       ├─ context_recall      (are relevant chunks present?)
       ├─ context_precision   (are retrieved chunks actually relevant?)
       ├─ faithfulness        (is the answer grounded in context?)
       └─ answer_correctness  (does the answer match ground truth?)
            ↓
    Display per-parameter scores in terminal
            ↓
    Write three timestamped reports:
       ├─ ragas_evaluation_detailed_<ts>.csv
       ├─ ragas_results_<ts>.json
       └─ ragas_summary_<ts>.txt

**Why a separate pipeline?**

- Evaluation is **offline**: it should not slow down live user requests.
- Each test case fires multiple judge LLM calls (one per metric). Running this
  inline would multiply per-request latency and cost.
- Test cases are curated manually and versioned independently of production traffic.

Data Flow Diagram
=================

Complete data journey through the system:

.. code-block:: text

    ┌──────────────────┐
    │  User Upload     │
    │      PDF         │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────────────┐
    │  FastAPI Upload Handler  │
    │  - Validate file         │
    │  - Check duplicates      │
    │  - Save to temp          │
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │  Upload to Blob Storage  │
    │  (input container)       │
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │  Document Intelligence   │
    │  Extraction Process      │
    │  - Layout analysis       │
    │  - Content extraction    │
    │  - Table detection       │
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │  Save DI Results JSON    │
    │  (output-of-di)          │
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │  Semantic Chunking       │
    │  - Remove noise          │
    │  - Identify sections     │
    │  - Create chunks         │
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │  Generate Embeddings     │
    │  (OpenAI Embeddings API) │
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │  Index in FAISS          │
    │    (stored in blob)      │
    │  - Store vectors         │
    │  - Index metadata        │
    └────────┬─────────────────┘
             │
             ▼ (Ready for document generation)

    ┌──────────────────────────┐
    │  User Question           │
    │ (Generate order document)│
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │  Embed Queries           │
    │  (Same embedding model)  │
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │  Semantic+keyword search │
    │  (FAISS Search Index)    │
    │  - Top-K retrieval       │
    │  - Metadata filtering    │
    │  - CrossEncoder reranking│
    │   for relevance          │
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │  RAG Processing          │
    │  (GPT-4)                 │
    │  - Build context         │
    │  - Generate response     │
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │  Document Generation     │
    │  (Template filling)      │
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │  Save to Blob Storage    │
    │  (order-design-docs)     │
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │  User Download           │
    │  Final .docx Document    │
    └──────────────────────────┘

**Offline Evaluation Flow** (separate from live request path):

.. code-block:: text

    ┌──────────────────────────┐
    │ manual_test_cases.json   │
    │ (curated test cases)     │
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │ evaluate_with_ragas.py   │
    │ - Validate items         │
    │ - Build RAGAS Dataset    │
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │ Azure OpenAI             │
    │ - Judge LLM              │
    │ - Embeddings             │
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │ RAGAS metrics            │
    │ - context_recall         │
    │ - context_precision      │
    │ - faithfulness           │
    │ - answer_correctness     │
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │ Reports (local files)    │
    │ - detailed CSV           │
    │ - results JSON           │
    │ - summary TXT            │
    └──────────────────────────┘

Database & Storage Architecture
================================

**Azure Blob Storage Containers**

.. code-block:: text

    storage-account/
    ├── transformer-input/              # Raw uploads
    │   ├── ProjectA/
    │   │   ├── spec1.pdf
    │   │   ├── spec2.docx
    │   │   └── data.xlsx
    │   └── ProjectB/
    │       └── spec.pdf
    │
    ├── output-of-di/                   # DI extraction results
    │   ├── ProjectA/
    │   │   ├── spec1_di_result.json
    │   │   └── spec2_di_result.json
    │   └── ProjectB/
    │       └── spec_di_result.json
    │
    ├── chunked-output/                 # Chunked documents
    │   └── all_chunks.json             # All chunks + metadata
    │
    ├── order-design-documents/         # Generated documents
    │   ├── ProjectA/
    │   │   ├── Order_A_unit1.docx
    │   │   └── Order_B_unit1.docx
    │   └── ProjectB/
    │       └── Order_A_unit1.docx
    │
    └── order-templates/                # Document templates
        ├── Order_A.docx
        └── Order_B.docx

**FAISS Index Storage Structure**

.. code-block:: text

    storage-account/
    ├── faiss-indexes/                  ← FAISS vector indexes
    │   └── docs.index
    │
    └── faiss-metadata/                 ← Chunk metadata for lookup
        └── docs.pkl

**FAISS Index Format**

.. code-block:: json

    {
      "embeddings": [
        [0.123, -0.456, 0.789, ...],
        [0.234, -0.567, 0.890, ...]
      ],
      "metadata": [
        {
          "chunk_id": "spec_p1_t123",
          "content": "Specification text...",
          "page": 1,
          "source_document": "spec.pdf"
        }
      ]
    }

**Evaluation Output (Local Filesystem)**

``evaluate_with_ragas.py`` writes its reports to the **current working directory**
(not Blob Storage), since evaluation is an operator workflow rather than a
production artifact:

.. code-block:: text

    project-root/
    ├── ragas_evaluation_detailed_<timestamp>.csv   # Per-parameter scores
    ├── ragas_results_<timestamp>.json              # Full metrics + summary
    └── ragas_summary_<timestamp>.txt               # Human-readable report

For long-term tracking, copy these files into a versioned ``evaluation/`` folder
or upload them to a dedicated Blob container.

API Layer Architecture
======================

**FastAPI Endpoints**

.. code-block:: text

    /upload                 → POST  (File upload & trigger DI)
    /query                  → POST  (RAG query)
    /generate-document      → POST  (Fill templates)
    /list-projects          → GET   (Project listing)
    /project-status         → GET   (Processing status)
    /download/{doc_id}      → GET   (Download document)
    /health                 → GET   (Health check)

.. note::

    The RAGAS evaluation script is **not** exposed as an API endpoint. It runs
    standalone from the command line because it is operator-driven and
    long-running. If you need scheduled or on-demand evaluation via the API,
    wrap ``evaluate_with_ragas.main()`` in a background task (Celery, FastAPI
    ``BackgroundTasks``, or an Azure Function).

**Authentication & Security**

.. code-block:: text

    Headers:
    ├── X-API-Key: {API_KEY}  # API key validation
    │
    CORS Middleware
    ├── Allowed origins (configurable)
    ├── Allowed methods (GET, POST, PUT, DELETE)
    └── Credential handling

**Error Handling**

.. code-block:: text

    Exception → HTTP Status
    ├── ValidationError → 400 Bad Request
    ├── Unauthorized → 401 Unauthorized
    ├── Forbidden → 403 Forbidden
    ├── NotFound → 404 Not Found
    ├── Duplicate → 409 Conflict
    └── ServerError → 500 Internal Server Error

Frontend Architecture
=====================

**React Application Structure**

.. code-block:: text

    /frontend
    ├── src/
    │   ├── components/
    │   │   ├── Docflow_chatui.jsx      # Chat interface
    │   │   ├── UploadPanel.jsx         # File upload
    │   │   └── ResultsPanel.jsx        # Display results
    │   │
    │   ├── hooks/
    │   │   ├── useApi.js               # API calls
    │   │   └── useChat.js              # Chat state
    │   │
    │   ├── services/
    │   │   └── api.js                  # API client
    │   │
    │   └── App.jsx                     # Main component
    │
    └── Index.HTML                      # HTML entry point

**Component Communication**

.. code-block:: text

    User Input (React)
           ↓
    useApi Hook (HTTP)
           ↓
    FastAPI Backend
           ↓
    Process (DI, Chunking, RAG)
           ↓
    FastAPI Response (JSON)
           ↓
    Update React State
           ↓
    Render Results (JSX)
           ↓
    Display to User


Next Steps
==========

- Read :doc:`source_code` and :doc:`modules` for detailed documentation
- See :doc:`evaluate_with_ragas` for RAGAS evaluation setup
