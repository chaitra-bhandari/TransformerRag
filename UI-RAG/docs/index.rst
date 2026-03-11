Transformer Spec RAG Documentation
==================================

Welcome to **Transformer Spec RAG** — an AI-powered document extraction and specification generation system using Retrieval-Augmented Generation (RAG).

This documentation provides complete information about the system architecture, module guides, API reference, and usage instructions.

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
   :caption: Core Modules

   modules/document-extraction
   modules/semantic-chunking
   modules/rag-query-engine
   modules/document-filling
   modules/fastapi-backend

.. toctree::
   :maxdepth: 2
   :caption: API Reference

   app
   rag_query
   doc_extraction_using_di
   chunk_by_title_semantic_blob
   doc_filling_blob

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

The system processes transformer specification documents through a multi-stage pipeline:

1. **Document Extraction** — Azure Document Intelligence extracts content from PDFs, DOCX, and XLSX files
2. **Semantic Chunking** — Intelligent chunking by title with noise removal and proper metadata
3. **Vector Indexing** — FAISS vector search combined with BM25 hybrid retrieval
4. **RAG Query** — Uses Azure OpenAI to extract specific transformer parameters
5. **Document Generation** — Fills Word templates with extracted data

Key Features
~~~~~~~~~~~~

- ✅ Automatic document processing pipeline
- ✅ Hybrid search (vector + keyword retrieval)
- ✅ Deep-dive search for null values
- ✅ Duplicate file detection
- ✅ Image page detection
- ✅ Azure Blob Storage integration
- ✅ FastAPI backend with CORS support
- ✅ Real-time processing status updates

Quick Links
~~~~~~~~~~~

- **Getting Started**: :doc:`getting-started`
- **Installation Guide**: :doc:`installation`
- **API Reference**: :doc:`api/app`
- **Configuration**: :doc:`configuration`
- **Troubleshooting**: :doc:`troubleshooting`

Project Structure
~~~~~~~~~~~~~~~~~

.. code-block:: text

   transformer-spec-rag/
   ├── docs/                          # Documentation (this folder)
   ├── app.py                         # FastAPI backend
   ├── doc_extraction_using_di.py    # Document extraction module
   ├── chunk_by_title_semantic_blob.py  # Chunking module
   ├── rag_query.py                   # RAG query engine
   ├── doc_filling_blob.py           # Document filling module
   ├── Docflow_chatui.jsx            # React frontend
   ├── requirements.txt               # Python dependencies
   ├── .env.example                   # Example environment variables
   └── .readthedocs.yaml             # ReadTheDocs configuration

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

For issues, questions, or contributions, please visit the project repository.

.. note::

   This documentation is automatically generated from the source code using Sphinx and hosted on ReadTheDocs.
   For the latest version, visit the main repository.
