========================
Document Extraction
========================

``doc_extraction_using_di.py``

Extracts structured content from documents using Azure Document Intelligence.

Overview
========

The Document Extraction module uses Microsoft Azure's Document Intelligence service to analyze documents and extract:

- Text content with role classification
- Page information and numbering
- Table structure and cell content
- Layout analysis and spatial relationships
- Image-heavy page detection

This is the first stage of the RAG pipeline.

Core Class
==========

.. code-block:: python

    class TransformerDocumentProcessor:
        """Process documents with Azure Document Intelligence"""
        
        def __init__(self):
            # Initialize Azure DI client
            # Initialize Blob Storage client

Initialization
==============

.. code-block:: python

    from doc_extraction_using_di import TransformerDocumentProcessor

    # Create processor
    processor = TransformerDocumentProcessor()

    # The constructor:
    # - Connects to Azure Document Intelligence
    # - Connects to Azure Blob Storage
    # - Sets up input/output containers
    # - Initializes tracking dictionaries

Required Configuration
======================

Set these environment variables:

.. code-block:: bash

    # Azure Document Intelligence
    AZURE_DI_ENDPOINT=https://region.api.cognitive.microsoft.com/
    AZURE_DI_API_KEY=your_api_key

    # Azure Blob Storage
    AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
    BLOB_INPUT_CONTAINER=transformer-input
    BLOB_OUTPUT_CONTAINER=output-of-di

Main Methods
============

**process_project(project_folder)**

Process all files in a project folder.

.. code-block:: python

    processor.process_project("MyProject_onshore")

**Parameters:**
- ``project_folder`` (str): Folder name in input blob container

**Returns:** None (uploads results to output blob)

**Example:**

.. code-block:: python

    processor = TransformerDocumentProcessor()
    processor.process_project("Energinet_onshore_offshore")
    # Results saved to output-of-di/Energinet_onshore_offshore/

**Workflow:**

1. Check if project already processed (skip if yes)
2. List all PDF/DOCX/XLSX files in project folder
3. For each file:
   - Download to temporary directory
   - Check for duplicates (MD5 hash)
   - Detect image-heavy pages
   - Run Azure Document Intelligence
   - Upload results JSON
4. Generate summary report

**project_already_processed(project_folder)**

Check if a project has been processed before.

.. code-block:: python

    if processor.project_already_processed("MyProject"):
        print("Project already processed")
    else:
        print("Ready to process")

**Parameters:**
- ``project_folder`` (str): Project folder name

**Returns:**
- ``True`` if output files exist
- ``False`` if needs processing

**Reason:** Avoids re-processing expensive DI operations.

**list_project_files(project_folder)**

List all processable files in a project.

.. code-block:: python

    files = processor.list_project_files("MyProject_onshore")
    # [
    #   {
    #     'project_name': 'MyProject_onshore',
    #     'blob_name': 'MyProject_onshore/spec1.pdf',
    #     'filename': 'spec1.pdf',
    #     'file_size': 2048576,
    #     'ext': '.pdf'
    #   },
    #   ...
    # ]

**Returns:**
- List of file info dictionaries
- Only includes .pdf, .docx, .xlsx files

**process_single_file(file_info, temp_dir)**

Process one document through DI.

.. code-block:: python

    summary = processor.process_single_file(file_info, temp_dir)

**Parameters:**
- ``file_info`` (dict): File metadata
- ``temp_dir`` (str): Temporary directory path

**Returns:**
- Dictionary with processing results
- Includes success status, DI output, image pages

**Steps:**

1. Download file to temporary storage
2. Check for duplicates
3. Detect image pages (PDFs only)
4. Run Azure Document Intelligence
5. Upload result JSON to output container

**Process with Azure Document Intelligence**

.. code-block:: python

    result_data = processor.process_with_di(local_path, file_info, temp_dir)
    # {
    #   'success': True,
    #   'pages_processed': 15,
    #   'tables_found': 3,
    #   'output_blob_path': 'MyProject/file_di_result.json'
    # }

Output Structure
================

**DI Result JSON** (saved to output-of-di/)

.. code-block:: json

    {
      "pages": [
        {
          "page_number": 1,
          "height": 792,
          "width": 612,
          "unit": "pixel"
        }
      ],
      "paragraphs": [
        {
          "content": "Transformer Specifications",
          "role": "title",
          "page_number": 0,
          "bounding_regions": [
            {
              "page_number": 0,
              "polygon": [[x1, y1], [x2, y2], ...]
            }
          ],
          "spans": [
            {
              "offset": 0,
              "length": 25
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
              "content": "Parameter",
              "bounding_regions": [...]
            }
          ],
          "bounding_regions": [...]
        }
      ]
    }

**Key Output Fields**

- ``pages``: Page metadata (dimensions, numbering)
- ``paragraphs``: Extracted text with roles and positions
- ``tables``: Structured table data
- ``spans``: Character position information

Image Page Detection
====================

For PDF files, the system automatically detects pages that are primarily images.

**Detection Method:**

.. code-block:: python

    def detect_image_pages(self, pdf_path: str) -> List[int]:
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=72)
        
        # Calculate pixel variance
        for page_num, img in enumerate(images):
            img_array = np.array(img.convert('L'))
            variance = np.var(img_array)
            
            # High variance = image content
            if variance > 1000:
                image_pages.append(page_num)

**Returns:** List of page numbers that are image-heavy

**Use Cases:**
- Scanned documents (need OCR)
- Diagrams and schematics
- Charts and graphs

Duplicate Detection
===================

Prevents re-processing of identical files.

.. code-block:: python

    def calculate_hash(filepath: str) -> str:
        # Calculate MD5 hash of file
        h = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()

