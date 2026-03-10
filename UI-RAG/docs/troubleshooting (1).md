# Troubleshooting

## Installation Issues

### "ModuleNotFoundError: No module named 'fastapi'"

**Problem:** Dependencies not installed.

**Solution:**
```bash
# Verify venv is activated
which python  # Should show path with 'venv'

# Reinstall
pip install -r requirements.txt
```

### "FAISS installation failed"

**Problem:** FAISS needs compilation.

**Solution:**
```bash
# Use precompiled version
pip install faiss-cpu==1.7.4

# Or GPU version if you have CUDA
pip install faiss-gpu
```

## Azure Authentication

### "AuthenticationError: Invalid credentials"

**Problem:** .env credentials are wrong.

**Solution:**
1. Go to Azure Portal
2. Find your resource (Document Intelligence, Storage Account, OpenAI)
3. Copy correct credentials
4. Update .env file
5. Verify no extra spaces

```bash
# Check .env syntax
cat .env | grep AZURE_DI_API_KEY
# Should be: AZURE_DI_API_KEY=actual_key
```

### "ContainerNotFound: The specified container does not exist"

**Problem:** Blob Storage containers weren't created.

**Solution:**
```bash
# Create missing containers
az storage container create \
  --name input-document-center \
  --connection-string $AZURE_STORAGE_CONNECTION_STRING

# Create all containers
for container in input-document-center output-of-di chunked-output faiss-indexes faiss-metadata order-templates order-design-documents; do
  az storage container create --name $container --connection-string $AZURE_STORAGE_CONNECTION_STRING
done
```

## API Errors

### "401 Unauthorized"

**Problem:** Invalid API key.

**Solution:**
```bash
# Check API key in .env
grep API_KEY .env

# Header must match exactly
curl -H "X-API-Key: your_key" ...
```

### "404 Not Found - Project doesn't exist"

**Problem:** Project name typo or project not uploaded yet.

**Solution:**
```bash
# Verify project was uploaded
curl http://localhost:8000/files/ProjectName

# Check spelling matches exactly
# Project name is case-sensitive
```

### "500 Internal Server Error"

**Problem:** Azure service failed or backend error.

**Solution:**
```bash
# Check FastAPI logs
# Look for error messages in terminal

# Verify DI is running
curl $AZURE_DI_ENDPOINT/formrecognizer/v3.1-preview.1/analyze

# Check OpenAI connection
ping $OPENAI_ENDPOINT
```

## Processing Issues

### "No chunks found"

**Problem:** Document Extraction failed silently.

**Solution:**
1. Check DI extraction completed:
   ```bash
   # Look in Azure blob
   # output-of-di/ProjectName/ should have JSON files
   ```
2. Re-run extraction manually:
   ```python
   from doc_extraction_using_di import TransformerDocumentProcessor
   processor = TransformerDocumentProcessor()
   processor.process_project("ProjectName")
   ```

### "Questions not answered" (all null)

**Problem:** RAG not finding relevant chunks.

**Solutions:**
1. Check chunks exist:
   ```bash
   # Verify chunked-output/all_chunks.json exists
   ```
2. Chunks might be too small - increase retrieval:
   ```python
   # In rag_query.py
   RETRIEVAL_K = 30  # Try higher number
   ```
3. Check document quality - might need better formatting

### "Template not found"

**Problem:** Order template missing from blob storage.

**Solution:**
```bash
# Upload templates
az storage blob upload \
  --container-name order-templates \
  --name Order_A.docx \
  --file ./Order_A.docx
```

## Performance Issues

### Processing taking too long

**Solutions:**
1. **Check document size** - Large PDFs take longer
2. **Reduce features:**
   ```python
   # Skip image detection
   detect_image_pages = False
   
   # Increase chunk size
   DocumentChunker(max_characters=5000)
   ```
3. **Use background processing** - Don't wait for completion

### High memory usage

**Problem:** FAISS index too large.

**Solutions:**
1. **Use GPU:** `pip install faiss-gpu`
2. **Quantize index** - Reduces memory
3. **Split project** - Process smaller batches
4. **Increase server RAM** - Upgrade instance

### Slow embeddings

**Problem:** Embedding API is slow.

**Solutions:**
1. **Check Azure quota** - May be rate-limited
2. **Batch process** - Process multiple at once
3. **Use smaller model:**
   ```env
   EMBEDDING_MODEL=text-embedding-3-small
   ```

## Document Issues

### PDF text extraction poor

**Problem:** Scanned PDF (image-based).

**Solutions:**
1. **Use original PDF** - Not scanned copy
2. **Check PDF quality** - Try rescan
3. **Use OCR preprocessing** - Before upload
4. **Split document** - Try smaller sections

### Tables not extracting

**Problem:** Complex table layout.

**Solutions:**
1. **Simplify table** - Remove merged cells
2. **Check DI JSON** - Verify table exists:
   ```bash
   # In output-of-di/ JSON, look for "tables" field
   ```
3. **Manual review** - Verify extraction quality

### Special characters causing issues

**Problem:** Non-ASCII characters.

**Solution:**
- Usually handled automatically
- Check .env file encoding: `UTF-8`
- Verify document encoding

## Frontend Issues

### React UI not loading

**Problem:** Static files not served.

**Solution:**
```bash
# Build frontend
cd frontend
npm run build

# Check it's mounted in app.py
# app.mount("/", StaticFiles(...))
```

### API calls failing from frontend

**Problem:** CORS error.

**Solution:**
1. Check CORS middleware in app.py
2. Add frontend URL to allowed_origins:
   ```python
   allow_origins=["http://localhost:3000"]
   ```

## Database/Storage Issues

### "Azure Storage timeout"

**Problem:** Network or API slowness.

**Solution:**
```bash
# Retry upload
# Check Azure Service Health

# Increase timeout if needed
# In code: timeout=30
```

### "Index corrupted"

**Problem:** FAISS index file damaged.

**Solution:**
```bash
# Rebuild index
rag = RAGPipeline(project_name="MyProject")
rag.build_indexes(chunks)
```

## Common Error Messages

| Error | Cause | Fix |
|-------|-------|-----|
| "Connection timeout" | Network issue | Check internet |
| "Quota exceeded" | Rate limited | Wait or upgrade |
| "Invalid format" | Unsupported file | Use PDF/DOCX/XLSX |
| "File corrupted" | Upload failed | Try again |
| "Key not found" | Missing credential | Check .env |

## Getting Help

1. **Check logs:**
   ```bash
   # Docker logs
   docker logs container_id
   
   # Local output
   # Terminal where uvicorn is running
   ```

2. **Check Azure Portal:**
   - Resource status
   - API usage
   - Error logs

3. **Verify configuration:**
   ```bash
   python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('AZURE_DI_ENDPOINT'))"
   ```

4. **Test connectivity:**
   ```bash
   curl -I https://your-di.cognitiveservices.azure.com/
   ```

---

**Still stuck?** → [FAQ](faq.md) or check module-specific docs
