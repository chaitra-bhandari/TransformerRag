===========
Source Code
===========

Complete source code reference for all modules in the Transformer Spec RAG system.

Project Structure
=================

.. code-block:: text

    transformer-spec-rag/
    ├── app.py                              # FastAPI application
    ├── rag_query.py                        # RAG query engine (CORE)
    ├── doc_extraction_using_di.py          # Document Intelligence
    ├── chunk_by_title_semantic_blob.py     # Semantic chunking
    ├── doc_filling_blob.py                 # Document generation
    ├── evaluate_with_ragas.py              # RAGAS evaluation pipeline
    ├── Docflow_chatui.jsx                  # React chat interface
    ├── Index.HTML                          # Frontend HTML
    └── .env.template                       # Environment variables

Core Modules
============

Core Modules
============



1. **app.py** — FastAPI Backend
   - Exposes three REST API endpoints: project creation, pipeline status polling, and order document download
   - Handles PDF file uploads, request routing, and CORS configuration for the React frontend

2. **rag_query.py** — RAG Query Engine *(Most Important)*
   - Hybrid retrieval combining FAISS dense vector search (60%) and BM25 keyword search (40%)
   - Reranks candidates using BAAI/bge-reranker-large and extracts parameters via GPT-4o as structured JSON
   - Supports English and German documents with a deep dive fallback for null values

3. **doc_extraction_using_di.py** — Document Processing
   - Processes uploaded PDFs through Azure Document Intelligence (prebuilt-layout model)
   - Extracts text, tables, and layout information with duplicate file detection via MD5 hash

4. **chunk_by_title_semantic_blob.py** — Semantic Chunking
   - Segments content under hierarchical headings into 2000–4000 character chunks
   - Preserves tables as atomic units, removes noise, and tags each chunk with project metadata

5. **doc_filling_blob.py** — Document Generation
   - Maps extracted JSON parameters into project-specific DOCX templates
   - Appends source attribution table linking every value to its source document and page number

6. **Docflow_chatui.jsx** — React Frontend
   - Single-page application for project creation, document upload, and pipeline status monitoring
   - Polls backend every 10 seconds and provides one-click download of the generated DOCX

7. **evaluate_with_ragas.py** — RAGAS Evaluation
   - Evaluates four metrics: Answer Correctness, Context Precision, Context Recall, and Faithfulness
   - Uses GPT-4o-mini as judge and exports results in CSV, JSON, and text formats


Key Source Files
================

rag_query.py (Core Module)
--------------------------

**This is the most important file in the system.**

Main components:

.. code-block:: python

    # Configuration
    OPENAI_KEY = os.getenv("OPENAI_KEY", "")
    OPENAI_ENDPOINT = os.getenv("OPENAI_ENDPOINT", "")
    CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o")
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    
    # Search weights
    BM25_WEIGHT = 0.4           # Keyword search
    VECTOR_WEIGHT = 0.6         # Vector search
    
    # Parameters
    RETRIEVAL_K = 20            # Initial retrieval
    RERANK_TOP_K = 10           # Final results
    
    # Batch processing
    BATCH_SIZE = 6              # Questions per batch

**Key Functions:**

.. code-block:: python

    def detect_document_language(db, project_name: str) -> str:
        """Auto-detect German or English documents"""
    
    def build_parameter_registry(p: str, language: str = "en") -> dict:
        """Build structured questions for parameters"""
    
    def search_faiss(query_embedding, k: int = RETRIEVAL_K):
        """FAISS vector search"""
    
    def search_bm25(query: str, k: int = RETRIEVAL_K):
        """BM25 keyword search"""
    
    def rerank_with_crossencoder(query, chunks):
        """CrossEncoder reranking for relevance"""
    
    def generate_with_gpt4(query, context, language):
        """OpenAI GPT-4 response generation"""
    
    def rag_query(query: str, project_name: str, language: str = "en"):
        """Complete RAG pipeline"""

**Technology Stack:**

