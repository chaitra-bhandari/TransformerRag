# Configuration Guide

## Environment Setup

### Prerequisites

Before starting, ensure you have:
- **Azure Subscription** with active resources
- **Python 3.8+** installed
- **pip** or **conda** package manager
- **.env** file in project root

### Step 1: Create `.env` File

In your project root, create a `.env` file with all required credentials:

```bash
# .env file - KEEP THIS SECRET!
```

### Step 2: Azure Services Configuration

#### Document Intelligence (DI)

1. Create resource in Azure Portal:
   - Service: **Document Intelligence**
   - Tier: **Standard** (S0 recommended)

2. Get credentials from **Keys and Endpoint** section:

```env
AZURE_DI_ENDPOINT=https://your-di-instance.cognitiveservices.azure.com/
AZURE_DI_API_KEY=your_di_api_key_here
```

#### Azure Storage (Blob)

1. Create **Storage Account** in Azure Portal

2. Get connection string:
   - Go to **Access keys** → Copy **Connection string**

```env
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;AccountName=...
```

3. Create these containers in your storage account:

```bash
# Using Azure CLI
az storage container create --name input-document-center --connection-string $CONN_STR
az storage container create --name output-of-di --connection-string $CONN_STR
az storage container create --name chunked-output --connection-string $CONN_STR
az storage container create --name faiss-indexes --connection-string $CONN_STR
az storage container create --name faiss-metadata --connection-string $CONN_STR
az storage container create --name order-templates --connection-string $CONN_STR
az storage container create --name order-design-documents --connection-string $CONN_STR
```

#### Azure OpenAI

1. Create **OpenAI** resource in Azure Portal:
   - Service: **Cognitive Services - OpenAI**
   - Model: **gpt-4o** and **text-embedding-3-large**

2. Get endpoint and key from **Keys and Endpoint**:

```env
OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
OPENAI_KEY=your_openai_api_key
OPENAI_API_VERSION=2024-02-15-preview
```

3. Deploy models (under **Model deployments**):
   - Model name: `gpt-4o` → Deployment name: `gpt-4o`
   - Model name: `text-embedding-3-large` → Deployment name: `text-embedding-3-large`

### Step 3: Container Configuration

Set container names in `.env`:

```env
# Input/Output containers
BLOB_INPUT_CONTAINER=input-document-center
BLOB_OUTPUT_CONTAINER=output-of-di
BLOB_CHUNK_CONTAINER=chunked-output
BLOB_INDEX_CONTAINER=faiss-indexes
BLOB_METADATA_CONTAINER=faiss-metadata
BLOB_TEMPLATES_CONTAINER=order-templates
BLOB_RESULTS_CONTAINER=order-design-documents
```

### Step 4: Application Configuration

```env
# FastAPI
API_KEY=your_secure_api_key_here
API_PORT=8000
DEBUG=false

# Models
CHAT_MODEL=gpt-4o
EMBEDDING_MODEL=text-embedding-3-large

# RAG Parameters
RETRIEVAL_K=20
RERANK_TOP_K=10
BM25_WEIGHT=0.4
VECTOR_WEIGHT=0.6

DEEP_DIVE_RETRIEVAL_K=25
DEEP_DIVE_RERANK_TOP_K=15
DEEP_DIVE_BM25_WEIGHT=0.3
DEEP_DIVE_VECTOR_WEIGHT=0.7

BATCH_SIZE=6
```

## Complete `.env` Template

```env
# ==================== AZURE CREDENTIALS ====================

# Document Intelligence
AZURE_DI_ENDPOINT=https://your-di-instance.cognitiveservices.azure.com/
AZURE_DI_API_KEY=your_di_api_key

# Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...

# OpenAI
OPENAI_ENDPOINT=https://your-openai.openai.azure.com/
OPENAI_KEY=your_openai_key
OPENAI_API_VERSION=2024-02-15-preview

# ==================== CONTAINER NAMES ====================

BLOB_INPUT_CONTAINER=input-document-center
BLOB_OUTPUT_CONTAINER=output-of-di
BLOB_CHUNK_CONTAINER=chunked-output
BLOB_INDEX_CONTAINER=faiss-indexes
BLOB_METADATA_CONTAINER=faiss-metadata
BLOB_TEMPLATES_CONTAINER=order-templates
BLOB_RESULTS_CONTAINER=order-design-documents

# ==================== APPLICATION CONFIG ====================

API_KEY=your_secure_api_key
API_PORT=8000
DEBUG=false

# ==================== MODEL CONFIG ====================

CHAT_MODEL=gpt-4o
EMBEDDING_MODEL=text-embedding-3-large

# ==================== RAG PARAMETERS ====================

# Initial retrieval
RETRIEVAL_K=20
RERANK_TOP_K=10
BM25_WEIGHT=0.4
VECTOR_WEIGHT=0.6

# Deep-dive (for null values)
DEEP_DIVE_RETRIEVAL_K=25
DEEP_DIVE_RERANK_TOP_K=15
DEEP_DIVE_BM25_WEIGHT=0.3
DEEP_DIVE_VECTOR_WEIGHT=0.7

# Batch processing
BATCH_SIZE=6
```

## Requirements.txt

Create `requirements.txt`:

