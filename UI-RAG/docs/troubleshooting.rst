===============
Troubleshooting
===============

Solutions to common issues.

General Troubleshooting Steps
=============================

**1. Check Logs**

Look for error messages in console output:

.. code-block:: bash

    # Backend logs
    uvicorn app:app --reload

    # Check .env file is loaded
    echo $AZURE_STORAGE_CONNECTION_STRING

**2. Verify Configuration**

Ensure .env file has all required variables:

.. code-block:: bash

    cat .env

Required variables:
- AZURE_STORAGE_CONNECTION_STRING
- AZURE_DI_ENDPOINT & AZURE_DI_API_KEY
- AZURE_SEARCH_ENDPOINT & AZURE_SEARCH_KEY
- OPENAI_KEY
- API_KEY

**3. Test Connectivity**

.. code-block:: bash

    # Test backend
    curl http://localhost:8000/health

    # Should return: {"status": "healthy"}

**4. Check Azure Services**

Verify all Azure resources are running and accessible:

1. Azure Portal → Your resources
2. Check Status column
3. Verify quotas not exceeded

**5. Review Recent Changes**

If it worked before:
- What changed in .env?
- Was code updated?
- Did Azure credentials rotate?

Installation Issues
===================

**Problem: "ModuleNotFoundError: No module named 'fastapi'"**

You likely skipped pip install or virtual environment not activated.

**Solution:**

.. code-block:: bash

    # Activate virtual environment
    venv\Scripts\activate     # Windows

    # Install dependencies
    pip install -r requirements.txt

**Problem: "pip: command not found"**

Python not installed or not in PATH.

**Solution:**

.. code-block:: bash

    # Check Python installation
    python --version
    python3 --version

    # Use python -m pip
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt

**Problem: "No module named azure"**

Azure SDK not installed.

**Solution:**

.. code-block:: bash

    pip install azure-storage-blob azure-ai-formrecognizer azure-search-documents

**Problem: "ImportError: cannot import name 'BlobServiceClient'"**

Wrong SDK version or incomplete installation.

**Solution:**

.. code-block:: bash

    pip install --upgrade azure-storage-blob
    pip install --upgrade azure-ai-formrecognizer

Configuration Issues
====================

**Problem: "ERROR: Missing required environment variable: AZURE_DI_API_KEY"**

Missing or incorrect environment variable.

**Solution:**

1. Check .env file exists in project root
2. Verify variable name is correct: ``AZURE_DI_API_KEY`` (case-sensitive)
3. Verify value is not empty
4. Don't use quotes around the value

.. code-block:: bash

    # Correct
    AZURE_DI_API_KEY=abc123xyz

    # Wrong
    AZURE_DI_API_KEY="abc123xyz"

**Problem: "Invalid connection string"**

Malformed Azure Storage connection string.

**Solution:**

1. Go to Azure Portal → Storage Account → Access Keys
2. Copy the full Connection String (not just the key)
3. Should contain: ``DefaultEndpointsProtocol=https;...``

.. code-block:: bash

    # Example format
    AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=myaccount;AccountKey=mykey;EndpointSuffix=core.windows.net

**Problem: "Failed to parse host/port from Endpoint URL"**

Incorrect Azure endpoint URL format.

**Solution:**

URLs must be in correct format:

.. code-block:: bash

    # Document Intelligence - correct
    AZURE_DI_ENDPOINT=https://eastus.api.cognitive.microsoft.com/

    # Wrong - missing trailing slash or wrong region
    AZURE_DI_ENDPOINT=https://eastus.api.cognitive.microsoft.com

    # Search Service - correct
    AZURE_SEARCH_ENDPOINT=https://myservice.search.windows.net/

Azure Authentication Issues
===========================

**Problem: "AuthenticationError: Invalid credentials"**

Azure credentials invalid or expired.

**Solution:**