.. code-block:: python

    import faiss                    # Vector search
    from openai import AzureOpenAI  # GPT-4 API
    from rank_bm25 import BM25Okapi # Keyword search
    from sentence_transformers import CrossEncoder  # Reranking
    import numpy as np              # Numerical computing

See: :doc:`modules/rag_query` for complete source code and documentation

app.py (FastAPI Backend)
------------------------

**Main API application**

.. code-block:: python

    from fastapi import FastAPI, UploadFile, File, Form, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    
    app = FastAPI(title="Transformer Spec RAG", version="1.0.0")
    
    # CORS configuration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://localhost:8000"],
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

**Main Endpoints:**

.. code-block:: python

    @app.post("/upload")
    async def upload_project(
        project_folder: str = Form(...),
        files: List[UploadFile] = File(...)
    ):
        """Upload documents for a project"""
    
    @app.post("/query")
    async def query_documents(
        question: str,
        project_folder: str
    ):
        """RAG query on documents"""
    
    @app.post("/generate-document")
    async def generate_document(
        project_folder: str,
        template: str,
        parameters: dict
    ):
        """Generate specification document"""
    
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""



doc_extraction_using_di.py
--------------------------

**Azure Document Intelligence Integration**

.. code-block:: python

    from azure.ai.formrecognizer import DocumentAnalysisClient
    from azure.storage.blob import BlobServiceClient
    
    class TransformerDocumentProcessor:
        def __init__(self):
            self.di_client = DocumentAnalysisClient(...)
            self.blob_client = BlobServiceClient.from_connection_string(...)
        
        def process_project(self, project_folder: str):
            """Process all files in project"""
        
        def process_with_di(self, local_path: str, file_info: Dict):
            """Run Azure Document Intelligence"""
        
        def detect_image_pages(self, pdf_path: str) -> List[int]:
            """Detect image-heavy pages"""

**Output Structure:**

.. code-block:: json

    {
      "pages": [...],
      "paragraphs": [...],
      "tables": [...],
      "spans": [...]
    }

See: :doc:`modules/extraction` for complete documentation

chunk_by_title_semantic_blob.py
-------------------------------

**Semantic Chunking Implementation**

.. code-block:: python

    import re
    import tiktoken
    
    class HierarchicalContext:
        """Track document structure hierarchy"""
    
    class DocumentChunker:
        def __init__(
            self,
            min_tokens: int = 10,
            max_characters: int = 4000,
            new_after_n_chars: int = 3800,
            combine_text_under_n_chars: int = 2000,
        ):
            """Initialize chunking parameters"""
        
        def process_single_json(self, json_path, project_name, doc_name):
            """Process DI result JSON"""
        
        def _extract_tables(self, tables, page_offset):
            """Extract table content"""

**Output Format:**

.. code-block:: python

    {
        "chunk_id": "spec_p3_t1704067200000",
        "content": "Section heading: paragraph text...",
        "metadata": {
            "source_document": "specification.pdf",
            "project_name": "Transformer_A",
            "page": 3
        }
    }

See: :doc:`modules/chunking` for complete documentation

doc_filling_blob.py
-------------------

**Document Template Filling**

.. code-block:: python

    from docx import Document
    from docx.shared import Pt, RGBColor
    
    class DocumentFiller:
        def __init__(self):
            """Initialize document filler"""
        
        def fill_template(
            self,
            template_path: str,
            parameters: dict,
            output_path: str
        ):
            """Fill template with parameters"""
        
        def extract_parameters(self, json_data: dict):
            """Extract parameters from JSON"""
        
        def upload_to_blob(self, local_path: str, blob_path: str):
            """Upload generated document"""

**Template Variables:**

.. code-block:: text

    {{TRANSFORMER_NAME}}
    {{RATED_VOLTAGE}}
    {{RATED_CAPACITY}}
    {{COOLING_METHOD}}
    {{VECTOR_GROUP}}
    {{IMPEDANCE}}
    {{FREQUENCY}}
    {{EFFICIENCY}}