```
# Azure Services
azure-ai-formrecognizer>=3.2.0
azure-storage-blob>=12.14.0
azure-search-documents>=11.4.0

# OpenAI
openai>=1.0.0

# Vector Search
faiss-cpu>=1.7.4  # or faiss-gpu for GPU support
sentence-transformers>=2.2.0  # For CrossEncoder
rank-bm25>=0.2.2

# Web Framework
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.0.0

# Document Processing
pdf2image>=1.16.0
PyPDF2>=3.0.0
python-docx>=0.8.11
openpyxl>=3.10.0

# Utilities
numpy>=1.24.0
dotenv>=0.21.0
requests>=2.31.0
```

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/your-org/transformer-spec-rag.git
cd transformer-spec-rag
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

For GPU support with FAISS:
```bash
pip install faiss-gpu
```

### 4. Configure Environment

Create `.env` file with all credentials (see template above)

### 5. Upload Templates

Upload order document templates to your Azure storage:

```bash
# Using Azure CLI
az storage blob upload \
  --container-name order-templates \
  --name Order_A.docx \
  --file ./templates/Order_A.docx \
  --connection-string $AZURE_STORAGE_CONNECTION_STRING

az storage blob upload \
  --container-name order-templates \
  --name Order_B.docx \
  --file ./templates/Order_B.docx \
  --connection-string $AZURE_STORAGE_CONNECTION_STRING
```

### 6. Start Application

```bash
# Production
uvicorn app:app --host 0.0.0.0 --port 8000

# Development with auto-reload
uvicorn app:app --reload
```

Visit: `http://localhost:8000`

## Chunking Parameters

Adjust these in `chunk_by_title_semantic_blob.py`:

```python
DocumentChunker(
    min_tokens=10,                    # Minimum chunk size
    max_characters=4000,              # Maximum chunk size
    new_after_n_chars=3800,           # Create new chunk after this size
    combine_text_under_n_chars=2000,  # Combine small sections
)
```

### Recommendations

| Use Case | min_tokens | max_chars | new_after |
|----------|-----------|-----------|-----------|
| **Dense** (technical specs) | 15 | 3000 | 2800 |
| **General** (mixed content) | 10 | 4000 | 3800 |
| **Sparse** (few tables) | 5 | 2000 | 1800 |

## RAG Search Parameters

Tune in `rag_query.py`:

```python
# Retrieval counts
RETRIEVAL_K = 20              # Chunks to retrieve initially
RERANK_TOP_K = 10             # Chunks to rerank

# Search weights
BM25_WEIGHT = 0.4             # Keyword relevance
VECTOR_WEIGHT = 0.6           # Semantic relevance

# Deep dive (when answer is null)
DEEP_DIVE_RETRIEVAL_K = 25    # More chunks for retry
DEEP_DIVE_RERANK_TOP_K = 15
DEEP_DIVE_BM25_WEIGHT = 0.3   # Less keyword, more semantic
DEEP_DIVE_VECTOR_WEIGHT = 0.7
```

### Optimization Guide

- **High precision needed?** Increase `RERANK_TOP_K` (more thorough)
- **Speed matters?** Decrease `RETRIEVAL_K` (fewer chunks)
- **Keyword-heavy docs?** Increase `BM25_WEIGHT`
- **Semantic docs?** Increase `VECTOR_WEIGHT`

## Azure Pricing

### Expected Monthly Costs

| Service | Tier | Estimate |
|---------|------|----------|
| **Document Intelligence** | S0 | $50-200 |
| **Azure Storage** | Hot | $20-50 |
| **OpenAI (GPT-4)** | Pay-as-go | $100-500* |
| **Azure Cognitive Search** | Basic | $50-200 (optional) |
| | **Total** | | **$220-950** |

*Depends on query volume and token usage

### Cost Optimization Tips

1. **Batch DI processing** - Process multiple pages at once
2. **Cache embeddings** - Reuse FAISS indexes
3. **Off-peak queries** - Schedule batch jobs at night
4. **Smaller models** - Use `gpt-4o-mini` for simple queries
5. **Short contexts** - Limit RAG chunk retrieval

## Verification Checklist

- [ ] `.env` file created with all credentials
- [ ] All 7 containers created in Azure Storage
- [ ] Document Intelligence deployed
- [ ] OpenAI models deployed (gpt-4o, text-embedding-3-large)
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Virtual environment activated
- [ ] Order templates uploaded to blob storage
- [ ] Application starts without errors
- [ ] Can access http://localhost:8000

## Troubleshooting

### "AuthenticationError: Invalid credentials"

**Problem:** .env credentials are wrong

**Solution:**
```bash
# Check credentials in Azure Portal
# Update .env file
# Verify no extra spaces in keys
```

### "ContainerNotFound: The specified container does not exist"

**Problem:** Container was not created

**Solution:**
```bash
az storage container create \
  --name missing-container \
  --connection-string $AZURE_STORAGE_CONNECTION_STRING
```

### "No module named 'faiss'"

**Problem:** FAISS not installed

**Solution:**
```bash
pip install faiss-cpu  # or faiss-gpu
```

### "OPENAI_API_KEY is not defined"

**Problem:** .env not loaded

**Solution:**
```bash
# Check .env exists in project root
# Check python-dotenv is installed
pip install python-dotenv
```

---

**Next:** [Installation Guide](installation.md) → Complete setup steps