1. Verify API key hasn't been regenerated
2. Check key is for correct service
3. Verify endpoint matches key's region
4. Try regenerating key:
   - Azure Portal → Keys and Endpoints
   - Click regenerate button
   - Update .env file

**Problem: "Access denied" when accessing blob storage**

Storage account key invalid or insufficient permissions.

**Solution:**

1. Verify connection string is current:

.. code-block:: bash

    # Azure Portal → Storage Account → Access Keys
    # Copy "Connection string" (full string)

2. Check storage account allows access:
   - Storage Account → Firewalls and Virtual Networks
   - Should allow "All networks" (or your IP)

3. Verify containers exist:

.. code-block:: bash

    # List containers
    az storage container list --connection-string "your_connection_string"

**Problem: "Unauthorized" on Document Intelligence calls**

DI API key or endpoint incorrect.

**Solution:**

1. Verify API key:
   - Azure Portal → Document Intelligence resource
   - Keys and Endpoints tab
   - Copy primary or secondary key

2. Verify endpoint:
   - Format: https://REGION.api.cognitive.microsoft.com/
   - Replace REGION with your deployment region (e.g., eastus)

3. Verify API version compatibility:

.. code-block:: bash

    # Check API version in code
    # Should use "2023-10-31-preview" or later
    poller = client.begin_analyze_document("prebuilt-layout", ...)

**Problem: "Index not found" on AI Search queries**

Search index not created or not found.

**Solution:**

1. Verify index name in .env:

.. code-block:: bash

  
   BLOB_INDEX_CONTAINER=faiss-indexes
   BLOB_METADATA_CONTAINER=faiss-metadata

Index files must be with the same names.

2. Create index if doesn't exist:
   - Upload document to trigger index creation
   - Or run chunking script first


API & Backend Issues
====================

**Problem: "Connection refused" on localhost:8000**

Backend not running.

**Solution:**

1. Start backend:

.. code-block:: bash

    uvicorn app:app --reload

2. Should see:
   - "Uvicorn running on http://0.0.0.0:8000"
   - "Application startup complete"

3. Verify port 8000 is free:

.. code-block:: bash

    # Check what's using port 8000
 
    netstat -ano | findstr :8000         # Windows

**Problem: "401 Unauthorized" on API calls**

Missing or invalid API key.

**Solution:**

1. Include X-API-Key header:

.. code-block:: bash

    curl -H "X-API-Key: your_api_key" \
         http://localhost:8000/query

2. Verify API_KEY in .env:

.. code-block:: bash

    cat .env | grep API_KEY

3. Restart backend after changing .env:

.. code-block:: bash

    # Stop current process (Ctrl+C)
    # Start again
    uvicorn app:app --reload


Query & RAG Issues
==================

**Problem: Wrong or irrelevant results**

RAG model retrieving incorrect chunks.

**Solution:**

1. Check top_k parameter:

.. code-block:: python

    # Retrieve more chunks
    response = requests.post(
        url,
        json={
            "question": "...",
            "top_k": 20  # Was 10
        }
    )

2. Refine question:
   - More specific is better
   - Include keywords from documents
   - Ask one question at a time

3. Check document quality:
   - Ensure source documents are clean
   - Remove noise/artifacts
   - Verify text is extractable

**Problem: "Temperature" parameter not affecting responses**

Temperature setting ignored.

**Solution:**

Valid range is 0.0 to 2.0:

.. code-block:: python

    # Low temperature (more factual)
    "temperature": 0.1

    # High temperature (more creative)
    "temperature": 0.9

    # Default
    "temperature": 0.3


Getting More Help
=================

**Check Documentation**

- :doc:`../quickstart` - Basic setup
- :doc:`../configuration` - Environment setup
- :doc:`../installation` - Installation help
- :doc:`../faq` - Common questions


.. code-block:: python

   # Restart backend
   uvicorn app:app --reload --log-level debug



**Contact Support**

- Email: chaitrabhadati@gmail.com


