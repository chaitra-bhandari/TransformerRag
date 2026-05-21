Transformer Spec RAG Documentation
==================================


An AI-powered system that automates technical parameter extraction from
power transformer customer specification documents using
Retrieval-Augmented Generation (RAG).

Engineers previously spent ~2 working days per project manually locating
parameters across PDFs, DOCX, and Excel files. This system ingests the
documents, retrieves relevant passages, and generates filled order design
documents — with every extracted value linked back to its source document
and page number.

----

Documentation Overview
----------------------

- **System Architecture** — End-to-end pipeline from document upload to order document generation
- **Module Guides** — Document parsing, chunking, hybrid retrieval, reranking, LLM extraction, and template population
- **API Reference** — Endpoint specifications for integration and programmatic use
- **Usage Instructions** — Environment setup, pipeline execution, and output interpretation


.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   getting-started
   installation
   quickstart

.. toctree::
   :maxdepth: 2
   :caption: Architecture & Design

   architecture
   pipeline
   system-overview

.. toctree::
   :maxdepth: 2
   :caption: Source Code

   modules
   source_code

.. toctree::
   :maxdepth: 2
   :caption: Configuration

   configuration
   environment-variables
   azure-setup

.. toctree::
   :maxdepth: 2
   :caption: Troubleshooting & Support

   troubleshooting
   faq

Overview
--------

The system processes power transformer customer specification documents through a multi-stage pipeline:

1. **Document Extraction** — Azure Document Intelligence extracts text, tables, and layout from uploaded PDF files
2. **Semantic Chunking** — By-Title chunking strategy with 2000–4000 character chunks, noise removal, and project-level metadata tagging
3. **Vector Indexing** — text-embedding-3-large embeddings indexed in FAISS, combined with BM25 for hybrid retrieval across English and German documents
4. **RAG Query** — Parameter registry, reranked by BAAI/bge-reranker-large, extracted via GPT-4o as structured JSON
5. **Document Generation** — Extracted parameters populate standardised DOCX templates with full source and page attribution per parameter
6. **Evaluation** — RAGAS framework with GPT-4o-mini as judge assesses Answer Correctness, Context Precision, Context Recall, and Faithfulness

Key Features
~~~~~~~~~~~~

- ✅ Automatic document processing pipeline
- ✅ Hybrid search (vector + keyword retrieval)
- ✅ Deep-dive search for null values
- ✅ Duplicate file detection
- ✅ Azure Blob Storage integration
- ✅ FastAPI backend
- ✅ Real-time processing status updates
- ✅ RAGAS evaluation with 4 quality metrics (faithfulness, answer correctness, context recall & precision)

Quick Links
~~~~~~~~~~~


- **Getting Stared**: :doc:`installation`
- **Quick Start**: :doc:`quickstart`
- **Source Code**: :doc:`source_code`
- **All Modules**: :doc:`modules`
- **Evaluation**: :doc:`evaluate_with_ragas`
- **Troubleshooting**: :doc:`troubleshooting`

Project Structure
~~~~~~~~~~~~~~~~~

.. code-block:: text

   transformer-spec-rag/
   ├── docs/                              # Documentation (this folder)
   ├── app.py                             # FastAPI backend
   ├── doc_extraction_using_di.py         # Document extraction module
   ├── chunk_by_title_semantic_blob.py    # Chunking module
   ├── rag_query.py                       # RAG query engine
   ├── doc_filling_blob.py                # Document filling module
   ├── evaluate_with_ragas.py             # RAGAS evaluation pipeline
   ├── Docflow_chatui.jsx                 # React frontend
   ├── requirements.txt                   # Python dependencies
   ├── .env.example                       # Example environment variables
   └── .readthedocs.yaml                  # ReadTheDocs configuration
Installation
~~~~~~~~~~~~

To get started quickly:

.. code-block:: bash

   # Clone the repository
   git clone https://github.com/yourusername/transformer-spec-rag.git
   cd transformer-spec-rag

   # Install dependencies
   pip install -r requirements.txt

   # Configure environment
   cp .env.example .env
   # Edit .env with your Azure credentials

   # Run the application
   python -m uvicorn app:app --reload

Support & Contact
~~~~~~~~~~~~~~~~~

For issues, questions, contact chaitrabhandati@gmail.com

