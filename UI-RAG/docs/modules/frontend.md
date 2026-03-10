# React Frontend Module

## Overview

The frontend is a React-based chat UI component for uploading documents and querying specifications.

**Component:** `Docflow_chatui.jsx`  
**Interface:** `static/Index.HTML`

## Features

✅ Document Upload Interface  
✅ Project Management  
✅ Chat-style Query Interface  
✅ Results Display  
✅ Language Selection (EN/DE)  
✅ Progress Tracking  
✅ File Download  

## Component Structure

### Docflow_chatui.jsx

Main React component with:

```jsx
function DocflowChatUI() {
  // State management
  const [projectName, setProjectName] = useState("");
  const [files, setFiles] = useState([]);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  
  // Main functions
  const handleUpload = async () => { ... }
  const handleQuery = async () => { ... }
  const handleDownload = async () => { ... }
  const checkStatus = async () => { ... }
  
  return (
    <div className="docflow-ui">
      {/* UI components */}
    </div>
  );
}
```

## Features

### 1. Document Upload

**UI:**
- File input (multi-select)
- Project name input
- Upload button
- Progress indicator

**Functionality:**
```jsx
// Upload files to backend
POST /upload
  project_name: "MyProject"
  files: [file1.pdf, file2.docx]

// Response
{
  status: "processing",
  project_name: "MyProject",
  files_processed: 2
}
```

### 2. Project Management

**Features:**
- List existing projects
- View project status
- Delete projects (optional)
- Switch between projects

### 3. Chat Interface

**User experience:**
- Type questions
- Send to backend
- Receive answers
- Display in chat format
- History preservation

**Query flow:**
```
User: "What is the rated voltage?"
  ↓
POST /query/{project}
  question: "What is the rated voltage?"
  ↓
Response:
  answer: "110 kV"
  confidence: 0.95
```

### 4. Results Display

**Shows:**
- All extracted specifications
- Generated documents (downloadable)
- Metadata (pages, chunks, etc.)
- Generation timestamp

### 5. Language Support

**Auto-detection:**
- English (EN)
- German (DE)
- Responses in document language

**User selection:**
- Dropdown to force language
- UI language follows selection

## API Integration

### Endpoints Used

| Endpoint | Purpose | Example |
|----------|---------|---------|
| `POST /upload` | Upload documents | Upload project files |
| `GET /status/{project}` | Check progress | Monitor processing |
| `GET /results/{project}` | Get answers | Display specifications |
| `GET /download/{project}/{file}` | Download document | Get Order_A.docx |
| `GET /files/{project}` | List files | Show project contents |

### Request/Response Examples

**Upload:**
```javascript
const formData = new FormData();
formData.append("project_name", "MyProject");
formData.append("files", file1);
formData.append("files", file2);

fetch("http://localhost:8000/upload", {
  method: "POST",
  headers: {"X-API-Key": "your_key"},
  body: formData
})
```

**Get Status:**
```javascript
fetch(`http://localhost:8000/status/MyProject`)
  .then(r => r.json())
  .then(data => console.log(data.status))
```

**Get Results:**
```javascript
fetch(`http://localhost:8000/results/MyProject`)
  .then(r => r.json())
  .then(data => console.log(data.answers))
```

## UI Workflow

```
┌─────────────────────────────────────┐
│  1. Upload Section                  │
│  ├─ Select files                    │
│  ├─ Enter project name              │
│  └─ Click Upload                    │
└────────────┬────────────────────────┘
             ↓
┌─────────────────────────────────────┐
│  2. Processing Monitor              │
│  ├─ Show progress: Extracting...    │
│  ├─ Show stages: Chunking...        │
│  └─ Auto-refresh status             │
└────────────┬────────────────────────┘
             ↓
┌─────────────────────────────────────┐
│  3. Chat Interface                  │
│  ├─ Show extracted specs            │
│  ├─ User can ask questions          │
│  └─ Display answers                 │
└────────────┬────────────────────────┘
             ↓
