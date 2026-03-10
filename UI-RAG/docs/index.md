# Transformer Spec RAG

**Intelligent Document Extraction & Specification Generation using Retrieval-Augmented Generation**

Transform unstructured transformer specification documents into structured, actionable data with AI-powered extraction and automatic document generation.

## What is Transformer Spec RAG?

Transformer Spec RAG is an end-to-end system that:

- **📄 Extracts** specifications from technical documents (PDFs, DOCX, XLSX)
- **🔍 Chunks** documents semantically for efficient retrieval
- **🤖 Uses RAG** (Retrieval-Augmented Generation) to answer specification queries
- **📝 Generates** structured order documents automatically
- **🌍 Supports** multiple languages (English, German)

## Key Features

| Feature | Description |
|---------|-------------|
| **Azure Document Intelligence** | Extract text, tables, and metadata from documents |
| **Semantic Chunking** | Smart document segmentation by title and content |
| **Vector Search** | FAISS-based semantic search with BM25 hybrid retrieval |
| **RAG Pipeline** | Context-aware question answering with GPT-4 |
| **Automatic Document Filling** | Generate order documents with extracted specifications |
| **Language Detection** | Auto-detect German/English and respond in same language |
| **Batch Processing** | Process multiple projects efficiently |

## Pipeline Overview

```
Raw Documents
    ↓
[1] Azure Document Intelligence
    ↓ Extract text, tables, metadata
    ↓
[2] Semantic Chunking
    ↓ Split by title, remove noise
    ↓
[3] Vector Indexing (FAISS)
    ↓ Create embeddings & BM25 index
    ↓
[4] RAG Query Engine
    ↓ Retrieve & generate answers
    ↓
[5] Document Generation
    ↓
Filled Order Documents
```

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Azure Services
```bash
# Create .env file with:
AZURE_DI_ENDPOINT=https://your-di.cognitiveservices.azure.com/
AZURE_DI_API_KEY=your_api_key
AZURE_STORAGE_CONNECTION_STRING=your_connection_string
```

### 3. Upload Documents
```python
# Upload to Azure Blob Storage
# input-document-center/ProjectName_onshore_offshore/
```

### 4. Start Processing
```bash
python app.py
```

Your extracted specifications and generated documents will be available in:
- `output-of-di/` - Extracted document data
- `chunked-output/` - Document chunks
- `order-design-documents/` - Generated order documents

## Project Structure

```
├── app.py                          # FastAPI backend & orchestration
├── doc_extraction_using_di.py      # Azure Document Intelligence
├── chunk_by_title_semantic_blob.py # Semantic chunking engine
├── rag_query.py                    # RAG query & retrieval
├── doc_filling_blob.py             # Document generation
├── Docflow_chatui.jsx              # React frontend chat UI
├── Index.HTML                      # Chat interface
└── docs/                           # This documentation
```

## Use Cases

- **Transformer Specification Extraction** - Automatically extract specs from technical docs
- **Document Standardization** - Generate consistent order documents
- **Knowledge Base Creation** - Build searchable document databases
- **Specification Comparison** - Query multiple documents for data comparison
- **Regulatory Compliance** - Ensure specifications meet standards

## Technology Stack

| Component | Technology |
|-----------|-----------|
| **Document Extraction** | Azure Document Intelligence (Form Recognizer) |
| **Vector Search** | FAISS + OpenAI Embeddings |
| **Ranking** | BM25 + Cross-Encoder |
| **LLM** | Azure OpenAI (GPT-4o) |
| **Backend** | FastAPI + Python |
| **Frontend** | React + Material UI |
| **Storage** | Azure Blob Storage |
| **Search Index** | Azure AI Search |

## Documentation Guide

- **[Getting Started](getting-started.md)** - Setup and first steps
- **[Architecture](architecture.md)** - System design and pipeline
- **[Installation](installation.md)** - Detailed setup instructions
- **[Configuration](configuration.md)** - Environment and system setup
- **[Modules](modules/overview.md)** - Each component explained
- **[Usage Guide](usage.md)** - Practical examples
- **[API Reference](api-reference.md)** - Complete function docs
- **[Troubleshooting](troubleshooting.md)** - Common issues & solutions
- **[FAQ](faq.md)** - Frequently asked questions

## System Requirements

- **Python** 3.8+
- **Azure Subscription** (Document Intelligence, Blob Storage, OpenAI)
- **4GB RAM** minimum (8GB recommended)
- **Internet connection** for Azure services

## Performance Metrics

- **Document Processing**: ~5-10 seconds per page
- **Chunking Speed**: ~100 MB/minute
- **Query Response Time**: ~2-5 seconds (with context retrieval)
- **Supported Document Size**: Up to 500 MB
- **Concurrent Users**: 10+ with standard Azure tier

## Next Steps

1. **[Get Started](getting-started.md)** - Follow setup guide
2. **[Understand Architecture](architecture.md)** - Learn how it works
3. **[Configure System](configuration.md)** - Set up Azure services
4. **[Run Your First Project](usage.md)** - Process your first document

## Support & Resources

- 📖 **[Full Documentation](.)** - Complete guides
- 🐛 **[Troubleshooting](troubleshooting.md)** - Common issues
- ❓ **[FAQ](faq.md)** - Quick answers
- 📧 **GitHub Issues** - Report bugs and request features

## License

MIT License - See LICENSE file for details

---

**Ready to get started?** → **[Go to Getting Started](getting-started.md)** 🚀
