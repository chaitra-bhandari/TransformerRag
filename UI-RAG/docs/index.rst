===============================
Transformer Spec RAG
===============================

**A Retrieval-Augmented Generation system for automated transformer specification document processing and analysis.**

.. image:: https://img.shields.io/badge/Python-3.8+-blue.svg
    :target: https://www.python.org/downloads/
.. image:: https://img.shields.io/badge/FastAPI-0.104+-green.svg
    :target: https://fastapi.tiangolo.com/
.. image:: https://img.shields.io/badge/Azure-Cloud-blue.svg
    :target: https://azure.microsoft.com/

Overview
========

Transformer Spec RAG is an intelligent document processing pipeline designed to extract, analyze, and generate transformer specification documents. It combines:

- **Azure Document Intelligence** for advanced document extraction
- **Semantic chunking** for intelligent text segmentation
- **Vector embeddings** for semantic search
- **Retrieval-Augmented Generation** for document synthesis
- **FastAPI** backend with React frontend

The system automates the entire workflow from raw PDF/DOCX uploads to formatted specification documents.

Key Features
============

✅ **Automated Document Extraction** - Uses Azure DI for layout analysis and content extraction
✅ **Intelligent Chunking** - By-title semantic chunking preserves document structure
✅ **Vector Search** - Azure AI Search with embeddings for semantic retrieval
✅ **RAG Pipeline** - Generates specification documents from retrieved chunks
✅ **Document Generation** - Fills templates with extracted transformer specifications
✅ **Web Interface** - React-based chat UI for user interactions
✅ **Azure Integration** - Cloud-native with Blob Storage and AI Search

Architecture
============

.. code-block:: text

    Upload Project
         ↓
    DI Extraction → output-of-di/
         ↓
    Semantic Chunking → chunked-output/
         ↓
    Vector Embedding & Indexing → Azure AI Search
         ↓
    RAG Query Processing → JSON Results
         ↓
    Document Generation → Order Documents (.docx)
         ↓
    User Interface (React) ← FastAPI Backend

Technology Stack
================

**Backend:**
- Python 3.8+
- FastAPI 0.104+
- Azure Document Intelligence
- Azure Blob Storage
- Azure AI Search
- OpenAI GPT-4
- FAISS (Local vector search)

**Frontend:**
- React 18+
- TypeScript
- TailwindCSS

**Infrastructure:**
- Microsoft Azure
- Docker (optional)

Quick Start
===========

1. **Installation**: :doc:`installation`
2. **Configuration**: :doc:`configuration`
3. **Quick Tour**: :doc:`quickstart`
4. **API Reference**: :doc:`api/index`

Documentation Contents
======================

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   installation
   configuration
   quickstart
   environment_setup

.. toctree::
   :maxdepth: 2
   :caption: Architecture & Design

   architecture
   pipeline_flow
   data_models

.. toctree::
   :maxdepth: 2
   :caption: Core Modules

   modules/extraction
   modules/chunking
   modules/rag_query
   modules/document_generation
   modules/api

.. toctree::
   :maxdepth: 2
   :caption: API Documentation

   api/index
   api/endpoints
   api/models

.. toctree::
   :maxdepth: 2
   :caption: Advanced Topics

   azure_integration
   vector_search
   performance_optimization
   troubleshooting

.. toctree::
   :maxdepth: 1
   :caption: Reference

   glossary
   faq
   contributing

System Requirements
====================

**Minimum Requirements:**
- Python 3.8 or higher
- 4GB RAM
- 2GB disk space

**Recommended for Production:**
- Python 3.11+
- 8GB+ RAM
- SSD storage
- Azure subscription

**Required Azure Services:**
- Azure Storage Account (Blob Storage)
- Azure Document Intelligence
- Azure AI Search
- Azure OpenAI or OpenAI API access

Supported File Formats
======================

- **PDF** (.pdf) - Primary format
- **Microsoft Word** (.docx)
- **Excel** (.xlsx)

Maximum file size: 100 MB per document

Use Cases
=========

- **Transformer Specification Processing**: Automated extraction from technical documents
- **Document Standardization**: Convert multiple formats to standardized specifications
- **Specification Generation**: Auto-generate specification documents from templates
- **Technical Analysis**: Query specifications using natural language
- **Compliance Documentation**: Generate order documents with precise parameters

Getting Help
============

- 📖 **Documentation**: Start with :doc:`quickstart`
- 🐛 **Issues**: Check :doc:`troubleshooting`
- ❓ **FAQ**: See :doc:`faq`
- 💬 **Contact**: Reach out to the development team

License & Attribution
======================

This project is built with:
- Azure Document Intelligence (Microsoft Azure)
- OpenAI GPT-4 API
- FastAPI
- React

Version Information
====================

**Current Version:** 1.0.0

**Last Updated:** 2024

**Status:** Production Ready

.. toctree::
   :hidden:

   changelog
