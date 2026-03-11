RAG Query Module
================

RAG Query Engine - Hybrid Retrieval & Parameter Extraction

Features
--------

- Hybrid search combining BM25 and vector search
- FAISS vector indexing
- Azure OpenAI integration
- Deep-dive search for null values

Usage
-----

.. code-block:: python

    from rag_query import extract_json
    results = extract_json(questions, project_name)

Configuration
-------------

- OPENAI_KEY
- OPENAI_ENDPOINT
- CHAT_MODEL
- EMBEDDING_MODEL

GitHub
------

`View source code <https://github.com/chaitra-bhandari/TransformerRag/blob/main/UI-RAG/rag_query.py>`_
