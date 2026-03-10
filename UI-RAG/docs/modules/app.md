# FastAPI Backend (app.py)

## Overview

The FastAPI backend orchestrates the entire pipeline and provides REST API endpoints.

**Module:** `app.py`

**Framework:** FastAPI + Uvicorn

**Features:**
- Pipeline orchestration
- REST API endpoints
- Background task processing
- Static file serving (React frontend)
- CORS middleware

## REST API Endpoints

### 1. Upload & Process

**Endpoint:** `POST /upload`

Trigger full pipeline for a project:

```bash
curl -X POST http://localhost:8000/upload \
  -H "X-API-Key: your_key" \
  -F "project_name=Energinet_onshore_offshore" \
  -F "files=@spec1.pdf" \
  -F "files=@spec2.docx"
```

**Parameters:**
- `project_name` (str, form): Project folder name
  - Format: `ProjectName_onshore_offshore`
  - Or: `ProjectName_onshore` or `ProjectName_offshore`
- `files` (file, form): Multiple files to upload

**Returns:**
```json
{
  "status": "processing",
  "project_name": "Energinet_onshore_offshore",
  "message": "Pipeline started",
  "files_processed": 2
}
```

**Pipeline Flow:**
1. Upload files to input-document-center
2. Extract with Document Intelligence
3. Chunk semantically
4. Build FAISS indexes
5. Run RAG queries
6. Fill templates
7. Save results

### 2. Check Status

**Endpoint:** `GET /status/{project_name}`

Get processing status:

```bash
curl http://localhost:8000/status/Energinet_onshore_offshore
```

**Returns:**
```json
{
  "project": "Energinet_onshore_offshore",
  "status": "completed",
  "stages": {
    "extraction": "complete",
    "chunking": "complete",
    "indexing": "complete",
    "rag": "complete",
    "filling": "complete"
  },
  "files": 2,
  "chunks": 145,
  "timestamp": "2024-03-10T10:30:00"
}
```

### 3. Get Results

**Endpoint:** `GET /results/{project_name}`

Get extraction results and documents:

```bash
curl http://localhost:8000/results/Energinet_onshore_offshore
```

**Returns:**
```json
{
  "project": "Energinet_onshore_offshore",
  "answers": {
    "question_1": "answer_1",
    ...
  },
  "documents": [
    "Order_A.docx",
    "Order_B.docx"
  ],
  "metadata": {
    "generation_date": "2024-03-10",
    "chunks_used": 145,
    "pages": 42
  }
}
```

### 4. List Files

**Endpoint:** `GET /files/{project_name}`

List files in a project:

```bash
curl http://localhost:8000/files/Energinet_onshore_offshore
```

**Returns:**
```json
{
  "input_files": [
    {
      "name": "spec1.pdf",
      "size": 5242880,
      "status": "processed"
    }
  ],
  "output_files": [
    {
      "name": "Order_A.docx",
      "size": 1048576
    }
  ]
}
```

### 5. Health Check

**Endpoint:** `GET /health`

Check API health:

```bash
curl http://localhost:8000/health
```

**Returns:**
```json
{
  "status": "healthy",
  "timestamp": "2024-03-10T10:30:00",
  "version": "1.0.0"
}
```

### 6. Download Result

**Endpoint:** `GET /download/{project_name}/{filename}`

Download filled document:

```bash
curl http://localhost:8000/download/Energinet_onshore_offshore/Order_A.docx \
  > Order_A.docx
```

**Returns:** Binary DOCX file

## Authentication

API Key authentication:

```bash
# Required header
X-API-Key: your_api_key_here
```

**Configuration in .env:**
```env
API_KEY=your_secure_key_here
```

**Validation:**
```python
def verify_api_key(api_key: str = Header(...)):
    if api_key != os.getenv("API_KEY"):
        raise HTTPException(status_code=401)
```

## Background Tasks

Processing happens asynchronously:

```python
@app.post("/upload")
async def upload_files(
    files: List[UploadFile],
    project_name: str,
    background_tasks: BackgroundTasks
):
    # Start background processing
    background_tasks.add_task(process_pipeline, project_name)
    
    # Return immediately
    return {"status": "processing"}
```

**Benefits:**
- No timeout on large projects
- User gets response immediately
- Check status with `/status` endpoint

## CORS Configuration

Allows frontend to call API:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Static File Serving

Serves React frontend:

```python
app.mount("/", StaticFiles(directory="frontend/build"), name="static")
```

Access at: `http://localhost:8000/`

## Running the Server

### Development

```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Features:**
- Auto-reload on code changes
- Debug mode enabled
- Slower performance

### Production

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

**Configuration:**
```bash
uvicorn app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4 \
  --loop uvloop \
  --http httptools
```

## Configuration

### Environment Variables

```env
# API
API_KEY=secure_key_here
API_PORT=8000
DEBUG=false

# Azure
AZURE_STORAGE_CONNECTION_STRING=...
AZURE_DI_ENDPOINT=...
AZURE_DI_API_KEY=...
OPENAI_ENDPOINT=...
OPENAI_KEY=...

# Containers
BLOB_INPUT_CONTAINER=input-document-center
BLOB_OUTPUT_CONTAINER=output-of-di
# ... etc
```

## Error Handling

### HTTP Error Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Upload completed |
| 400 | Bad request | Missing project_name |
| 401 | Unauthorized | Invalid API key |
| 404 | Not found | Project doesn't exist |
| 500 | Server error | DI API failed |

### Error Response Format

```json
{
  "error": "Project not found",
  "details": "Energinet_onshore_offshore",
  "timestamp": "2024-03-10T10:30:00"
}
```

## Usage Examples

### Upload Project

```python
import requests

# Upload files
files = [
    ('files', open('spec1.pdf', 'rb')),
    ('files', open('spec2.docx', 'rb'))
]

response = requests.post(
    'http://localhost:8000/upload',
    files=files,
    data={'project_name': 'MyProject_onshore_offshore'},
    headers={'X-API-Key': 'your_key'}
)

print(response.json())
# {'status': 'processing', 'project_name': ...}
```

### Check Status

```python
import requests
import time

project = 'MyProject_onshore_offshore'

while True:
    response = requests.get(f'http://localhost:8000/status/{project}')
    status = response.json()
    
    print(f"Status: {status['status']}")
    
    if status['status'] == 'completed':
        break
    
    time.sleep(5)  # Check every 5 seconds
```

### Download Results

```python
import requests

response = requests.get(
    'http://localhost:8000/download/MyProject_onshore_offshore/Order_A.docx'
)

# Save file
with open('Order_A.docx', 'wb') as f:
    f.write(response.content)
```

## Deployment

### Docker

```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
```

Build:
```bash
docker build -t transformer-rag .
docker run -p 8000:8000 --env-file .env transformer-rag
```

### Azure App Service

```bash
az webapp up --name transformer-rag --runtime PYTHON:3.9
```

### Docker Compose

```yaml
version: '3'
services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - AZURE_STORAGE_CONNECTION_STRING=${AZURE_STORAGE_CONNECTION_STRING}
      - OPENAI_KEY=${OPENAI_KEY}
    volumes:
      - ./temp:/tmp
```

## Monitoring

### Logging

```python
import logging

logger = logging.getLogger(__name__)

logger.info(f"Processing project: {project_name}")
logger.error(f"Failed to process: {error}")
```

Check logs:
```bash
# Docker
docker logs container_id

# Local
tail -f app.log
```

### Metrics

Monitor:
- Request count
- Response time
- Error rate
- Queue size

---

**Next:** [Usage Guide](../usage.md) → Practical examples