**Tracking:**
- Maintains dictionary of file hashes
- Skips files if hash seen before
- Within-run deduplication only

Error Handling
==============

**Common Errors & Solutions**

**Azure DI Failures**

.. code-block:: text

    Error: "DocumentAnalysisClient initialization failed"
    → Verify AZURE_DI_ENDPOINT and AZURE_DI_API_KEY
    → Check endpoint format: https://region.api.cognitive.microsoft.com/

    Error: "Service returned error"
    → Check file format is supported (.pdf, .docx, .xlsx)
    → Verify file is not corrupted
    → Check Azure DI quota/limits

**Blob Storage Issues**

.. code-block:: text

    Error: "Azure Storage connection failed"
    → Verify AZURE_STORAGE_CONNECTION_STRING is correct
    → Check containers exist
    → Verify storage account has not exceeded quota

**File Size Issues**

.. code-block:: text

    Error: "File too large for DI processing"
    → Maximum supported: 2000 pages or 500 MB
    → Split large documents
    → Remove unnecessary appendices

Example Usage
=============

**Basic Processing**

.. code-block:: python

    from doc_extraction_using_di import TransformerDocumentProcessor

    processor = TransformerDocumentProcessor()
    processor.process_project("MyProject_onshore")

**Processing Multiple Projects**

.. code-block:: python

    projects = [
        "Energinet_onshore",
        "Energinet_offshore",
        "Customer_A_onshore"
    ]

    processor = TransformerDocumentProcessor()
    for project in projects:
        if not processor.project_already_processed(project):
            processor.process_project(project)

**Checking Processing Status**

.. code-block:: python

    processor = TransformerDocumentProcessor()
    files = processor.list_project_files("MyProject_onshore")
    print(f"Found {len(files)} files to process")

    for file_info in files:
        print(f"  - {file_info['filename']} ({file_info['file_size']} bytes)")

**Handling Batch Processing**

.. code-block:: python

    import tempfile
    from pathlib import Path

    processor = TransformerDocumentProcessor()

    with tempfile.TemporaryDirectory() as temp_dir:
        files = processor.list_project_files("MyProject_onshore")
        
        for idx, file_info in enumerate(files, 1):
            print(f"[{idx}/{len(files)}] Processing {file_info['filename']}...")
            
            result = processor.process_single_file(file_info, temp_dir)
            
            if result['status'] == 'success':
                print(f"  ✓ Processed {result['di_result']['pages_processed']} pages")
            else:
                print(f"  ✗ Failed: {result.get('error')}")

Performance Considerations
==========================

**Processing Times**

.. code-block:: text

    File Size    → DI Processing Time
    5 MB         → 10-15 seconds
    10 MB        → 20-30 seconds
    50 MB        → 60-120 seconds
    100+ MB      → May require document splitting

**Optimization Tips**

1. **Batch Processing**: Process multiple files concurrently
2. **Caching**: Don't re-process (use duplicate check)
3. **File Preparation**: Remove unnecessary pages
4. **Regional Deployment**: Use DI in same region as storage

**Cost Considerations**

- Azure DI: ~$50/1000 pages
- Blob Storage: ~$0.018 per GB/month
- Transfer: Free within same region

Supported File Formats
======================

**PDF**
- Text-based PDFs ✓
- Scanned PDFs (image-based) ⚠️ (detected but needs OCR)
- Password-protected PDFs ✗

**Microsoft Word (.docx)**
- Standard documents ✓
- Tables ✓
- Headers/footers ✓
- Complex layouts ⚠️

**Excel (.xlsx)**
- Data tables ✓
- Multiple sheets ⚠️ (first sheet only)
- Formulas ✗

**Unsupported**
- Images (.jpg, .png) ✗
- PowerPoint (.pptx) ✗
- Text files (.txt) ✗

Troubleshooting
===============

**Issue: "Project already processed" error when I want to reprocess**

*Solution:* Delete the output folder or use a new project folder name

.. code-block:: bash

    # Delete output folder
    # Or rename project folder

**Issue: Image pages detected incorrectly**

*Solution:* Adjust variance threshold in code

.. code-block:: python

    # In detect_image_pages() method
    if variance > 1000:  # Adjust this value
        image_pages.append(page_num)

**Issue: Processing is slow**

*Solution:* Consider parallelizing file processing

.. code-block:: python

    from concurrent.futures import ThreadPoolExecutor

    with ThreadPoolExecutor(max_workers=3) as executor:
        results = executor.map(processor.process_single_file, files)

**Issue: Out of memory with large PDFs**

*Solution:* Process files individually, not in batch

.. code-block:: python

    for file_info in files:
        result = processor.process_single_file(file_info, temp_dir)
        # Process immediately, don't store in memory

Advanced Configuration
======================

**Custom DI Model**

The module uses the "prebuilt-layout" model. To use other models:

.. code-block:: python

    poller = self.di_client.begin_analyze_document(
        "prebuilt-layout",  # Can change to other prebuilt models
        f
    )

Available models:
- prebuilt-layout (default)
- prebuilt-read
- prebuilt-document
- Custom trained models

**API Version**

Specify API version:

.. code-block:: python

    from azure.ai.formrecognizer import DocumentAnalysisClient
    from azure.core.credentials import AzureKeyCredential

    client = DocumentAnalysisClient(
        endpoint=ENDPOINT,
        credential=AzureKeyCredential(KEY),
        api_version="2023-10-31-preview"
    )

Next Steps
==========

After extraction:

1. :doc:`../modules/chunking` - Split documents semantically
2. :doc:`../modules/rag_query` - Query extracted content
3. :doc:`../architecture` - Understand the full pipeline