evaluate_with_ragas.py
----------------------

**RAGAS-based Evaluation Pipeline**

Evaluates the quality of the RAG system by running RAGAS metrics against a set of
test cases (question, retrieved contexts, generated answer, ground truth). Uses
Azure OpenAI both as the judge LLM and as the embeddings provider.

.. code-block:: python

    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import (
        context_recall,
        context_precision,
        faithfulness,
        answer_correctness,
    )
    from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

**Configuration:**

.. code-block:: python

    INPUT_FILE = "manual_test_cases.json"  # Test cases (list of dicts)
    
    OPENAI_KEY = ""                         # Azure OpenAI key
    OPENAI_ENDPOINT = ""                    # Azure endpoint
    CHAT_MODEL = "gpt-4o-mini"              # Judge LLM
    EMBEDDING_MODEL = "text-embedding-3-large"  # Embeddings

**Key Functions:**

.. code-block:: python

    def convert_to_string(value, separator="\n"):
        """Normalize a value (str | list | None) to a stripped string."""
    
    def validate_item(item):
        """Validate a single test-case dict.
        Returns (is_valid, normalized_item, error_msg).
        """
    
    def main():
        """Run the 8-step evaluation pipeline:
        validate credentials -> load JSON -> validate items ->
        build Dataset -> init Azure judge & embeddings ->
        run RAGAS metrics -> display results -> save reports.
        """

**Input Format:**

.. code-block:: json

    [
      {
        "param_name": "rated_voltage",
        "question": "What is the rated voltage of the transformer?",
        "contexts": ["The transformer is rated at 132 kV..."],
        "answer": "132 kV",
        "ground_truth": "132 kV"
      }
    ]

**Metrics Evaluated:**

- ``context_recall`` — Are all relevant chunks present in contexts?
- ``context_precision`` — Are the retrieved chunks actually relevant?
- ``faithfulness`` — Is the answer grounded in the contexts?
- ``answer_correctness`` — Does the answer match the ground truth?

All scored 0.0 (worst) to 1.0 (best).

**Output Files (timestamped per run):**

.. code-block:: text

    ragas_evaluation_detailed_<timestamp>.csv    # Per-parameter scores
    ragas_results_<timestamp>.json               # Full results + summary
    ragas_summary_<timestamp>.txt                # Human-readable summary

**Running the Evaluation:**

.. code-block:: bash

    # Set credentials in the script, then:
    python evaluate_with_ragas.py

See: :doc:`evaluate_with_ragas` for complete documentation

Docflow_chatui.jsx
-------------------

**React Chat Interface**

.. code-block:: jsx

    import React, { useState } from 'react';
    import axios from 'axios';
    
    function DocflowChatUI() {
        const [messages, setMessages] = useState([]);
        const [input, setInput] = useState('');
        const [projectFolder, setProjectFolder] = useState('');
        
        const handleSendMessage = async () => {
            // Send query to backend
            const response = await axios.post('/query', {
                question: input,
                project_folder: projectFolder
            });
            
            // Display response
            setMessages([...messages, response.data]);
        };
        
        const handleFileUpload = async (files) => {
            // Upload files to backend
            const formData = new FormData();
            formData.append('project_folder', projectFolder);
            files.forEach(file => formData.append('files', file));
            
            await axios.post('/upload', formData);
        };
        
        return (
            <div>
                <ChatMessages messages={messages} />
                <FileUpload onUpload={handleFileUpload} />
                <InputBox value={input} onChange={setInput} onSend={handleSendMessage} />
            </div>
        );
    }

Index.HTML
----------

**Frontend HTML Structure**

.. code-block:: html

    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Transformer Spec RAG</title>
        <link rel="stylesheet" href="styles.css">
    </head>
    <body>
        <div id="root"></div>
        <script src="react.js"></script>
        <script src="app.js"></script>
    </body>
    </html>

Dependencies
============

**Required Packages**

