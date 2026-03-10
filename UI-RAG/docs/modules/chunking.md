# Semantic Chunking Module

## Overview

The Semantic Chunking module intelligently splits document text into chunks optimized for RAG retrieval.

**Module:** `chunk_by_title_semantic_blob.py`

**Main Class:** `DocumentChunker`

## Key Features

### 1. Smart Chunking by Title
- Groups content under section headings
- Maintains semantic coherence
- Respects document hierarchy

### 2. Noise Removal
Automatically filters out:
- Page numbers ("1/7", "page 5 of 12")
- Document numbers ("Doc. no. 22/10231-12")
- Headers and footers
- Revision/date information
- Company names and watermarks

### 3. Structured Heading Detection
- Numbered headings (1, 1.1, 1.1.1)
- Role-based headings (title, sectionHeading)
- Automatic level hierarchy

### 4. Table Extraction
- Tables extracted as separate chunks
- Cell content preserved with structure
- Deduplication within document

## API Reference

### DocumentChunker

```python
from chunk_by_title_semantic_blob import DocumentChunker

chunker = DocumentChunker(
    min_tokens=10,                      # Minimum chunk tokens
    max_characters=4000,                # Maximum chunk size
    new_after_n_chars=3800,             # Create new chunk threshold
    combine_text_under_n_chars=2000,    # Combine small sections
)
```

**Parameters:**
- `min_tokens` (int): Minimum tokens to create chunk. Smaller chunks discarded.
- `max_characters` (int): Maximum characters per chunk
- `new_after_n_chars` (int): Create new chunk when this size reached
- `combine_text_under_n_chars` (int): Combine sections under this size

### Methods

#### `process_all_projects() → List[Dict]`

Process all DI JSON files from Azure Blob:

```python
chunker = DocumentChunker()
chunks = chunker.process_all_projects()

print(f"Created {len(chunks)} chunks")
for chunk in chunks[:5]:
    print(f"- {chunk['metadata']['source_document']} (page {chunk['metadata']['page']})")
```

**Returns:** List of chunk dicts:
```python
{
    "chunk_id": "spec_p1_t123456",
    "content": "Full chunk text...",
    "metadata": {
        "source_document": "spec",
        "project_name": "Energinet_onshore",
        "page": 1
    }
}
```

#### `process_single_json(json_path, project_name, doc_name) → List[Dict]`

Process a single DI JSON file:

```python
from pathlib import Path

json_file = Path("output-of-di/MyProject/spec_di_result.json")
chunks = chunker.process_single_json(json_file, "MyProject", "spec")

print(f"Created {len(chunks)} chunks from single file")
```

#### `save_chunks(output_blob_name: str = "all_chunks.json")`

Upload all chunks to Azure Blob:

```python
chunker.process_all_projects()
chunker.save_chunks("all_chunks.json")

# Or custom name
chunker.save_chunks("chunks_v2.json")
```

**Uploads to:** `chunked-output/{filename}` in Azure Blob Storage

### Internal Classes

#### HierarchicalContext

Tracks document section hierarchy:

```python
ctx = HierarchicalContext()
ctx.update(level=1, text="Introduction", page=1)
ctx.update(level=2, text="Background", page=2)
ctx.get(level=1)  # Returns "Introduction"
```

## Usage Examples

### Basic Processing

```python
from chunk_by_title_semantic_blob import DocumentChunker

# Initialize with default settings
chunker = DocumentChunker()

# Process all DI JSON files
chunks = chunker.process_all_projects()

# Save to blob storage
chunker.save_chunks()

print(f"✓ Created and saved {len(chunks)} chunks")
```

### Custom Configuration

```python
# Dense chunking (more, smaller chunks)
chunker = DocumentChunker(
    min_tokens=5,
    max_characters=2000,
    new_after_n_chars=1800,
)

chunks = chunker.process_all_projects()

# Sparse chunking (fewer, larger chunks)
chunker = DocumentChunker(
    min_tokens=20,
    max_characters=6000,
    new_after_n_chars=5500,
)

chunks = chunker.process_all_projects()
```

### Single Project Processing

```python
from pathlib import Path
import json

chunker = DocumentChunker()

# Process one project's DI files
json_path = Path("temp/Energinet_onshore_di_result.json")
chunks = chunker.process_single_json(
    json_path,
    project_name="Energinet",
    doc_name="Energinet_spec"
)

# Examine chunks
for chunk in chunks:
    print(f"Chunk: {chunk['chunk_id']}")
    print(f"Content length: {len(chunk['content'])} chars")
    print(f"Page: {chunk['metadata']['page']}")
```

### Analyze Chunking Results

