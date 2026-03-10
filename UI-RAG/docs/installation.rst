============
Installation
============

This guide walks you through setting up Transformer Spec RAG on your system.

Prerequisites
=============

Before you begin, ensure you have:

- **Python 3.8 or higher** installed (3.11+ recommended)
- **pip** package manager (comes with Python)
- **git** for version control
- **Azure subscription** with the following services:
  - Azure Storage Account
  - Azure Document Intelligence
  - Azure AI Search
  - Azure OpenAI (or OpenAI API key)

Check Your Python Version
==========================

Open a terminal and run:

.. code-block:: bash

    python --version
    # or
    python3 --version

You should see Python 3.8 or higher.

Step 1: Clone the Repository
=============================

.. code-block:: bash

    git clone https://github.com/yourorg/transformer-spec-rag.git
    cd transformer-spec-rag

Step 2: Create Virtual Environment
===================================

Creating a virtual environment isolates your project dependencies.

**On Windows:**

.. code-block:: bash

    python -m venv venv
    venv\Scripts\activate

**On macOS/Linux:**

.. code-block:: bash

    python3 -m venv venv
    source venv/bin/activate

You'll see ``(venv)`` prefix in your terminal prompt when activated.

Step 3: Install Dependencies
=============================

Install all required Python packages:

.. code-block:: bash

    pip install -r requirements.txt

This installs:

- **fastapi** - Web framework
- **uvicorn** - ASGI server
- **azure-ai-formrecognizer** - Document Intelligence client
- **azure-storage-blob** - Blob Storage client
- **azure-search-documents** - AI Search client
- **openai** - OpenAI API client
- **faiss-cpu** - Vector search (use faiss-gpu for GPU acceleration)
- **pdf2image** - PDF image conversion
- **PyPDF2** - PDF processing
- **python-dotenv** - Environment variable management

Dependencies Breakdown
======================

**Core Processing:**

.. code-block:: text

    azure-ai-formrecognizer>=3.3.0      # Document Intelligence
    azure-storage-blob>=12.18.0         # Blob Storage
    azure-search-documents>=11.4.0      # AI Search
    pdf2image>=1.16.0                   # PDF conversion
    PyPDF2>=3.0.0                       # PDF tools
    numpy>=1.24.0                       # Numerical computing

**Vector Search:**

.. code-block:: text

    faiss-cpu>=1.7.4                    # Local vector search
    # OR
    faiss-gpu>=1.7.4                    # GPU acceleration (requires CUDA)

**Web Framework:**

.. code-block:: text

    fastapi>=0.104.0                    # Web framework
    uvicorn[standard]>=0.24.0           # ASGI server
    python-multipart>=0.0.6             # Form handling
    pydantic>=2.0.0                     # Data validation

**External APIs:**

.. code-block:: text

    openai>=1.3.0                       # OpenAI GPT-4
    python-dotenv>=1.0.0                # Environment variables

**Development:**

.. code-block:: text

    pytest>=7.4.0                       # Testing
    pytest-asyncio>=0.21.0              # Async testing
    black>=23.0.0                       # Code formatting

Step 4: Configure Environment Variables
========================================

Create a ``.env`` file in the project root with your Azure and API credentials:

.. code-block:: bash

    # Azure Storage
    AZURE_STORAGE_CONNECTION_STRING=your_connection_string

    # Azure Document Intelligence
    AZURE_DI_ENDPOINT=https://your-region.api.cognitive.microsoft.com/
    AZURE_DI_API_KEY=your_di_api_key

    # Azure AI Search
    AZURE_SEARCH_ENDPOINT=https://your-search-service.search.windows.net/
    AZURE_SEARCH_KEY=your_search_key
    AZURE_SEARCH_INDEX=transformer-chunks

    # Blob Container Names
    BLOB_INPUT_CONTAINER=transformer-input
    BLOB_OUTPUT_CONTAINER=output-of-di
    BLOB_CHUNK_CONTAINER=chunked-output
    BLOB_DESIGN_DOCS_CONTAINER=order-design-documents
    BLOB_TEMPLATE_CONTAINER=order-templates

    # OpenAI
    OPENAI_KEY=sk-your_openai_key
    OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
    CHAT_MODEL=gpt-4o

    # API Security
    API_KEY=your_secret_api_key

See :doc:`configuration` for detailed environment setup instructions.

Step 5: Verify Installation
============================

Test if everything is installed correctly:

.. code-block:: bash

    python -c "import fastapi; import azure; import openai; print('✓ All imports successful!')"

Or run the test suite:

.. code-block:: bash

    pytest tests/ -v

Step 6: Start the Application
==============================

**Backend (FastAPI):**

.. code-block:: bash

    uvicorn app:app --reload --host 0.0.0.0 --port 8000

You should see:

.. code-block:: text

    INFO:     Uvicorn running on http://0.0.0.0:8000
    INFO:     Application startup complete

**Frontend (React):**

In a new terminal:

.. code-block:: bash

    cd frontend
    npm install
    npm start

The React app will open at ``http://localhost:3000``

Docker Installation (Optional)
==============================

For containerized deployment:

.. code-block:: bash

    docker build -t transformer-rag:latest .
    docker run -p 8000:8000 --env-file .env transformer-rag:latest

Troubleshooting Installation
============================

**Problem: "Python not found"**

Solution: Install Python from `python.org <https://python.org>`__ or use a package manager:

.. code-block:: bash

    # macOS with Homebrew
    brew install python3

    # Windows with Chocolatey
    choco install python

**Problem: "pip: command not found"**

Solution: Use python's module syntax:

.. code-block:: bash

    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt

**Problem: "ModuleNotFoundError" after pip install**

Solution: Ensure virtual environment is activated:

.. code-block:: bash

    # Activate environment
    source venv/bin/activate  # macOS/Linux
    # or
    venv\Scripts\activate     # Windows

**Problem: Azure authentication errors**

Solution: Verify your ``.env`` file has correct credentials and restart the application.

**Problem: "No module named 'faiss'"**

Solution: Install CPU or GPU version:

.. code-block:: bash

    # CPU version (recommended for most users)
    pip install faiss-cpu

    # GPU version (requires CUDA)
    pip install faiss-gpu

Next Steps
==========

After installation:

1. Complete :doc:`configuration` setup
2. Follow the :doc:`quickstart` guide
3. Explore the :doc:`api/index` documentation
4. Review :doc:`architecture` for system design

Getting Help
============

If you encounter issues:

1. Check :doc:`troubleshooting`
2. Review :doc:`faq`
3. Check the `GitHub Issues <https://github.com/yourorg/transformer-spec-rag/issues>`__
4. Contact the development team

.. note::

    On systems without GPU acceleration, FAISS (CPU) is recommended for easier setup.
    GPU acceleration is optional but recommended for large-scale deployments.