┌─────────────────────────────────────┐
│  4. Results Display                 │
│  ├─ All specifications              │
│  ├─ Generated documents             │
│  └─ Download buttons                │
└─────────────────────────────────────┘
```

## Styling

**Framework:** (Typically Material-UI or custom CSS)

**Key Classes:**
```css
.docflow-ui { }           /* Main container */
.upload-section { }       /* File upload area */
.progress-section { }     /* Status display */
.chat-section { }         /* Chat interface */
.results-section { }      /* Results display */
.message { }              /* Chat message */
.loading { }              /* Loading indicator */
```

## State Management

```javascript
// Project/Upload State
projectName: string
files: File[]
uploadProgress: number
uploadStatus: "idle" | "uploading" | "processing" | "complete"

// Query State
messages: Array<{role, content}>
loading: boolean
currentProject: string
language: "en" | "de"

// Results State
results: {
  answers: Object,
  documents: string[],
  metadata: Object
}
downloadProgress: number
```

## Error Handling

**Upload Errors:**
```javascript
if (files.size > 500MB) {
  showError("File too large");
}

try {
  const response = await fetch("/upload", ...);
  if (!response.ok) {
    showError(`Upload failed: ${response.status}`);
  }
} catch (error) {
  showError(`Network error: ${error.message}`);
}
```

**Query Errors:**
```javascript
if (response.status === 404) {
  showError("Project not found");
}
if (response.status === 401) {
  showError("Unauthorized - check API key");
}
```

## Customization

### Add New Query Type

```jsx
// In chat handler
const customQuery = async (question) => {
  const response = await fetch(
    `/query/${projectName}`,
    {
      method: "POST",
      headers: {"X-API-Key": API_KEY},
      body: JSON.stringify({question})
    }
  );
  return response.json();
}
```

### Change Styling

```jsx
// In component
const styles = {
  container: {
    maxWidth: "900px",
    margin: "0 auto",
    padding: "20px"
  },
  // ... more styles
}
```

### Add New Language

```jsx
// In language handler
const LANGUAGES = {
  en: { uploadLabel: "Upload Files" },
  de: { uploadLabel: "Dateien hochladen" },
  fr: { uploadLabel: "Télécharger des fichiers" }
}
```

## Building & Deployment

### Local Development

```bash
# Install dependencies
npm install

# Development server
npm start

# Should serve on http://localhost:3000
```

### Build for Production

```bash
npm run build

# Creates build/ directory
# Copy contents to static/ folder
```

### Integration with FastAPI

```python
# In app.py
app.mount("/", StaticFiles(directory="static"), name="static")

# Serves Index.HTML on http://localhost:8000
```

## Performance Optimization

### Tips

1. **Lazy load results** - Don't show all at once
2. **Debounce search** - Wait for user to stop typing
3. **Cache API responses** - Avoid duplicate requests
4. **Compress files** - Before upload
5. **Show progress** - Long operations need feedback

### Example: Debounced Search

```jsx
const [searchTerm, setSearchTerm] = useState("");

useEffect(() => {
  const timer = setTimeout(() => {
    // Search only after 500ms of inactivity
    handleSearch(searchTerm);
  }, 500);
  
  return () => clearTimeout(timer);
}, [searchTerm]);
```

## Browser Compatibility

**Recommended:**
- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

**Requires:**
- ES6+ JavaScript support
- Fetch API
- FormData API

## Security Considerations

### API Key

```javascript
// Store API key securely
const API_KEY = process.env.REACT_APP_API_KEY;

// Include in all requests
headers: {
  "X-API-Key": API_KEY,
  "Content-Type": "application/json"
}
```

### File Upload Validation

```javascript
const validateFile = (file) => {
  // Check size
  if (file.size > 100_000_000) return false;
  
  // Check type
  const allowed = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"];
  return allowed.includes(file.type);
}
```

### CORS

```python
# In app.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

**Next:** [FastAPI Backend](app.md) documentation
