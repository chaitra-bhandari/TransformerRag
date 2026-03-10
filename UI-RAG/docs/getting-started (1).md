# Getting Started

## What You Have

Your project structure:

```
UI-COMPLETE/
├── .env                              # Your credentials
├── .venv/                            # Python environment
├── app.py                            # FastAPI backend
├── rag_query.py                      # RAG engine
├── chunk_by_title_semantic_blob.py   # Chunking
├── doc_extraction_using_di.py        # Document extraction
├── doc_filling_blob.py               # Document generation
├── Docflow_chatui.jsx                # React chat UI
├── static/Index.HTML                 # Web interface
└── temp_uploads/                     # Temp files
```

## 5-Minute Quick Start

### 1. Activate Virtual Environment

```bash
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

### 2. Verify Dependencies

```bash
pip list | grep -E "fastapi|azure|faiss|openai"
```

If missing, install:
```bash
pip install -r requirements.txt
```

### 3. Check .env File

Verify `.env` has all credentials:
```bash
cat .env | grep AZURE_DI_ENDPOINT
```

Should show your Azure endpoints and keys.

### 4. Start Backend

```bash
uvicorn app:app --reload --port 8000
```

You should see:
```
Uvicorn running on http://127.0.0.1:8000
```

### 5. Open Web UI

Visit: **http://localhost:8000**

You should see the Docflow chat interface!

### 6. Upload Your First Project

1. Click **Upload Files**
2. Select a PDF/DOCX
3. Enter project name: `MyFirst_Test`
4. Click **Upload**
5. Watch the progress bar
6. See results when complete!

## That's It! 🎉

Your system is working end-to-end.

## Next Steps

- **Upload more documents** → See it extract specs
- **Understand the flow** → Read [Architecture](architecture.md)
- **Customize questions** → Edit [RAG Module](modules/rag-query.md)
- **Deploy to cloud** → Check [Configuration](configuration.md)

## Common Issues

| Issue | Solution |
|-------|----------|
| Port 8000 in use | `uvicorn app:app --port 8001` |
| .env not loading | Ensure .env is in project root |
| Azure auth fails | Check credentials in .env |
| Frontend not showing | Ensure `static/Index.HTML` exists |

## Project Structure Guide

See [Project Structure](project-structure.md) for complete directory layout.

---

**Ready to dive deeper?** → [Architecture](architecture.md) explains the pipeline