```python
chunker = DocumentChunker()
chunks = chunker.process_all_projects()

# Statistics
total_chars = sum(len(c['content']) for c in chunks)
avg_chars = total_chars / len(chunks)

print(f"Total chunks: {len(chunks)}")
print(f"Total characters: {total_chars}")
print(f"Avg chunk size: {avg_chars:.0f} chars")

# By source document
by_doc = {}
for chunk in chunks:
    doc = chunk['metadata']['source_document']
    by_doc[doc] = by_doc.get(doc, 0) + 1

for doc, count in sorted(by_doc.items()):
    print(f"  {doc}: {count} chunks")
```

## Chunking Strategy

### By-Title Semantic Approach

```
Document
  ├─ Heading 1: "Section A"
  │   ├─ Para 1
  │   ├─ Para 2
  │   ├─ Para 3   ← Chunk 1: "Section A: Para 1 Para 2 Para 3"
  │   └─ Para 4   ← Chunk 2: "Section A: Para 4"
  │
  ├─ Heading 2: "Section B"
  │   ├─ Para 5
  │   └─ Para 6   ← Chunk 3: "Section B: Para 5 Para 6"
```

### Token-Based Splitting

Uses OpenAI's `cl100k_base` encoding (GPT-3.5/4):

```python
import tiktoken
enc = tiktoken.get_encoding("cl100k_base")
tokens = len(enc.encode("Your text"))

# Typical conversions:
# 1 token ≈ 4 characters
# 10 tokens ≈ 40 characters
# 100 tokens ≈ 400 characters
```

## Output Format

### Chunk Structure

```json
{
  "chunk_id": "filename_p1_t1234567890",
  "content": "Section Title: Full paragraph text...",
  "metadata": {
    "source_document": "spec",
    "project_name": "Energinet_onshore",
    "page": 1
  }
}
```

### All Chunks JSON

```json
[
  {
    "chunk_id": "spec_p1_t123",
    "content": "1. Introduction: ...",
    "metadata": {...}
  },
  {
    "chunk_id": "spec_p2_t456",
    "content": "1.1 Background: ...",
    "metadata": {...}
  },
  ...
]
```

Saved to: `chunked-output/all_chunks.json`

## Noise Pattern Examples

Patterns automatically removed:

```
✓ Removed: "1/7" (page number)
✓ Removed: "page: 5 of 12"
✓ Removed: "Doc. no. 22/10231-12"
✓ Removed: "Revision: 2.1"
✓ Removed: "Date: 01/06/2024"
✓ Removed: "ENERGINET"
✓ Removed: "Confidential"
✓ Removed: "taking power further"
✓ Removed: "version: 1.0"

✓ Kept: "Section 2: Technical Specifications"
✓ Kept: "The transformer has a rated voltage of 110 kV"
✓ Kept: "Loss at rated load: 150 kW"
```

## Heading Detection

### Automatic Classification

| Text | Detected As | Level |
|------|------------|-------|
| "1" | Numbered | 1 |
| "1.2" | Numbered | 2 |
| "1.2.3" | Numbered | 3 |
| "1.2.3.4" | Numbered | 4 |
| "Introduction" (title role) | Title | 1 |
| "Section" (sectionHeading) | Section | 2 |
| "Subsection" (heading) | Heading | 3 |

## Performance Optimization

### Fast Processing

```python
chunker = DocumentChunker(
    min_tokens=5,              # Lower threshold
    max_characters=5000,       # Larger chunks
    combine_text_under_n_chars=500,  # Aggressive combining
)
```

### Quality Over Speed

```python
chunker = DocumentChunker(
    min_tokens=20,             # Higher threshold
    max_characters=2000,       # Smaller chunks
    combine_text_under_n_chars=1000,  # Less combining
)
```

## Troubleshooting

### Too Many Tiny Chunks

**Problem:** Lots of chunks under 10 tokens

**Solution:** Reduce `min_tokens`
```python
chunker = DocumentChunker(min_tokens=5)
```

### Chunks Too Large for Embeddings

**Problem:** Some chunks exceed 8000 tokens

**Solution:** Reduce `max_characters`
```python
chunker = DocumentChunker(max_characters=2000)
```

### Headings Missing from Chunks

**Problem:** Section headings not appearing in content

**Solution:** Check heading classification in DI output
- Verify `role` field is set correctly
- May need to manually adjust `_HEADING_ROLES`

### Tables Not Extracted

**Problem:** Tables missing from chunks

**Solution:**
- Check DI JSON contains tables
- Verify `table_id` deduplication logic

## Configuration Recommendations

| Document Type | min_tokens | max_chars | new_after |
|--------------|-----------|-----------|-----------|
| **Dense specs** | 15 | 3000 | 2800 |
| **General text** | 10 | 4000 | 3800 |
| **Tables heavy** | 5 | 2000 | 1800 |
| **Sparse docs** | 20 | 5000 | 4500 |

---

**Next:** [RAG Query Engine](rag-query.md) → Use chunks for retrieval
