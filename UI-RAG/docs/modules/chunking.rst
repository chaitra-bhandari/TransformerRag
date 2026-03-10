====================
Semantic Chunking
====================

``chunk_by_title_semantic_blob.py``

Intelligently chunks documents while preserving semantic structure and hierarchy.

Overview
========

The Semantic Chunking module transforms extracted documents into optimized chunks for:

- Vector embedding
- Semantic search
- RAG context retrieval
- Efficient processing

**Key Features:**

- ✓ Preserves document structure (headings, sections)
- ✓ Removes noise (headers, footers, page numbers)
- ✓ Maintains hierarchical relationships
- ✓ Handles tables intelligently
- ✓ Optimizes chunk sizes for embedding models
- ✓ Provides rich metadata

Core Class
==========

.. code-block:: python

    class DocumentChunker:
        """Create semantic chunks from extracted documents"""
        
        def __init__(self, min_tokens=10, max_characters=4000, ...):
            # Initialize chunking parameters

Configuration Parameters
=========================

.. code-block:: python

    chunker = DocumentChunker(
        min_tokens=10,                      # Minimum tokens per chunk
        max_characters=4000,                # Maximum chunk size (chars)
        new_after_n_chars=3800,             # Start new chunk after
        combine_text_under_n_chars=2000     # Merge chunks smaller than
    )

**Explanation:**

- ``min_tokens``: Chunks with fewer tokens are discarded (noise filtering)
- ``max_characters``: Hard limit on chunk size
- ``new_after_n_chars``: When to break and start new chunk
- ``combine_text_under_n_chars``: Small chunks merged with next

**Why These Values:**

- OpenAI embeddings: max ~8,191 tokens (~32k characters)
- Typical transformer spec: 4000 chars ≈ 1000 tokens
- Balances: chunk detail vs. search precision
- Smaller chunks → more targeted retrieval
- Larger chunks → more context

Initialization
==============

.. code-block:: python

    from chunk_by_title_semantic_blob import DocumentChunker

    # Create chunker with defaults
    chunker = DocumentChunker()

    # Or customize parameters
    chunker = DocumentChunker(
        min_tokens=5,
        max_characters=3000,
        new_after_n_chars=2800,
        combine_text_under_n_chars=1500
    )

Main Methods
============

**process_all_projects()**

Process all DI results from Azure Blob Storage.

.. code-block:: python

    chunks = chunker.process_all_projects()
    # Returns list of all chunks from all projects

**Returns:**
- List of chunk dictionaries
- Automatically discovers all DI JSON files
- Processes projects in sorted order

**Example:**

.. code-block:: python

    chunker = DocumentChunker()
    all_chunks = chunker.process_all_projects()
    print(f"Created {len(all_chunks)} chunks")
    
    # Chunks are now in memory
    # And stored in self.all_chunks

**process_single_json(json_path, project_name, doc_name)**

Process one DI result file.

.. code-block:: python

    chunks = chunker.process_single_json(
        json_path=Path("output/file_di_result.json"),
        project_name="MyProject_onshore",
        doc_name="specification"
    )

**Parameters:**

- ``json_path`` (Path): Path to DI result JSON
- ``project_name`` (str): Project identifier
- ``doc_name`` (str): Document name (without extension)

**Returns:**
- List of chunk dictionaries for this document

**Workflow:**

1. Load DI result JSON
2. Extract paragraphs and tables
3. Detect page numbering (0-based vs 1-based)
4. Classify headings and structure
5. Apply semantic chunking
6. Return chunks with metadata

**save_chunks(output_blob_name)**

Upload all chunks to Azure Blob Storage.

.. code-block:: python

    chunker.process_all_projects()
    chunker.save_chunks("all_chunks.json")

**Parameters:**
- ``output_blob_name`` (str): Name for output JSON file

**Output:**
- Uploads to configured chunk container
- JSON format with all chunks
- Compressed representation

Chunk Structure
===============

**Chunk Dictionary**

.. code-block:: python

    {
        "chunk_id": "specification_p3_t1704067200000",
        "content": "Technical Specifications: This section covers...",
        "metadata": {
            "source_document": "specification",
            "project_name": "MyProject_onshore",
            "page": 3
        }
    }

**Fields:**

- ``chunk_id``: Unique identifier (document_page_timestamp)
- ``content``: The actual chunk text
- ``metadata``: Source information for retrieval

**Example Chunks:**

.. code-block:: json

    [
      {
        "chunk_id": "spec_p1_t1704067200000",
        "content": "Transformer Specifications: Overview of transformer design and operation",
        "metadata": {
          "source_document": "spec",
          "project_name": "Project_A",
          "page": 1
        }
      },
      {
        "chunk_id": "spec_p2_t1704067201000",
        "content": "Technical Specifications: Voltage 400 kV, Capacity 100 MVA, Cooling ONAN",
        "metadata": {
          "source_document": "spec",
          "project_name": "Project_A",
          "page": 2
        }
      }
    ]