.. code-block:: bash

    # FastAPI & Web
    fastapi>=0.104.0
    uvicorn[standard]>=0.24.0
    
    # Azure Services
    azure-storage-blob>=12.18.0
    azure-ai-formrecognizer>=3.3.0
    
    # Vector Search & ML
    faiss-cpu>=1.7.4
    openai>=1.3.0
    rank-bm25>=0.2.0
    sentence-transformers>=2.0.0
    
    # Document Processing
    pdf2image>=1.16.0
    PyPDF2>=3.0.0
    python-docx>=0.8.11
    
    # Evaluation (RAGAS)
    ragas>=0.1.0
    datasets>=2.14.0
    langchain-openai>=0.0.5
    pandas>=2.0.0
    
    # Utilities
    numpy>=1.24.0
    python-dotenv>=1.0.0
    tiktoken>=0.5.0

Configuration Files
===================

**.env Template**

.. code-block:: bash

    # Azure Services
    AZURE_STORAGE_CONNECTION_STRING=...
    
    # OpenAI
    OPENAI_KEY=...
    OPENAI_ENDPOINT=...
    CHAT_MODEL=gpt-4o
    
    # FAISS Search
    BLOB_INDEX_CONTAINER=faiss-indexes
    BLOB_METADATA_CONTAINER=faiss-metadata
    VECTOR_SEARCH_K=20
    RERANK_TOP_K=10
    BM25_WEIGHT=0.4
    VECTOR_WEIGHT=0.6
    
    # Application
    API_KEY=...
    DEBUG=false

Data Flow
=========

**Complete Pipeline with Source Code**

.. code-block:: text

    User Input (Docflow_chatui.jsx)
              ↓
    FastAPI (app.py)
              ↓
    doc_extraction_using_di.py (if upload)
              ↓
    chunk_by_title_semantic_blob.py (if chunking)
              ↓
    rag_query.py (Core Query Engine)
       ├─ FAISS search
       ├─ BM25 search
       ├─ CrossEncoder reranking
       └─ GPT-4 generation
              ↓
    doc_filling_blob.py (if generation)
              ↓
    FastAPI (app.py)
              ↓
    Response to Frontend

    ─── Offline Quality Loop ───
    evaluate_with_ragas.py
       ├─ Loads test cases (JSON)
       ├─ Runs RAGAS metrics with Azure OpenAI
       └─ Outputs CSV / JSON / summary reports

Key Implementation Details
==========================

**FAISS Integration (rag_query.py)**

.. code-block:: python

    import faiss
    
    # Load FAISS index
    index = faiss.read_index("index.faiss")
    
    # Search
    distances, indices = index.search(query_vector, k=20)
    
    # Results
    for i, idx in enumerate(indices[0]):
        chunk = metadata[idx]
        print(f"Score: {distances[0][i]}")
        print(f"Content: {chunk['content']}")

**Hybrid Search (rag_query.py)**

.. code-block:: python

    # Vector search
    vector_scores = faiss_search(query_embedding, k=20)
    
    # Keyword search
    bm25_scores = bm25.get_scores(query.split())
    
    # Combine with weights
    final_scores = BM25_WEIGHT * bm25_scores + VECTOR_WEIGHT * vector_scores
    
    # Rerank with CrossEncoder
    cross_scores = crossencoder.predict([(query, chunk) for chunk in top_chunks])

**RAG Generation (rag_query.py)**

.. code-block:: python

    # Build context
    context = "\n".join([chunk['content'] for chunk in top_chunks])
    
    # Generate with GPT-4
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a transformer expert..."},
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {query}"}
        ],
        temperature=0.3
    )

**RAGAS Evaluation (evaluate_with_ragas.py)**

