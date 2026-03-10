=======
Modules
=======

Core modules that power the RAG pipeline.

Module Overview
===============

Transformer Spec RAG is composed of specialized modules, each handling a specific stage of the pipeline:

.. code-block:: text

    1. Document Extraction (doc_extraction_using_di.py)
       └─ Extract content using Azure Document Intelligence
    
    2. Semantic Chunking (chunk_by_title_semantic_blob.py)
       └─ Intelligently split documents while preserving structure
    
    3. RAG Query Processing (rag_query.py)
       └─ Retrieve relevant chunks and generate responses
    
    4. Document Generation (doc_filling_blob.py)
       └─ Fill templates with extracted specifications
    
    5. FastAPI Application (app.py)
       └─ HTTP API and orchestration

Module Architecture
===================

.. image:: /_static/modules.png
    :align: center
    :alt: Module dependency graph

Core Modules
============

.. toctree::
   :maxdepth: 2

   modules/extraction
   modules/chunking
   modules/rag_query
   modules/document_generation
   modules/api

Module Interaction Flow
=======================

**Pipeline Execution**

.. code-block:: text

    FastAPI (app.py)
    ├── Orchestrates entire pipeline
    │
    ├─→ doc_extraction_using_di.py
    │   └─ Extracts paragraphs, tables, metadata
    │
    ├─→ chunk_by_title_semantic_blob.py
    │   └─ Creates semantic chunks
    │
    ├─→ openai embeddings (via app.py)
    │   └─ Generates vectors
    │
    ├─→ Azure AI Search (via app.py)
    │   └─ Indexes chunks
    │
    ├─→ rag_query.py
    │   └─ Retrieves and synthesizes
    │
    └─→ doc_filling_blob.py
        └─ Generates .docx files

Usage Patterns
==============

**Pattern 1: Sequential Pipeline**

.. code-block:: python

    from doc_extraction_using_di import TransformerDocumentProcessor
    from chunk_by_title_semantic_blob import DocumentChunker

    # Extract
    processor = TransformerDocumentProcessor()
    processor.process_project("MyProject_onshore")

    # Chunk
    chunker = DocumentChunker()
    chunks = chunker.process_all_projects()

**Pattern 2: Custom RAG Query**

.. code-block:: python

    from rag_query import RAGQueryProcessor

    rag = RAGQueryProcessor()
    result = rag.query(
        question="Extract specifications",
        project_folder="MyProject_onshore"
    )

**Pattern 3: Document Generation**

.. code-block:: python

    from doc_filling_blob import DocumentFiller

    filler = DocumentFiller()
    filler.fill_template(
        template="Order_A.docx",
        parameters={"voltage": "400 kV"},
        output_path="Order_A_filled.docx"
    )

Class Hierarchy
===============

.. code-block:: text

    BaseProcessor (abstract)
    ├── TransformerDocumentProcessor
    │   └─ Handles DI extraction
    │
    ├── DocumentChunker
    │   └─ Performs semantic chunking
    │
    ├── RAGQueryProcessor
    │   └─ Processes RAG queries
    │
    └── DocumentFiller
        └─ Fills templates

Dependency Graph
================

.. code-block:: text

    External Libraries
    ├── azure-ai-formrecognizer
    │   └─ doc_extraction_using_di
    │
    ├── azure-storage-blob
    │   ├─ doc_extraction_using_di
    │   ├─ chunk_by_title_semantic_blob
    │   ├─ doc_filling_blob
    │   └─ app.py
    │
    ├── azure-search-documents
    │   └─ app.py
    │
    ├── openai
    │   ├─ rag_query.py
    │   └─ app.py
    │
    └── python-docx
        └─ doc_filling_blob

Error Handling Strategy
=======================

Each module implements consistent error handling:

.. code-block:: python

    try:
        result = module_function()
        return {"success": True, "data": result}
    except ValidationError as e:
        return {"success": False, "error": str(e), "type": "validation"}
    except AzureError as e:
        return {"success": False, "error": str(e), "type": "azure"}
    except Exception as e:
        return {"success": False, "error": str(e), "type": "unknown"}

Configuration Management
=========================

All modules read from environment variables:

.. code-block:: python

    import os
    from dotenv import load_dotenv

    load_dotenv()

    # Azure configuration
    AZURE_CONN_STR = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    AZURE_DI_KEY = os.getenv("AZURE_DI_API_KEY")
    OPENAI_KEY = os.getenv("OPENAI_KEY")