Semantic Structure Preservation
================================

**How Hierarchies Are Maintained**

The chunker uses ``HierarchicalContext`` to track document structure:

.. code-block:: text

    Document Hierarchy:
    ├─ Level 1 (Title): "Transformer Specifications"
    │
    ├─ Level 2 (Heading): "Technical Parameters"
    │  ├─ Level 3: "Voltage Ratings"
    │  │  └─ Text: "Rated voltage: 400 kV..."
    │  │
    │  └─ Level 3: "Current Ratings"
    │     └─ Text: "Rated current: 150 A..."
    │
    └─ Level 2 (Heading): "Operating Conditions"
       └─ Text: "Operating temperature range..."

**Chunking preserves context:**

.. code-block:: text

    Chunk 1: "Technical Parameters: Voltage Ratings: Rated voltage: 400 kV..."
    Chunk 2: "Technical Parameters: Current Ratings: Rated current: 150 A..."
    Chunk 3: "Operating Conditions: Operating temperature range..."
```

Each chunk includes its section context for better retrieval.

Heading Detection
=================

**Numbered Headings**

Automatic detection of numbered section headings:

.. code-block:: text

    "1. Introduction"           → Level 1
    "1.2 Overview"             → Level 2
    "1.2.3 Details"            → Level 3
    "1.2.3.4 Sub-details"      → Level 4

**Role-Based Detection**

Classified by Document Intelligence roles:

.. code-block:: python

    if role in {"title", "sectionHeading", "heading"}:
        level = {"title": 1, "sectionHeading": 2, "heading": 3}[role]

**Text Validation**

Headings must pass text rules:

- Max 80 characters
- Must contain words (not just symbols)
- Cannot start with prose ("The", "A", "This", etc.)
- Cannot be pure numbers or symbols
- Cannot end with period or contain commas

Noise Removal
=============

**Patterns Removed**

The chunker identifies and filters noise:

.. code-block:: python

    # Page numbers
    "1/7"
    "page 5 of 12"
    
    # Document IDs
    "22/10231-12"
    "Doc. no. 21/10231-14"
    
    # Metadata
    "Revision 2.1"
    "Date: 03/15/2024"
    "Version 1.0"
    
    # Headers/Footers
    "ENERGINET"
    "taking power further"
    "CONFIDENTIAL"
    
    # Symbols only
    "-----"
    "====="
    "     "

**Result:** Clean, meaningful chunks without noise

Table Handling
==============

**Table Extraction**

Tables are extracted with structure preserved:

.. code-block:: python

    def _extract_tables(self, tables: List[Dict], page_offset: int):
        # For each table:
        # 1. Get cells (row_index, column_index, content)
        # 2. Reconstruct full rows
        # 3. Format as readable text with pipes
        # 4. Create chunk from table text

**Table Chunk Format**

.. code-block:: text

    Row 1 | Row 2 | Row 3
    --------------------
    Data 1 | Data 2 | Data 3
    Data 4 | Data 5 | Data 6

**Example:**

.. code-block:: text

    Parameter | Value | Unit
    Voltage | 400 | kV
    Current | 150 | A
    Power | 100 | MVA

Token Counting
==============

**Why Token Count Matters**

Tokens are how embeddings work:

- 1 token ≈ 4 characters (rough estimate)
- OpenAI limit: 8,191 tokens
- Minimum meaningful chunk: 10 tokens
- Target chunk: ~1000 tokens

**Token Counting Methods**

.. code-block:: python

    # Method 1: Use tiktoken (accurate)
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    token_count = len(enc.encode(text))
    
    # Method 2: Approximate (fallback)
    token_count = max(1, len(text) // 4)

**Min Token Filter**

.. code-block:: python

    min_tokens = 10  # Discard very small chunks
    
    if token_count < min_tokens:
        skip_chunk()  # Too small, likely noise

Small Chunk Merging
===================

**Problem:** Small chunks lose context

.. code-block:: text

    Without merging:
    Chunk 1: "Section 2.1: Introduction"
    Chunk 2: "This section describes"  ← Too small alone
    Chunk 3: "the operating parameters."

**Solution:** Merge with next section

.. code-block:: text

    After merging:
    Chunk 1: "Section 2.1: Introduction"
    Chunk 2: "Section 2.2: Operating Parameters: This section describes
             the operating parameters."

**Configuration:**

.. code-block:: python

    combine_text_under_n_chars = 2000  # Merge if < 2000 chars
    
    # Example:
    # Small section (1500 chars) + next section → merged chunk

Performance Characteristics
===========================

**Processing Speed**

.. code-block:: text

    100-page document:
    - Loading DI JSON:       ~1 second
    - Noise removal:         ~1 second
    - Heading detection:     ~1 second
    - Chunking:             ~1 second
    - Table extraction:     ~1 second
    ────────────────────
    Total:                  ~5 seconds

**Memory Usage**

.. code-block:: text

    100-page document:
    - DI JSON in memory:    ~20 MB
    - Chunk processing:     ~50 MB
    - Final chunks:         ~10 MB
    
    Peak: ~80 MB

**Output Size**

.. code-block:: text

    Raw document:          ~5 MB
    DI result JSON:        ~20 MB (includes structure)
    Chunks JSON:           ~10 MB (compressed representation)

Example Usage
=============

**Basic Chunking**

.. code-block:: python

    from chunk_by_title_semantic_blob import DocumentChunker

    chunker = DocumentChunker()
    chunks = chunker.process_all_projects()
    chunker.save_chunks()

**Custom Configuration**

.. code-block:: python

    # Smaller chunks for more granular retrieval
    chunker = DocumentChunker(
        min_tokens=5,
        max_characters=2000,
        new_after_n_chars=1800,
        combine_text_under_n_chars=1000
    )
    
    chunks = chunker.process_all_projects()

**Process Single Document**

.. code-block:: python

    from pathlib import Path

    chunker = DocumentChunker()
    
    chunks = chunker.process_single_json(
        json_path=Path("output/spec_di_result.json"),
        project_name="MyProject_onshore",
        doc_name="specification"
    )
    
    print(f"Created {len(chunks)} chunks")

**Filter by Project**

.. code-block:: python

    chunker = DocumentChunker()
    all_chunks = chunker.process_all_projects()
    
    # Get chunks for specific project
    project_chunks = [
        c for c in all_chunks 
        if c['metadata']['project_name'] == 'MyProject_onshore'
    ]

**Analyze Chunks**

.. code-block:: python

    chunker = DocumentChunker()
    chunks = chunker.process_all_projects()
    
    # Statistics
    total_chunks = len(chunks)
    avg_size = sum(len(c['content']) for c in chunks) / total_chunks
    
    print(f"Total chunks: {total_chunks}")
    print(f"Average size: {avg_size:.0f} characters")

Advanced Topics
===============

**Custom Heading Patterns**

Modify the regex pattern for heading detection:

.. code-block:: python

    # In chunk_by_title_semantic_blob.py
    _NUMBERED_HEADING = re.compile(r"^(\d+(?:\.\d+){0,3})[\s.]\s*\S")
    
    # For different numbering schemes:
    # Roman numerals: r"^([IVX]+)\.\s*\S"
    # Letters: r"^([A-Z])\.\s*\S"
    # Custom format: your regex here

**Custom Noise Patterns**

Add domain-specific noise:

.. code-block:: python

    _NOISE_PATTERNS.append(
        re.compile(r"your_pattern_here", re.IGNORECASE)
    )

**Performance Optimization**

For large batches:

.. code-block:: python

    import asyncio
    from concurrent.futures import ThreadPoolExecutor

    async def process_files_parallel(json_files):
        with ThreadPoolExecutor(max_workers=4) as executor:
            tasks = [
                asyncio.to_thread(chunker.process_single_json, ...)
                for f in json_files
            ]
            results = await asyncio.gather(*tasks)
        return results

Troubleshooting
===============

**Issue: Getting too many small chunks**

*Cause:* Minimum tokens threshold too low
*Solution:* Increase min_tokens or combine_text_under_n_chars

.. code-block:: python

    chunker = DocumentChunker(
        min_tokens=20,  # was 10
        combine_text_under_n_chars=3000  # was 2000
    )

**Issue: Chunks missing context**

*Cause:* Headers not properly detected
*Solution:* Check heading classification rules

.. code-block:: python

    # Add debug output
    if h_level is not None:
        print(f"Heading detected: {text} (level {h_level})")

**Issue: Lost tables or important content**

*Cause:* Noise filter too aggressive
*Solution:* Review noise patterns

.. code-block:: python

    if _is_noise(text):
        print(f"Filtered as noise: {text}")  # Debug

**Issue: Memory issues with large documents**

*Cause:* Holding all chunks in memory
*Solution:* Process and save incrementally

.. code-block:: python

    for file in files:
        chunks = chunker.process_single_json(file_path, ...)
        save_to_blob(chunks)  # Don't accumulate in memory

Next Steps
==========

After chunking:

1. :doc:`../modules/rag_query` - Query chunks with RAG
2. :doc:`../modules/api` - Index in Azure AI Search
3. :doc:`../architecture` - Understand the full pipeline
