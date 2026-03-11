============
Architecture
============

Transformer Spec RAG is built on a modular, cloud-native architecture designed for scalability and maintainability.

System Overview
===============

The system consists of three main layers:

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
    │ - DI (Extract)   │ │ - AI Search       │ │ - Blob Storage │
    │ - OpenAI (RAG)   │ │ - FAISS (Local)   │ │ - Containers   │
    └──────────────────┘ └───────────────────┘ └────────────────┘

Core Processing Pipeline
=========================

**1. Document Ingestion**

When a user uploads documents:

.. code-block:: text

    Upload File (PDF/DOCX/XLSX)
             ↓
    FastAPI Endpoint validates
             ↓
    Save to temporary storage
             ↓
    Upload to Azure Blob Storage

**File Validation:**
- Extension check (.pdf, .docx, .xlsx)
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

**Image Page Detection:**

For PDFs, system detects image-heavy pages:
- Convert PDF to images
- Calculate pixel variance
- Flag low-text pages for manual review
- Extract minimal text from images

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

**4. Vector Embedding & FAISS Indexing** (rag_query.py)

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

**5. FAISS Indexing**

Stores vectors in FAISS for fast retrieval:

.. code-block:: text

    Chunks + Vectors
         ↓
    FAISS Index Creation
    - Create index for fast search
    - Use approximate nearest neighbors
    - Store in Azure Blob Storage
    - Backup metadata separately
         ↓
    Ready for queries

**6. Query Processing** (``rag_query.py`` - Core Module)

When user asks a question:

.. code-block:: text

    User Question: "What is the transformer voltage?"
         ↓
    Convert to embedding (same model as chunks)
         ↓
    Search FAISS Index:
    - Fast approximate nearest neighbor search
    - Retrieve top-K results (default: 20)
    - BM25 hybrid search for keyword matching
    - CrossEncoder reranking for relevance
         ↓
    Retrieved Chunks:
    [
      {chunk1: "...rated voltage 400 kV..."},
      {chunk2: "...operating voltage range..."},
      {chunk3: "...voltage regulation..."}
    ]
         ↓
    Pass to RAG model

**7. RAG Generation**

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
    Generated Response:
    "Based on the specifications, the transformer is rated
     for 400 kV nominal voltage with operating range of
     380-420 kV as per document section 2.3..."
         ↓
    Return to user

**Temperature & Sampling:**
- Low temperature (0.3) for factual extraction
- Higher temperature (0.7) for synthesis tasks
- Top-p sampling for diversity control

**8. Document Generation** (``doc_filling_blob.py``)

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

Data Flow Diagram
=================

Complete data journey through the system:

.. code-block:: text

    ┌──────────────────┐
    │  User Upload     │
    │   PDF/DOCX       │
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
    │  Index in Azure AI Search│
    │  - Store vectors         │
    │  - Index metadata        │
    └────────┬─────────────────┘
             │
             ▼ (Ready for queries)
    
    ┌──────────────────────────┐
    │  User Question           │
    │  (Chat Interface)        │
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │  Embed Query             │
    │  (Same embedding model)  │
    └────────┬─────────────────┘
             │
             ▼
    ┌──────────────────────────┐
    │  Semantic Search         │
    │  (AI Search Index)       │
    │  - Top-K retrieval       │
    │  - Metadata filtering    │
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

Database & Storage Architecture
================================

**Azure Blob Storage Containers**

.. code-block:: text

    storage-account/
    ├── transformer-input/              # Raw uploads
    │   ├── ProjectA_onshore/
    │   │   ├── spec1.pdf
    │   │   ├── spec2.docx
    │   │   └── data.xlsx
    │   └── ProjectB_offshore/
    │       └── spec.pdf
    │
    ├── output-of-di/                   # DI extraction results
    │   ├── ProjectA_onshore/
    │   │   ├── spec1_di_result.json
    │   │   └── spec2_di_result.json
    │   └── ProjectB_offshore/
    │       └── spec_di_result.json
    │
    ├── chunked-output/                 # Chunked documents
    │   └── all_chunks.json             # All chunks + metadata
    │
    ├── order-design-documents/         # Generated documents
    │   ├── ProjectA_onshore/
    │   │   ├── Order_A_unit1.docx
    │   │   └── Order_B_unit1.docx
    │   └── ProjectB_offshore/
    │       └── Order_A_unit1.docx
    │
    ├── order-templates/                # Document templates
    │   ├── Order_A.docx
    │   └── Order_B.docx
    │
    └── chunked-output/
        └── all_chunks.json

**FAISS Index Storage Structure**

.. code-block:: text

    storage-account/
    ├── faiss-indexes/                  ← FAISS vector indexes
    │   ├── ProjectA_onshore.index
    │   ├── ProjectA_offshore.index
    │   ├── ProjectB_onshore.index
    │   └── ProjectB_offshore.index
    │
    └── faiss-metadata/                 ← Chunk metadata for lookup
        ├── ProjectA_onshore_metadata.json
        ├── ProjectA_offshore_metadata.json
        ├── ProjectB_onshore_metadata.json
        └── ProjectB_offshore_metadata.json

**FAISS Index Format**

.. code-block:: json

    {
      "embeddings": [
        [0.123, -0.456, 0.789, ...],  // 3072-dim vectors
        [0.234, -0.567, 0.890, ...],
        ...
      ],
      "metadata": [
        {
          "chunk_id": "spec_p1_t123",
          "content": "Specification text...",
          "page": 1,
          "source_document": "spec.pdf"
        },
        ...
      ]
    }

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

Scalability Considerations
==========================

**Vertical Scaling**
- Increase Azure resource SKUs
- Add more API replicas
- Larger AI Search indexes

**Horizontal Scaling**
- Multiple FastAPI instances behind load balancer
- Distributed task queue (Celery) for DI processing
- Caching layer (Redis) for embeddings

**Performance Optimizations**
- Batch embedding processing
- Chunk size optimization
- Index query caching
- Async/await for I/O operations

Security Architecture
=====================

**Layer-Based Security**

.. code-block:: text

    Network Layer
    ├── HTTPS/TLS encryption
    ├── CORS policy enforcement
    └── Rate limiting
    
    Application Layer
    ├── API key validation
    ├── Input validation
    ├── SQL injection prevention
    └── XSS protection
    
    Data Layer
    ├── Azure Storage encryption
    ├── Azure AI Search security
    ├── Credential management
    └── Access control

**Secrets Management**
- Use Azure Key Vault (production)
- .env files (development only)
- Never commit secrets
- Rotate credentials regularly

Module Dependencies
===================

.. code-block:: text

    app.py (main)
    ├── doc_extraction_using_di.py
    │   ├── azure.ai.formrecognizer
    │   ├── pdf2image
    │   └── PyPDF2
    │
    ├── chunk_by_title_semantic_blob.py
    │   └── tiktoken
    │
    ├── rag_query.py
    │   └── openai
    │
    └── doc_filling_blob.py
        └── python-docx

Deployment Architecture
=======================

**Development**
- Local FastAPI server
- Local Blob emulator (optional)
- Cloud AI services

**Staging**
- Docker container on Azure Container Instances
- Azure services (full scale)
- Staging data containers

**Production**
- Azure App Service or Container Instances
- Load balancer
- Auto-scaling based on queue depth
- Backup and disaster recovery
- Monitoring and alerting

See :doc:`deployment` for detailed setup instructions.

Next Steps
==========

- Read :doc:`pipeline_flow` for detailed workflow
- Explore :doc:`modules/index` for module details
- Check :doc:`api/endpoints` for API reference