Module Testing Strategy
=======================

**Unit Tests** - Test individual functions

.. code-block:: python

    def test_chunk_creation():
        chunker = DocumentChunker()
        chunks = chunker.process_single_json(...)
        assert len(chunks) > 0
        assert chunks[0]["metadata"]["page"] > 0

**Integration Tests** - Test module interactions

.. code-block:: python

    def test_extraction_to_chunking():
        processor = TransformerDocumentProcessor()
        processor.process_project("TestProject")
        
        chunker = DocumentChunker()
        chunks = chunker.process_all_projects()
        assert len(chunks) > 0

**End-to-End Tests** - Test full pipeline

.. code-block:: bash

    pytest tests/e2e/ -v --tb=short

Performance Characteristics
===========================

**Processing Times (per 100-page document)**

.. code-block:: text

    Extraction:    ~30 seconds  (Azure DI)
    Chunking:      ~5 seconds   (semantic analysis)
    Embedding:     ~20 seconds  (API calls)
    Indexing:      ~10 seconds  (AI Search)
    ──────────────────────────
    Total:         ~65 seconds

**Memory Usage**

.. code-block:: text

    Extraction:    ~500 MB      (PDF conversion)
    Chunking:      ~200 MB      (JSON + processing)
    Embedding:     ~100 MB      (batch processing)
    Vector Search: ~1 GB        (index)

**API Response Times**

.. code-block:: text

    Query embedding:   ~200 ms
    Vector search:     ~100 ms
    RAG processing:    ~2-5 seconds
    Total query:       ~2.5-5.5 seconds

Module Configuration Options
=============================

**Chunking Parameters**

.. code-block:: python

    chunker = DocumentChunker(
        min_tokens=10,              # Minimum tokens per chunk
        max_characters=4000,        # Maximum chunk size
        new_after_n_chars=3800,     # Start new chunk after
        combine_text_under_n_chars=2000  # Merge small chunks
    )

**Embedding Parameters**

.. code-block:: python

    embedding_config = {
        "model": "text-embedding-3-large",
        "dimensions": 3072,
        "batch_size": 100
    }

**RAG Parameters**

.. code-block:: python

    rag_config = {
        "top_k": 10,                 # Retrieve top 10 chunks
        "temperature": 0.3,          # Lower = more factual
        "max_tokens": 1000           # Max response length
    }

Module Best Practices
=====================

**1. Error Handling**
- Always wrap Azure calls in try-except
- Log errors with context
- Return consistent error objects

**2. Resource Management**
- Close files and connections properly
- Use context managers (with statements)
- Clean up temporary files

**3. Configuration**
- Use environment variables
- Validate on initialization
- Fail fast with clear errors

**4. Logging**
- Log major operations
- Include timestamps
- Track performance metrics

**5. Documentation**
- Document public APIs
- Include type hints
- Provide usage examples

Extending Modules
=================

**Adding a New Module**

.. code-block:: python

    # new_module.py
    class CustomProcessor:
        def __init__(self, config=None):
            self.config = config or {}
            self._validate_config()
        
        def _validate_config(self):
            """Validate required configuration"""
            pass
        
        def process(self, input_data):
            """Main processing function"""
            try:
                # Implementation
                pass
            except Exception as e:
                raise ProcessingError(str(e))

**Integrating with Pipeline**

.. code-block:: python

    # app.py
    from new_module import CustomProcessor

    @app.post("/custom-endpoint")
    async def custom_endpoint(request: RequestModel):
        processor = CustomProcessor()
        result = processor.process(request.data)
        return result

Module Maintenance
==================

**Dependencies**
- Keep dependencies up to date
- Monitor security advisories
- Test with new versions

**Performance**
- Profile regularly
- Optimize bottlenecks
- Monitor cloud resource usage

**Compatibility**
- Test with different Python versions
- Verify Azure SDK compatibility
- Check OpenAI API versions

Next Steps
==========

Explore individual modules:

- :doc:`modules/extraction` - Document Intelligence integration
- :doc:`modules/chunking` - Semantic chunking algorithm
- :doc:`modules/rag_query` - RAG processing
- :doc:`modules/document_generation` - Template filling
- :doc:`modules/api` - FastAPI endpoints

See :doc:`api/index` for complete API reference.
