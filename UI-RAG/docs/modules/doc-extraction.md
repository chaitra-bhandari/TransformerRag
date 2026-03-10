# Document Extraction Module (Azure DI)

## Overview

The Document Extraction module uses **Azure Document Intelligence (Form Recognizer)** to extract structured data from raw documents (PDFs, DOCX, XLSX).

**Module:** `doc_extraction_using_di.py`

**Main Class:** `TransformerDocumentProcessor`

## What It Does

```
Raw Document (PDF/DOCX/XLSX)
        ↓
    [Download to temp]
        ↓
    [Duplicate check]
        ↓
    [Image detection] (PDF only)
        ↓
    [Azure DI prebuilt-layout]
        ↓
    Extract: paragraphs, tables, layout
        ↓
    Save JSON result
        ↓
    Upload to: output-of-di/{project}/
```

## Key Features

### 1. Automatic Page Number Normalization

Some DI systems use 0-based indexing, others use 1-based:

```python
# Detector automatically converts:
0-based: [page 0, page 1, page 2]
   ↓
1-based: [page 1, page 2, page 3]
```

### 2. Duplicate File Detection

Prevents re-processing identical files:

```python
# Each file is hashed (MD5)
# If same hash seen before → SKIP
# Saves API calls and time
```

### 3. Image Page Detection

Flags pages that are mostly images:

```python
# Pixel variance analysis:
# High variance (>1000) → image-heavy
# Low variance  (<1000) → mostly text
```

### 4. Structured Extraction

Extracts from documents:

```python
# Paragraphs with:
# - Content text
# - Role (title, sectionHeading, heading)
# - Bounding regions (coordinates, page)
# - Span information

# Tables with:
# - Cell content
# - Row & column indices
# - Bounding regions
```

## API Reference

### TransformerDocumentProcessor

Main class for document processing.

#### `__init__()`

Initialize the processor:

```python
from doc_extraction_using_di import TransformerDocumentProcessor

processor = TransformerDocumentProcessor()
```

**Parameters:** None (credentials from .env)

**Credentials needed in .env:**
```env
AZURE_DI_ENDPOINT=https://your-di.cognitiveservices.azure.com/
AZURE_DI_API_KEY=your_api_key
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
BLOB_INPUT_CONTAINER=input-document-center
BLOB_OUTPUT_CONTAINER=output-of-di
```

#### `process_project(project_folder: str)`

Process all documents in a project folder:

```python
processor.process_project("Energinet_onshore_offshore")
```

**Parameters:**
- `project_folder` (str): Folder name in `input-document-center` blob
  - Example: `ProjectName_onshore_offshore`
  - Source: Directly from UI/upload

**Returns:** None (results uploaded to Azure)

**What it does:**
1. Checks if project already processed (skip if yes)
2. Lists all PDF/DOCX/XLSX files in folder
3. Downloads each file to temp
4. Checks for duplicates
5. Detects image pages (PDF only)
6. Runs Azure DI on each file
7. Uploads results to `output-of-di/{project}/`

**Example:**

```python
# Process a single project
processor.process_project("MyCompany_onshore_offshore")

# Process multiple projects
for project in ["Project1_onshore", "Project1_offshore", "Project2"]:
    processor.process_project(project)
```

#### `project_already_processed(project_folder: str) → bool`

Check if a project has already been processed:

```python
if processor.project_already_processed("MyProject"):
    print("Already done!")
else:
    processor.process_project("MyProject")
```

**Returns:** `True` if output files exist, `False` otherwise

#### `list_project_files(project_folder: str) → List[Dict]`

List all processable files in a project:

```python
files = processor.list_project_files("MyProject")
for file in files:
    print(f"- {file['filename']} ({file['file_size']} bytes)")
```

**Returns:** List of file info dicts with:
- `project_name` - Folder name
- `blob_name` - Full path in blob
- `filename` - Just the filename
- `file_size` - Size in bytes
- `ext` - File extension

**Supported extensions:** `.pdf`, `.docx`, `.xlsx`

#### `process_single_file(file_info: Dict, temp_dir: str) → Dict`

Process a single file (called internally):

```python
summary = processor.process_single_file(file_info, "/tmp/dir")
print(f"Status: {summary['status']}")
print(f"Duplicate: {summary['duplicate']}")
```

**Returns:** Summary dict with:
- `file_info` - Original file info
- `timestamp` - Processing time
- `duplicate` - Was it a duplicate?
- `image_pages` - List of image-heavy pages
- `di_result` - DI extraction result
- `status` - 'success', 'failed', or 'skipped_duplicate'

#### `detect_image_pages(pdf_path: str) → List[int]`

Detect which pages contain mostly images:

```python
image_pages = processor.detect_image_pages("/tmp/document.pdf")
print(f"Image pages: {image_pages}")  # [1, 3, 5]
```

**Returns:** List of page numbers that are image-heavy

**Criteria:**
- Pixel variance > 1000
- OR extractable text < 50 characters

#### `process_with_di(local_path: str, file_info: Dict, temp_dir: str) → Dict`

Run Azure DI on a document (called internally):

