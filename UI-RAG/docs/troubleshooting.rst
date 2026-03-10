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
    source venv/bin/activate  # macOS/Linux
    # or
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

Search index not created or name mismatch.

**Solution:**

1. Verify index name in .env:

.. code-block:: bash

    AZURE_SEARCH_INDEX=transformer-chunks
    # Must match exactly

2. Create index if doesn't exist:
   - Upload document to trigger index creation
   - Or run chunking script first

3. Check AI Search is accessible:

.. code-block:: python

    from azure.search.documents import SearchClient
    client = SearchClient(endpoint, index_name, AzureKeyCredential(key))
    results = client.search("*")
    print(f"Index has {len(list(results))} documents")

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
    # macOS/Linux
    lsof -i :8000

    # Windows
    netstat -ano | findstr :8000

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

**Problem: "413 Payload Too Large"**

File exceeds maximum size (100 MB).

**Solution:**

1. Check file size:

.. code-block:: bash

    # macOS/Linux
    ls -lh document.pdf

    # Windows
    dir document.pdf

2. Split large files:
   - Split PDF into multiple documents
   - Remove unnecessary pages
   - Compress before uploading

3. Increase limit if needed:

.. code-block:: python

    # In app.py
    MAX_FILE_SIZE_MB = 200  # Increase limit

**Problem: "415 Unsupported Media Type"**

File format not supported.

**Solution:**

Supported formats: .pdf, .docx, .xlsx

.. code-block:: bash

    # Check file extension
    file document.pdf

    # Rename if needed
    mv document.doc document.docx

**Problem: Endpoint "/docs" returns 404**

Swagger UI not available (production mode?).

**Solution:**

Swagger UI is available in development mode:

.. code-block:: bash

    # Make sure running with --reload
    uvicorn app:app --reload

    # Then visit http://localhost:8000/docs

Document Processing Issues
===========================

**Problem: "Image pages detected" but document is text-based**

PDF is scanned or image-heavy.

**Solution:**

1. Check if PDF is truly text-based:

.. code-block:: bash

    # Try extracting text from first page
    pdftotext document.pdf -
    # If empty, it's scanned

2. Solution options:
   - Use original digital PDF if available
   - OCR the scanned PDF first
   - Extract images manually

**Problem: "No chunks created" after upload**

Document extraction failed or noise filters too aggressive.

**Solution:**

1. Check DI result JSON:
   - Navigate to output-of-di container
   - View the _di_result.json file
   - Verify paragraphs and tables extracted

2. Check if document is valid:
   - Open with PDF reader
   - Verify text is extractable
   - Check for password protection

3. Adjust chunking parameters:

.. code-block:: python

    chunker = DocumentChunker(
        min_tokens=5,  # Lower threshold
        combine_text_under_n_chars=1000  # Merge smaller chunks
    )

**Problem: Chunks too small or too large**

Chunking parameters need adjustment.

**Solution:**

Adjust parameters in DocumentChunker:

.. code-block:: python

    # For larger chunks (more context)
    chunker = DocumentChunker(
        max_characters=8000,
        new_after_n_chars=7500,
        combine_text_under_n_chars=3000
    )

    # For smaller chunks (more granular)
    chunker = DocumentChunker(
        max_characters=2000,
        new_after_n_chars=1800,
        combine_text_under_n_chars=1000
    )

**Problem: Tables not extracted correctly**

Table detection or formatting issue.

**Solution:**

1. Check DI detected tables:
   - Look in DI result JSON
   - Search for "tables" section
   - Verify cells are present

2. Complex tables:
   - Merged cells may cause issues
   - Very wide tables may not format well
   - Consider manual extraction

**Problem: Duplicate documents being processed**

Duplicate detection not working.

**Solution:**

1. Check MD5 hash calculation:
   - Verify files are truly identical
   - Different content = different hash

2. Clear duplicate tracker:
   - Restart the processor
   - Duplicates tracked per-run only