.. code-block:: python

    # Build Dataset from validated test cases
    dataset = Dataset.from_list([
        {
            "question": item["question"],
            "contexts": item["contexts"],
            "answer": item["answer"],
            "ground_truth": item["ground_truth"],
        }
        for item in prepared
    ])
    
    # Initialize Azure judge + embeddings
    judge_llm = AzureChatOpenAI(
        azure_endpoint=OPENAI_ENDPOINT,
        api_key=OPENAI_KEY,
        api_version="2024-02-15-preview",
        model=CHAT_MODEL,
        temperature=0,
    )
    embeddings = AzureOpenAIEmbeddings(
        azure_endpoint=OPENAI_ENDPOINT,
        api_key=OPENAI_KEY,
        api_version="2024-02-15-preview",
        model=EMBEDDING_MODEL,
    )
    
    # Run the four RAGAS metrics
    result = evaluate(
        dataset=dataset,
        metrics=[context_recall, context_precision, faithfulness, answer_correctness],
        llm=judge_llm,
        embeddings=embeddings,
    )

Module Relationships
====================

.. code-block:: text

    app.py (Entry Point)
    ├── Calls: doc_extraction_using_di.py
    │   └── Outputs: DI JSON
    │
    ├── Calls: chunk_by_title_semantic_blob.py
    │   └── Outputs: Chunks JSON
    │
    ├── Calls: rag_query.py (CORE)
    │   ├── Uses: FAISS
    │   ├── Uses: BM25
    │   ├── Uses: CrossEncoder
    │   └── Uses: OpenAI GPT-4
    │
    └── Calls: doc_filling_blob.py
        └── Outputs: .docx file

    evaluate_with_ragas.py (Standalone / Offline)
    ├── Reads: test cases JSON
    ├── Uses: RAGAS
    ├── Uses: Azure OpenAI (judge + embeddings)
    └── Outputs: CSV, JSON, and summary reports

Development Tips
================

**Debugging rag_query.py**

.. code-block:: python

    # Enable verbose logging
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Test individual components
    from rag_query import (
        search_faiss,
        search_bm25,
        rerank_with_crossencoder,
        generate_with_gpt4
    )
    
    # Test FAISS search
    results = search_faiss(query_embedding, k=20)
    print(f"FAISS results: {results}")
    
    # Test BM25
    scores = search_bm25(query, k=20)
    print(f"BM25 scores: {scores}")

**Testing API Endpoints**

.. code-block:: bash

    # Health check
    curl http://localhost:8000/health
    
    # Query
    curl -X POST http://localhost:8000/query \
      -H "X-API-Key: your_key" \
      -H "Content-Type: application/json" \
      -d '{"question": "What is the voltage?", "project_folder": "ProjectA"}'

**Running RAGAS Evaluation**

.. code-block:: bash

    # Make sure Azure credentials are set in evaluate_with_ragas.py
    python evaluate_with_ragas.py
    
    # Inspect results
    ls ragas_*
    # ragas_evaluation_detailed_<timestamp>.csv
    # ragas_results_<timestamp>.json
    # ragas_summary_<timestamp>.txt

Performance Considerations
==========================

**rag_query.py Optimization**

- FAISS search: ~100ms for 1M vectors
- BM25 search: ~10ms for 10K documents
- CrossEncoder reranking: ~50ms for 20 chunks
- GPT-4 generation: ~2-5 seconds

**Tuning for Speed**

.. code-block:: python

    # Faster
    RETRIEVAL_K = 5
    RERANK_TOP_K = 3
    
    # More thorough
    RETRIEVAL_K = 50
    RERANK_TOP_K = 20

**evaluate_with_ragas.py Throughput**

- Each test case triggers multiple judge LLM calls (one per metric)
- Typical cost: ~4–8 Azure OpenAI calls per item
- A 25-item run takes ~3–5 minutes on ``gpt-4o-mini``
- To speed up: reduce the number of metrics, or use a smaller judge model

Next Steps
==========

- :doc:`modules/rag_query` - Complete RAG module documentation
- :doc:`evaluate_with_ragas` - RAGAS evaluation documentation
- :doc:`api/endpoints` - API implementation
- :doc:`architecture` - System overview
- :doc:`quickstart` - Get started

All source code is included in the project and fully documented!
