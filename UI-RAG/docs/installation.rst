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
  - Azure OpenAI (or OpenAI API key) — with both a **chat model** deployment (e.g. ``gpt-4o``, ``gpt-4o-mini``) and an **embedding model** deployment (e.g. ``text-embedding-3-large``)

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
- **python-dotenv** - Environment variable management
- **ragas** - RAG evaluation framework
- **datasets** - HuggingFace datasets (required by RAGAS)
- **langchain-openai** - LangChain wrappers for Azure OpenAI (judge LLM + embeddings)
- **pandas** - Used by ``evaluate_with_ragas.py`` for result tables and CSV export

Dependencies Breakdown
======================

**Core Processing:**

.. code-block:: text

    azure-ai-formrecognizer>=3.3.0      # Document Intelligence
    azure-storage-blob>=12.18.0         # Blob Storage
    azure-search-documents>=11.4.0      # AI Search
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

**Evaluation (RAGAS):**

.. code-block:: text

    ragas>=0.1.0                        # RAG evaluation framework
    datasets>=2.14.0                    # HuggingFace dataset wrapper
    langchain-openai>=0.0.5             # Azure judge LLM + embeddings
    pandas>=2.0.0                       # Result tables & CSV export

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

    # OpenAI (used by RAG pipeline AND RAGAS evaluation)
    OPENAI_KEY=sk-your_openai_key
    OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
    CHAT_MODEL=gpt-4o
    EMBEDDING_MODEL=text-embedding-3-large

    # RAGAS Evaluation (optional — defaults shown)
    RAGAS_JUDGE_MODEL=gpt-4o-mini       # Smaller/cheaper for judge calls
    RAGAS_INPUT_FILE=manual_test_cases.json

    # API Security
    API_KEY=your_secret_api_key

.. note::

    ``evaluate_with_ragas.py`` currently reads credentials from constants at the
    top of the script rather than from ``.env``. After cloning, open the file and
    paste your ``OPENAI_KEY`` and ``OPENAI_ENDPOINT`` there. Never commit those
    values to GitHub.

See :doc:`configuration` for detailed environment setup instructions.

Step 5: Verify Installation
============================

Test if everything is installed correctly:

.. code-block:: bash

    python -c "import fastapi; import azure; import openai; print('✓ Core imports successful!')"

Then verify the evaluation stack:

.. code-block:: bash

    python -c "import ragas; import datasets; from langchain_openai import AzureChatOpenAI; print('✓ RAGAS evaluation stack ready!')"


Step 6: Start the Application
==============================

**Backend (FastAPI):**

.. code-block:: bash

    uvicorn app:app --reload --host 0.0.0.0 --port 8000

You should see:

.. code-block:: text

    INFO:     Uvicorn running on http://0.0.0.0:8000
    INFO:     Application startup complete


Step 7: (Optional) Run RAGAS Evaluation
========================================

Once your RAG pipeline is running, you can measure its quality with RAGAS.

1. Prepare a JSON file of test cases (see :doc:`evaluate_with_ragas` for the schema)::

       manual_test_cases.json


2. Open ``evaluate_with_ragas.py`` and confirm your Azure credentials are set
   in the configuration block at the top of the file.


3. Run the evaluation:

   .. code-block:: bash

       python evaluate_with_ragas.py

4. Three timestamped report files are written to the current directory:

   .. code-block:: text

       ragas_evaluation_detailed_<timestamp>.csv
       ragas_results_<timestamp>.json
       ragas_summary_<timestamp>.txt

   Open the CSV in Excel for per-parameter scores across all four metrics
   (faithfulness, answer correctness, context recall, context precision).

Troubleshooting Installation
============================

**Problem: "Python not found"**

Solution: Install Python from `python.org <https://python.org>`__ or use a package manager:

.. code-block:: bash

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

**Problem: "No module named 'ragas'" or "No module named 'datasets'"**

Solution: Install the evaluation dependencies:

.. code-block:: bash

    pip install ragas datasets langchain-openai pandas

If the install fails on Windows due to a heavy transitive dependency,
upgrade pip and setuptools first:

.. code-block:: bash

    python -m pip install --upgrade pip setuptools wheel
    pip install ragas datasets langchain-openai pandas


Next Steps
==========

After installation:


1. Follow the :doc:`quickstart` guide
2. Explore the :doc:`source_code` and :doc:`ui rag` documentation
3. Review :doc:`architecture` for system design
4. Measure RAG quality with :doc:`evaluate_with_ragas`

Getting Help
============

If you encounter issues, check :doc:`troubleshooting`


.. note::

    On systems without GPU acceleration, FAISS (CPU) is recommended for easier setup.
    GPU acceleration is optional but recommended for large-scale deployments.