Query & RAG Issues
==================

**Problem: "No results" for query**

Query didn't match any documents.

**Solution:**

1. Verify documents are indexed:

.. code-block:: bash

    curl -H "X-API-Key: your_key" \
         http://localhost:8000/list-projects

2. Check project exists:
   - Verify project_folder in request

3. Try simpler query:
   - Shorter, more specific question
   - Include document keywords

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

**Problem: Slow response times**

Query taking more than 5 seconds.

**Solution:**

1. Check network:
   - Azure services may be slow
   - Check Azure Portal metrics

2. Optimize query:
   - Reduce top_k parameter
   - Use simpler questions

3. Reduce index size:
   - Archive old documents
   - Remove duplicates
   - Split large projects

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

Performance Issues
==================

**Problem: Memory usage growing**

Memory leak or large document accumulation.

**Solution:**

1. Restart application:

.. code-block:: bash

    # Stop server (Ctrl+C)
    # Restart
    uvicorn app:app --reload

2. Monitor memory:

.. code-block:: bash

    # macOS/Linux
    top -p $(pgrep -f uvicorn)

    # Windows
    tasklist /v | find "python"

3. Increase available RAM or optimize:
   - Process files individually
   - Clear temporary files
   - Use chunking parameters

**Problem: Slow document extraction**

DI processing is slow.

**Solution:**

DI speed depends on:
- File size (larger = slower)
- Page count
- Azure DI service load
- Network latency

Optimizations:
- Split large documents
- Process during off-peak hours
- Use faster region (if available)

**Problem: Frontend not connecting to backend**

React app can't reach API.

**Solution:**

1. Verify backend is running:

.. code-block:: bash

    curl http://localhost:8000/health

2. Check CORS configuration:

.. code-block:: bash

    # In app.py or .env
    CORS_ORIGINS must include frontend origin

3. Check frontend URL:

.. code-block:: bash

    # Frontend should be on port 3000
    http://localhost:3000

4. Check network:

   - Browser console (F12) for CORS errors
   - Verify firewall allows localhost access

Frontend Issues
===============

**Problem: "Cannot find module 'react'"**

React not installed.

**Solution:**

.. code-block:: bash

    cd frontend
    npm install
    npm start

**Problem: Blank screen or 404 on frontend**

React build or routing issue.

**Solution:**

1. Restart React dev server:

.. code-block:: bash

    cd frontend
    npm start

2. Clear browser cache:
   - Open DevTools (F12)
   - Network tab → Disable cache
   - Reload page

3. Check build:

.. code-block:: bash

    npm run build
    # Check for errors in output

**Problem: Can't upload files in web UI**

File upload not working.

**Solution:**

1. Check file size:
   - Maximum 100 MB

2. Check file type:
   - Only .pdf, .docx, .xlsx

3. Check API connectivity:
   - Open browser DevTools (F12)
   - Network tab
   - Look for failed requests
   - Check response status/error

4. Check API key:
   - Verify API_KEY is set in backend
   - Check frontend is sending X-API-Key header

Getting More Help
=================

**Check Documentation**

- :doc:`../quickstart` - Basic setup
- :doc:`../configuration` - Environment setup
- :doc:`../installation` - Installation help
- :doc:`../faq` - Common questions

**Enable Debug Logging**

.. code-block:: bash

    # Set in .env
    DEBUG=true
    LOG_LEVEL=DEBUG

    # Restart backend
    uvicorn app:app --reload --log-level debug

**Check GitHub Issues**

- Search existing issues
- Check closed issues for solutions
- Open new issue with:
  - Error message
  - Steps to reproduce
  - System info (OS, Python version)
  - Configuration (without secrets)

**Contact Support**

- Email: support@example.com
- Forum: community.example.com
- Chat: Discord/Slack

**Enable Tracing**

For complex issues:

.. code-block:: python

    import logging
    logging.basicConfig(level=logging.DEBUG)
    # Now all operations show detailed logs