```python
result = processor.process_with_di(
    local_path="/tmp/spec.pdf",
    file_info=file_dict,
    temp_dir="/tmp"
)

if result['success']:
    print(f"Pages: {result['pages_processed']}")
    print(f"Tables: {result['tables_found']}")
```

**Returns:** Result dict with:
- `success` (bool) - Did DI succeed?
- `pages_processed` (int) - Number of pages
- `tables_found` (int) - Number of tables
- `error` (str) - Error message if failed

## Output Format

### DI Result JSON Structure

```json
{
  "pages": [
    {
      "page_number": 1,
      "width": 595,
      "height": 842,
      "unit": "pixel"
    }
  ],
  "paragraphs": [
    {
      "content": "Section 1: Technical Specifications",
      "role": "sectionHeading",
      "bounding_regions": [
        {
          "page_number": 1,
          "polygon": [[x1, y1], [x2, y2], ...]
        }
      ],
      "spans": [
        {
          "offset": 0,
          "length": 33,
          "confidence": 0.95
        }
      ]
    }
  ],
  "tables": [
    {
      "row_count": 5,
      "column_count": 3,
      "cells": [
        {
          "row_index": 0,
          "column_index": 0,
          "content": "Voltage",
          "bounding_regions": [...]
        }
      ],
      "bounding_regions": [...]
    }
  ]
}
```

## Usage Examples

### Basic Example

```python
from doc_extraction_using_di import TransformerDocumentProcessor

# Initialize
processor = TransformerDocumentProcessor()

# Process a project
processor.process_project("Energinet_onshore_offshore")

# Check status
results = processor.processing_log
for result in results:
    print(f"File: {result['file_info']['filename']}")
    print(f"Status: {result['status']}")
```

### Advanced Example

```python
# Process with logging
processor = TransformerDocumentProcessor()

projects = [
    "Company_onshore",
    "Company_offshore",
    "Company_combined"
]

for project in projects:
    print(f"\nProcessing: {project}")
    
    if processor.project_already_processed(project):
        print("  → Already processed, skipping")
        continue
    
    try:
        processor.process_project(project)
        print("  → Success!")
    except Exception as e:
        print(f"  → Error: {e}")
```

### Check File List

```python
# See what files will be processed
processor = TransformerDocumentProcessor()
files = processor.list_project_files("MyProject")

total_size = sum(f['file_size'] for f in files)
print(f"Found {len(files)} files, {total_size / 1024 / 1024:.1f} MB total")

for file in files:
    print(f"  - {file['filename']} ({file['file_size']} bytes)")
```

## Configuration

### Environment Variables

```env
# Required
AZURE_DI_ENDPOINT=https://your-di.cognitiveservices.azure.com/
AZURE_DI_API_KEY=your_api_key
AZURE_STORAGE_CONNECTION_STRING=your_connection_string

# Container names
BLOB_INPUT_CONTAINER=input-document-center
BLOB_OUTPUT_CONTAINER=output-of-di
```

### Optional Settings

```python
# Adjust image detection threshold
# Higher = more strict (fewer pages flagged as images)
PIXEL_VARIANCE_THRESHOLD = 1000  # Default
TEXT_LENGTH_THRESHOLD = 50        # Characters
```

## Error Handling

### Common Errors & Solutions

| Error | Cause | Solution |
|-------|-------|----------|
| `AuthenticationError` | Invalid API key | Check `.env` credentials |
| `ContainerNotFound` | Input container doesn't exist | Create container in blob storage |
| `DocumentAnalysisError` | DI API error | Check DI endpoint, try different file |
| `ConnectionError` | Azure service down | Wait and retry |

### Retry Logic

```python
# DI has built-in retry with exponential backoff
# If DI fails, entire file is marked as failed
# Processor continues with next file
```

## Performance

### Processing Times

| Document Type | Pages | Time |
|---------------|-------|------|
| Text PDF | 10 | 5-10s |
| Complex PDF | 10 | 10-20s |
| Image PDF | 10 | 20-30s |
| DOCX | 10 | 5-8s |

### Optimization Tips

1. **Use text-based PDFs** - Faster than scanned images
2. **Compress PDFs** - Smaller files = faster upload
3. **Split large documents** - Process in chunks
4. **Batch process** - Use project folders to group related docs
5. **Monitor quotas** - DI has rate limits (check Azure subscription)

## What Happens Next

The output of this module:
- **Location:** `output-of-di/{project}/filename_di_result.json`
- **Used by:** `chunk_by_title_semantic_blob.py`
- **Purpose:** Serve as input for semantic chunking

## Troubleshooting

### "Project already processed" - Force Reprocess

```python
# Delete existing outputs from Azure Portal
# OR manually delete container contents
# Then run processor again

processor.process_project("MyProject")
```

### DI Extraction Quality Issues

**Problem:** Poor text extraction

**Solutions:**
1. Check if PDF is scanned (image-based)
2. Try different PDF format/compression
3. Manually verify extracted data
4. Consider using OCR preprocessing

### Duplicate Detection Too Aggressive

**Problem:** Similar but different files marked as duplicates

**Solutions:**
- The MD5 hash must be exact (byte-for-byte identical)
- If files are truly different, hashes will differ
- Check file sizes in Azure portal

---

**Next:** [Semantic Chunking](chunking.md) → Process the extracted data
