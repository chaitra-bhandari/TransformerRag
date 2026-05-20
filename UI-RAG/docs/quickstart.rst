===========
Quick Start
===========

Get Transformer Spec RAG running in 15 minutes.

Prerequisites
=============

You need:
- ✅ Python 3.8+
- ✅ Azure account with services configured (see :doc:`configuration`)
- ✅ Project cloned and dependencies installed (see :doc:`installation`)

5-Minute Setup
==============

**1. Activate virtual environment**

.. code-block:: bash

    # Windows
    venv\Scripts\activate

**2. Verify configuration**

Ensure your ``.env`` file is complete:

.. code-block:: bash

    type .env # Windows

Required variables:
- AZURE_STORAGE_CONNECTION_STRING
- AZURE_DI_ENDPOINT & AZURE_DI_API_KEY
- AZURE_SEARCH_ENDPOINT & AZURE_SEARCH_KEY
- OPENAI_KEY

**3. Start the backend**

.. code-block:: bash

    uvicorn app:app --reload

You should see:

.. code-block:: text

    ✓ Uvicorn running on http://127.0.0.1:8000
    ✓ Application startup complete

**4. Test the API**

Open ``http://127.0.0.1:8000/docs`` in your browser - you'll see the interactive API documentation.

**5. Start the frontend**

In a new terminal:

.. code-block:: bash

    cd frontend
    npm install  # First time only
    npm start

The React app opens at ``http://localhost:3000``

Your First Upload
=================

1. **Prepare a PDF document**

   Use any PDF 

2. **Go to the web interface**

   Navigate to ``http://localhost:8000``

3. **Upload document and create the project**

   - Click "Upload Project"
   - Select project type: "standalone" or "combined"
   - Choose your PDF file
   - Click "Upload"

4. **Download the document**

   - Order documents


Core Workflow
=============

.. code-block:: text

    1. User uploads PDF
           ↓
    2. Document Intelligence extracts content
           ↓
    3. System chunks document semantically
           ↓
    4. Chunks converted to embeddings
           ↓
    5. Stored in Faiss index
           ↓
    6. System retrieves relevant chunks
           ↓
    7. RAG generates specification document
           ↓
    8. Document filled with extracted parameters
           ↓
    9. Download as .docx file

Using the Web Interface
=======================

**Upload Tab**

.. code-block:: text

    1. Select Project Type
       - Standalone: Single configuration (currently working)
       - Combined: Both onshore and offshore

    2. Choose Files
       - Supports PDF
       - Max 100MB per file

    3. Click Upload
       - Files sent to backend
       - Processing begins immediately

**Chat Tab(needs improvment)**

.. code-block:: text

    1. Enter Query
       - Specification extraction requests
       - Document generation requests

    2. System Processes
       - Retrieves relevant chunks
       - Uses RAG to synthesize answer
       - Returns results and documents

    3. Download Documents
       - Generated .docx files available
       - Can download and edit further

Common Tasks
============

Extracting Specifications from a PDF
-------------------------------------

**Via Web Interface:**

1. Upload PDF (automatic DI extraction)
2. Ask: "Generate documents"
3. Click to download generated document

Generating Specification Documents
-----------------------------------

1. Upload raw specification PDFs
2. Query to extract key parameters
3. Use generated specifications to fill templates
4. Download completed order documents

Performance Tips
================

**For Better Results:**

1. **Use clean PDFs**
   - Avoid scanned images (must be OCR'd first)
   - Ensure text is extractable
   - Check page numbers are correct

2. **Organize by project**
   - Group related documents
   - Use consistent naming
   - Keep project folders separate

3. **Refine queries**
   - Be specific: "What is the rated voltage?" not "Tell me about the transformer"
   - Include context: "From transformer unit-01, what is..."
   - Ask one question at a time

4. **Monitor processing**
   - Check Azure Portal for DI usage
   - Verify AI Search index grows
   - Monitor API response times

System Limitations & Workarounds
=================================

**Azure DI may struggle with**
- Dense tables with many columns
- Mixed languages in single document
- Non-standard page layouts

Workaround: Clean up PDFs or split into simpler documents

Debugging
=========

**Check Backend Logs**

When running with ``--reload``:

.. code-block:: bash

    # Look for errors in terminal output
    uvicorn app:app --reload

**Check Frontend Logs**

Open browser console:
- Chrome: F12 → Console tab
- Firefox: F12 → Console tab
- Safari: Develop → Show Error Console

**Verify Azure Connectivity**

.. code-block:: python

    from azure.storage.blob import BlobServiceClient
    import os
    from dotenv import load_dotenv

    load_dotenv()
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    
    try:
        client = BlobServiceClient.from_connection_string(conn_str)
        containers = client.list_containers()
        print("✓ Azure Storage connected")
    except Exception as e:
        print(f"✗ Azure Storage error: {e}")


.. note::

   First upload may take 1-2 minutes as the system creates indexes and embeddings. Subsequent uploads are faster.

.. tip::

   Start with a small, clean PDF to test. Once working, move to larger documents.
