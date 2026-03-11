RAG Query Module
================

RAG Query Engine - Hybrid Retrieval & Parameter Extraction

A sophisticated system for extracting transformer specifications from documents using
Retrieval-Augmented Generation (RAG) with hybrid search combining vector and keyword-based
retrieval methods.

Features
--------

- Hybrid search combining BM25 (keyword) and vector search (semantic)
- FAISS vector indexing for semantic similarity search
- CrossEncoder re-ranking for improved relevance
- Azure OpenAI integration for LLM-based parameter extraction
- Deep-dive search that automatically searches for null values
- Batch processing of questions for efficient extraction
- ThreadPoolExecutor for parallel processing
- Source attribution and confidence scoring

Usage
-----

.. code-block:: python

    from rag_query import extract_json, extract_with_deep_dive
    
    results = extract_json(questions, project_name)
    results_with_deepdive = extract_with_deep_dive(questions, project_name)

Configuration
-------------

Environment variables required:

- ``OPENAI_KEY`` - Azure OpenAI API key
- ``OPENAI_ENDPOINT`` - Azure OpenAI endpoint URL
- ``CHAT_MODEL`` - LLM model name (default: gpt-4o)
- ``EMBEDDING_MODEL`` - Embedding model name (default: text-embedding-3-large)
- ``AZURE_STORAGE_CONNECTION_STRING`` - Azure Blob Storage connection
- ``BLOB_INDEX_CONTAINER`` - Container for FAISS indexes
- ``BLOB_CHUNK_CONTAINER`` - Container for chunked documents

Search Weights
--------------

**Regular Search:**

- BM25: 40% (exact keyword matching)
- Vector: 60% (semantic similarity)

**Deep Dive Search (for null values):**

- BM25: 30% (less emphasis on exact match)
- Vector: 70% (more emphasis on semantics)

See Source Code
---------------

View the full source code on GitHub: `rag_query.py <https://github.com/chaitra-bhandari/TransformerRag/blob/main/rag_query.py>`_