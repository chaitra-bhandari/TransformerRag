"""
Transformer Spec RAG — FastAPI Backend
=================================================================
Pipeline flow (triggered on every new project upload):
  1. DI extraction        → output-of-di/{project}/
  2. Chunking             → chunked-output/all_chunks.json
  3. Azure AI Search indexing → vector search index
  4. RAG extraction       → JSON from rag_query.py 
  5. Order doc generation → order-design-documents/{project}/Order_A.docx
                            order-design-documents/{project}/Order_B.docx

Containers (configured in .env):
  - transformer-input          : uploaded raw PDFs
  - output-of-di               : DI JSON results
  - chunked-output             : all_chunks.json
  - order-templates            : Order_A.docx, Order_B.docx templates
  - order-design-documents     : generated/filled order documents
"""

import os
import re
import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional, List
import io
import os as os_module
from dotenv import load_dotenv
load_dotenv()
import faiss
import numpy as np
import pickle
import tempfile
import io
import os as os_module
from azure.storage.blob import BlobServiceClient
from openai import AzureOpenAI
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Header, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel


#Congifiguring values from .env
API_KEY                    = os.getenv("API_KEY", "")
AZURE_CONN_STR             = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
BLOB_INPUT_CONTAINER       = os.getenv("BLOB_INPUT_CONTAINER",       "transformer-input")
BLOB_OUTPUT_CONTAINER      = os.getenv("BLOB_OUTPUT_CONTAINER",      "output-of-di")
BLOB_DESIGN_DOCS_CONTAINER = os.getenv("BLOB_DESIGN_DOCS_CONTAINER", "order-design-documents")

#Azure AI Search config
AZURE_SEARCH_ENDPOINT      = os.getenv("AZURE_SEARCH_ENDPOINT", "")
AZURE_SEARCH_KEY           = os.getenv("AZURE_SEARCH_KEY", "")
AZURE_SEARCH_INDEX         = os.getenv("AZURE_SEARCH_INDEX", "transformer-chunks")

#OpenAI config
OPENAI_KEY                 = os.getenv("OPENAI_KEY", "")
OPENAI_ENDPOINT            = os.getenv("OPENAI_ENDPOINT", "")
CHAT_MODEL                 = os.getenv("CHAT_MODEL", "gpt-4o")

TEMP_DIR = Path("temp_uploads")
TEMP_DIR.mkdir(exist_ok=True)
Path("static").mkdir(exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx"}
MAX_FILE_SIZE_MB   = 100
MAX_FILE_SIZE_B    = MAX_FILE_SIZE_MB * 1024 * 1024
EMBEDDING_MODEL = "text-embedding-3-large"
if not API_KEY:
    print(" WARNING: API_KEY not set in .env — all routes are unprotected!")



# APP + MIDDLEWARE
app = FastAPI(title="Transformer Spec RAG", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",      # React dev server default
        "http://127.0.0.1:3000",
        "http://localhost:5173",      # Vite dev server default
        "http://127.0.0.1:5173",
        "http://localhost:8080",      # Other common ports
        "http://127.0.0.1:8080",
    ],
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    allow_credentials=True,
    expose_headers=["Content-Disposition", "Content-Type", "Content-Length"],
    max_age=600,
)

app.mount("/static", StaticFiles(directory="static"), name="static")




def sanitize_name(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name.strip())


def make_blob_folder(project_name: str, transformer_type: str = None) -> str:
    safe = sanitize_name(project_name)
    if transformer_type and transformer_type != "none":
        return f"{safe}_{transformer_type}/"
    return f"{safe}/"


def validate_file(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"'{filename}': type '{ext}' not allowed. Accepted: {', '.join(ALLOWED_EXTENSIONS)}"
    return ""



#Upload all the docs from UI into blob: input-document-center
def upload_file_to_blob(local_path: Path, blob_path: str):
    from azure.storage.blob import BlobServiceClient
    client    = BlobServiceClient.from_connection_string(AZURE_CONN_STR)
    container = client.get_container_client(BLOB_INPUT_CONTAINER)
    with open(local_path, "rb") as f:
        container.upload_blob(name=blob_path, data=f, overwrite=True)
    print(f"[BLOB] Uploaded: {local_path.name} → {BLOB_INPUT_CONTAINER}/{blob_path}")

#Extract the data from PDFs using document intelligence, and store the output json in output-of-di
def trigger_di_processing(project_name: str, blob_folder: str):
    from doc_extraction_using_di import TransformerDocumentProcessor
    processor = TransformerDocumentProcessor()
    processor.process_project(blob_folder)
    print(f"[DI] Completed: {blob_folder}")

#Chunk all DI JSONs → chunked-output/all_chunks.json
def trigger_chunking(project_name: str, blob_folder: str):
    from chunk_by_title_semantic_blob import DocumentChunker
    chunker = DocumentChunker()
    chunker.process_all_projects()
    chunker.save_chunks()
    print(f"[CHUNKING] Completed: {project_name}")

#Run RAG extraction then fill Order A and Order B templates.
def trigger_order_generation(project_name: str):
    """
    Flow:
      1. query_rag()  → uses Azure AI Search + LLM
                        → extracts all parameters from rag_query.py
                        → returns combined JSON string
      2. DocxFiller() → downloads template from order-templates/
                        → fills it with the extracted JSON
                        → uploads filled .docx to order-design-documents/{project_name}/
    """
    from rag_query import query_rag
    from doc_filling_blob import DocxFiller

    print(f"\n[ORDER GEN] Starting RAG extraction for project: {project_name}")

    #RAG extraction (one run covers both orders — same data source)
    try:
        json_str  = query_rag(query=project_name, project_name=project_name)
        json_data = json.loads(json_str)
        json_dir = Path("extracted_json")
        json_dir.mkdir(exist_ok=True)

# Save JSON to local file for evaluation
        json_filename = json_dir / f"{project_name}_extracted.json"

        with open(json_filename, 'w', encoding='utf-8') as f:
         json.dump(json_data, f, indent=2, ensure_ascii=False)

        print(f"[ORDER GEN] JSON saved locally: {json_filename}")
        print(f"[ORDER GEN] RAG extraction complete — {len(json_data)} parameters extracted")
        print(f"[ORDER GEN] Parameters: {list(json_data.keys())}")
        if len(json_data) <= 3:
            print(f"[ORDER GEN] JSON content: {json.dumps(json_data, indent=2)[:500]}")
    except Exception as e:
        print(f"[ORDER GEN ERROR] RAG extraction failed: {e}")
        raise

    # Fill Order A and Order B with the same extracted JSON
    for order_type in ["A", "B"]:
        try:
            print(f"[ORDER GEN] Filling Order {order_type} for {project_name}...")
            filler    = DocxFiller(json_data, order_type=order_type)
            blob_path = filler.run(project_name=project_name)
            print(f"[ORDER GEN] Order {order_type} saved → {blob_path}")
        except Exception as e:
            # Log and continue — don't abort the whole pipeline if one order fails
            print(f"[ORDER GEN ERROR] Order {order_type} failed: {e}")


# BACKGROUND PIPELINE


async def run_pipeline(project_name: str, blob_folder: str):
    """
    Full end-to-end pipeline. Runs in background after file upload.
    DI → Chunking → RAG Extraction → Order Doc Generation
    """
    try:
        print(f"\n{'='*70}")
        print(f"[PIPELINE] Starting for project: {project_name}")
        print(f"[PIPELINE] Blob folder: {blob_folder}")
        print(f"{'='*70}")

        #  1: Document Intelligence
        print(f"\n[PIPELINE] Step 1/3 — Document Intelligence")
        trigger_di_processing(project_name, blob_folder)

        #  2: Chunking
        print(f"\n[PIPELINE] Step 2/3 — Chunking")
        trigger_chunking(project_name, blob_folder)

        #  3: RAG Extraction + Order Document Generation
        print(f"\n[PIPELINE] Step 3/3 — RAG Extraction & Order Generation")
        trigger_order_generation(project_name)

        print(f"\n{'='*70}")
        print(f"[PIPELINE]  DONE: {project_name}")
        print(f"{'='*70}\n")

    except Exception as e:
        print(f"\n[PIPELINE ERROR] {project_name}: {e}")
        import traceback
        traceback.print_exc()



# ORDER LOOKUP  (reads from order-design-documents container)
def find_order_in_blob(order_type: str, project_name: str,
                       transformer_filter: str = None) -> dict:
    """
    Search order-design-documents/{project_name}/ for an Order A or B docx.
    Returns {"found": True/False, ...}
    """
    from azure.storage.blob import BlobServiceClient

    blob_svc         = BlobServiceClient.from_connection_string(AZURE_CONN_STR)
    design_container = blob_svc.get_container_client(BLOB_DESIGN_DOCS_CONTAINER)

    prefix    = f"{project_name}/"
    all_blobs = list(design_container.list_blobs(name_starts_with=prefix))

    if not all_blobs:
        return {
            "found":   False,
            "reason":  "no_project",
            "message": (
                f"No documents found for project '{project_name}'.\n"
                f"Upload your spec files first using the 'New Project' option."
            )
        }

    matches = []
    for blob in all_blobs:
        blob_lower  = blob.name.lower()
        order_match = (f"order_{order_type.lower()}" in blob_lower or
                       f"order {order_type.lower()}" in blob_lower or
                       f"order{order_type.lower()}"  in blob_lower)
        if not order_match:
            continue
        if transformer_filter and transformer_filter.lower() not in blob_lower:
            continue
        matches.append(blob.name)

    if not matches:
        available  = [b.name.split('/')[-1] for b in all_blobs]
        filter_msg = f" ({transformer_filter})" if transformer_filter else ""
        return {
            "found":   False,
            "reason":  "not_generated",
            "message": (
                f"Order {order_type}{filter_msg} not yet generated for '{project_name}'.\n"
                f"Available files: {', '.join(available) if available else 'none'}\n"
                f"Generating now — please wait a moment and try again."
            )
        }

    if len(matches) > 1:
        filenames = [m.split('/')[-1] for m in matches]
        return {
            "found":   False,
            "reason":  "ambiguous",
            "message": (
                f"Multiple Order {order_type} files found for '{project_name}':\n" +
                "\n".join([f"  • {f}" for f in filenames]) + "\n\n"
                f"Please specify: 'Order {order_type} onshore' or 'Order {order_type} offshore'"
            )
        }

    return {
        "found":     True,
        "blob_name": matches[0],
        "filename":  matches[0].split('/')[-1]
    }



# RAG / CHAT HELPERS
def run_rag_query(message: str, project_name: str, transformer_type: str) -> str:
    from rag_query import query_rag
    return query_rag(query=message, project_name=project_name)


def answer_general_question(message: str, project_name: str) -> str:
    """
    Answer general questions using FAISS index from Azure containers + OpenAI
    
    Uses the SAME filtering logic as rag_query.py but with VECTOR SEARCH ONLY
    
    Flow:
    1. Download FAISS index from Azure blob
    2. Download metadata pickle from Azure blob
    3. Prepare project (filter chunks by project_name upfront)
    4. Embed query with OpenAI
    5. Search FAISS with larger k to account for filtering
    6. Filter vector results by project chunks
    7. Build context from filtered chunks
    8. Call OpenAI to generate answer
    9. Return answer with sources
    
    Args:
        message: User's question
        project_name: Project to filter chunks for
    
    Returns:
        Answer text with sources
    """
    try:
        print("\n\n========== ANSWER_GENERAL_QUESTION CALLED ==========")
        print(f"Message: {message}")
        print(f"Project: {project_name}")
        print("=" * 60 + "\n")
        
        # Validate credentials
        if not AZURE_CONN_STR:
            return "Error: Azure Storage credentials not configured in .env"
        
        if not OPENAI_KEY or not OPENAI_ENDPOINT:
            return "Error: OpenAI credentials not configured in .env"
        
        print(f"[Q&A] Starting Q&A for project: {project_name}")
        
        # Initialize Azure Blob Client ───
        blob_client = BlobServiceClient.from_connection_string(AZURE_CONN_STR)
        
        # Step 1: Download FAISS index ───
        print(f"[Q&A] Downloading FAISS index...")
        index_container = blob_client.get_container_client("faiss-indexes")
        
        try:
            index_blob = index_container.get_blob_client("docs.index")
            index_data = index_blob.download_blob().readall()
            
            # Write temporarily to disk (FAISS requires file path)
            with tempfile.NamedTemporaryFile(delete=False, suffix=".index") as tmp:
                tmp.write(index_data)
                tmp_path = tmp.name
            
            # Load from temporary file
            index = faiss.read_index(tmp_path)
            
            # Clean up temp file
            os_module.remove(tmp_path)
            
            print(f"[Q&A] FAISS index loaded: {index.ntotal} total vectors")
        except Exception as e:
            print(f"[Q&A] Error loading index: {str(e)}")
            return f"Error: Could not load FAISS index. {str(e)}"
        
        # 2: Download metadata pickle ───
        print(f"[Q&A] Downloading metadata...")
        metadata_container = blob_client.get_container_client("faiss-metadata")
        
        try:
            metadata_blob = metadata_container.get_blob_client("docs.pkl")
            metadata_data = metadata_blob.download_blob().readall()
            
            # Load pickle from bytes (no temp file needed)
            all_metadata = pickle.load(io.BytesIO(metadata_data))
            
            print(f"[Q&A] Metadata loaded: {len(all_metadata)} total chunks")
        except Exception as e:
            print(f"[Q&A] Error loading metadata: {str(e)}")
            return f"Error: Could not load metadata. {str(e)}"
        
        # Step 3: PREPARE PROJECT - Filter to project chunks only ───
        # This is the KEY step from rag_query.py!
        print(f"[Q&A] Preparing project-specific indices...")
        project_indices = set()
        
        for i, chunk in enumerate(all_metadata):
            chunk_project = chunk.get('metadata', {}).get('project_name', '').strip().lower()
            if chunk_project == project_name.strip().lower():
                project_indices.add(i)
        
        if not project_indices:
            print(f"[Q&A] No chunks found for project '{project_name}'")
            return f"No relevant information found for project '{project_name}'."
        
        print(f"[Q&A] Found {len(project_indices)} chunks for project '{project_name}'")
        
        # Step 4: Initialize OpenAI client and embed query 
        print(f"[Q&A] Embedding query...")
        
        openai_client = AzureOpenAI(
            api_key=OPENAI_KEY,
            api_version="2024-02-15-preview",
            azure_endpoint=OPENAI_ENDPOINT
        )
        
        try:
            embedding_response = openai_client.embeddings.create(
                input=[message],
                model=EMBEDDING_MODEL
            )
            query_embedding = np.array([embedding_response.data[0].embedding]).astype('float32')
        except Exception as e:
            print(f"[Q&A] Error embedding query: {str(e)}")
            return f"Error: Could not embed query. {str(e)}"
        
        #  5: VECTOR SEARCH with larger k (like rag_query.py)
        # Search with 3x k to account for filtering by project
        search_k = min(100, len(all_metadata))  # Use larger k like rag_query does
        print(f"[Q&A] Searching FAISS index (search_k={search_k})...")
        
        distances, indices = index.search(query_embedding, search_k)
        
        # 6: FILTER to project indices only (like rag_query.py) 
        valid_chunks = []
        
        for idx in indices[0]:
            if idx != -1 and idx < len(all_metadata) and idx in project_indices:
                chunk_metadata = all_metadata[idx]
                valid_chunks.append({
                    'content': chunk_metadata.get('content', ''),
                    'doc_name': chunk_metadata.get('metadata', {}).get('source_document', 'Unknown Document'),
                    'page': chunk_metadata.get('metadata', {}).get('page', 0),
                    'index': idx
                })
                
                # Stop at 20 chunks
                if len(valid_chunks) >= 20:
                    break
        
        if not valid_chunks:
            print(f"[Q&A] No valid chunks found after filtering")
            return f"No relevant information found for project '{project_name}'."
        
        print(f"[Q&A] Found {len(valid_chunks)} relevant chunks for project '{project_name}'")
        
        # 7: Build context from filtered chunks
        context_parts = []
        for chunk in valid_chunks:
            content = chunk['content'].strip()
            
            if content:  # Only add non-empty chunks
                context_parts.append(content)
                      
                        
            print(f"[DEBUG] ───── CHUNK {i}/{len(valid_chunks)} ─────")
           
            
            print(f"[DEBUG] Content Length: {len(content)} characters")
            print(f"[DEBUG] Content Preview (first 300 chars):")
            print(f"[DEBUG] {content[:50000]}")
            print(f"[DEBUG] Full Content:")
            print(f"[DEBUG] {content}")
            print(f"[DEBUG] ")
        
        context = "\n---\n".join(context_parts)
        context = context[:50000]  # Limit context size
        
        print(f"[DEBUG] Context size: {len(context)} characters from {len(valid_chunks)} chunks")
        
        if not context or len(context) < 50:
            print(f"[Q&A] Context too small or empty")
            return "Error: Retrieved chunks contain insufficient content to answer."
        
        #8: Call OpenAI 
        print(f"[Q&A] Calling OpenAI GPT model...")
        
        try:
            response = openai_client.chat.completions.create(
                model=CHAT_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            f"You are a technical assistant for the '{project_name}' project. "
                            f"Answer the user's question using ONLY the provided context. "
                            f"If the information is clearly in the context, provide it directly. "
                            f"Be precise and technical. "
                            f"Do not use markdown formatting (no **, __, ##, *, etc). "
                            f"If information is not in the context, say 'This information is not available in the current documents.'"
                        )
                    },
                    {
                        "role": "user",
                        "content": f"Context:\n{context}\n\nQuestion: {message}"
                    }
                ],
                temperature=0.2,
                max_tokens=1000
            )
            
            answer = response.choices[0].message.content
            print(f"[Q&A] OpenAI response received")
        except Exception as e:
            print(f"[Q&A] Error calling OpenAI: {str(e)}")
            return f"Error: Could not generate answer. {str(e)}"
        
        #  9: Clean up answer (remove markdown)
        answer = answer.replace("**", "")
        answer = answer.replace("__", "")
        answer = answer.replace("##", "")
        answer = answer.replace("*", "")
        answer = " ".join(answer.split())
        
        #Step 10: Build sources section
        sources_text = "\n\nSources:"
        
        for i, chunk in enumerate(valid_chunks[:5], 1):
            doc_name = chunk.get('doc_name', '') or 'Unknown Document'
            page = chunk.get('page', 0)
            
            if not doc_name or doc_name.strip() == '':
                doc_name = 'Unknown Document'
            
            # Clean up document name
            doc_name = doc_name.replace('.json', '').replace('.pdf', '').replace('.docx', '').strip()
            
            if page and page != 0:
                sources_text += f"\n{i}. {doc_name}, Page {page}"
            else:
                sources_text += f"\n{i}. {doc_name}"
        
        final_answer = answer + sources_text
        
        print(f"[Q&A] Answer generated successfully\n")
        return final_answer
        
    except Exception as e:
        print(f"[Q&A] Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error generating answer: {str(e)}"

#Parse project name from free-text message.
def extract_project_from_message(message: str) -> str:
    """
    Supported formats:
        "Energinet_VSR: what is the rated voltage?"
        "Energinet_VSR — what is the rated voltage?"
        "TenneT_715MVA what is the cost?"
        "for project TenneT_715MVA"
        "rated voltage for project TenneT_715MVA"
    """
    # Pattern 1: "ProjectName: ..."  /  "ProjectName — ..."  /  "ProjectName - ..."
    match = re.match(r'^([A-Za-z0-9_]+)\s*[:—\-]', message.strip())
    if match:
        return match.group(1)

    # Pattern 2: "... for project ProjectName" - get the ENTIRE word after "project"
    match = re.search(r'for\s+project\s+([A-Za-z0-9_]+)', message, re.IGNORECASE)
    if match:
        candidate = match.group(1)
        # Make sure it's not a common word
        if candidate.lower() not in ['the', 'a', 'an', 'onshore', 'offshore']:
            return candidate

    # Pattern 3: first token that looks like project name (has underscore or digits)
    tokens = message.strip().split()
    for token in tokens:
        if '_' in token and len(token) > 3:  # Project names usually have _ and reasonable length
            # Clean up any trailing punctuation
            token = token.rstrip('?.,!;:')
            if re.match(r'^[A-Za-z0-9_]+$', token):
                return token

    return None



# PYDANTIC MODELS
class ChatRequest(BaseModel):
    message:          str
    project_name:     Optional[str] = None
    transformer_type: Optional[str] = None


# ROUTES
@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    p = Path("static/index.html")
    return HTMLResponse(p.read_text(encoding="utf-8") if p.exists() else
                        "<h1>Place index.html in /static/</h1>")


@app.get("/api/projects")
async def list_projects():
    """
    List all projects from Order-Design-Docs container.
    Includes latest status and available orders for each.
    """
    from azure.storage.blob import BlobServiceClient
    
    blob_svc  = BlobServiceClient.from_connection_string(AZURE_CONN_STR)
    container = blob_svc.get_container_client(BLOB_DESIGN_DOCS_CONTAINER)
    
    # Get all blobs, extract unique project folders
    all_blobs = list(container.list_blobs())
    projects_dict = {}
    
    for blob in all_blobs:
        # blob.name is like "ProjectName/Order_A.docx"
        parts = blob.name.split('/')
        if len(parts) >= 2:
            project_name = parts[0]
            file_name    = parts[1]
            
            if project_name not in projects_dict:
                projects_dict[project_name] = {
                    "name": project_name,
                    "files": [],
                    "order_a": False,
                    "order_b": False,
                    "last_updated": blob.last_modified.isoformat() if blob.last_modified else None
                }
            
            projects_dict[project_name]["files"].append(file_name)
            
            if "order_a" in file_name.lower():
                projects_dict[project_name]["order_a"] = True
            elif "order_b" in file_name.lower():
                projects_dict[project_name]["order_b"] = True
    
    return {"projects": list(projects_dict.values())}

#Get detailed info for a specific project.
@app.get("/api/projects/{project_name}")
async def get_project_details(project_name: str):
   
    from azure.storage.blob import BlobServiceClient
    
    blob_svc  = BlobServiceClient.from_connection_string(AZURE_CONN_STR)
    container = blob_svc.get_container_client(BLOB_DESIGN_DOCS_CONTAINER)
    
    prefix = f"{project_name}/"
    blobs  = list(container.list_blobs(name_starts_with=prefix))
    
    if not blobs:
        raise HTTPException(status_code=404, detail=f"Project '{project_name}' not found.")
    
    return {
        "name": project_name,
        "files": [b.name.split('/')[-1] for b in blobs],
        "last_updated": blobs[0].last_modified.isoformat() if blobs else None
    }

#Create a new project and kick off the full pipeline.
@app.post("/api/projects/create")
async def create_new_project(
    project_name: str = Form(...),
    files: List[UploadFile] = File(...),
    background_tasks: BackgroundTasks = None
):
    """
    Files are temporarily uploaded, then pushed to Azure Blob.
    Pipeline is triggered in background.
    """
    # Validate inputs
    project_name = project_name.strip()
    if not project_name:
        raise HTTPException(400, "Project name cannot be empty.")
    
    if not files:
        raise HTTPException(400, "At least one file is required.")
    
    # Validate file extensions
    for file in files:
        error = validate_file(file.filename)
        if error:
            raise HTTPException(400, error)
        if file.size and file.size > MAX_FILE_SIZE_B:
            raise HTTPException(400,
                f"File '{file.filename}' exceeds max size ({MAX_FILE_SIZE_MB}MB)."
            )
    
    # Create temp folder for this project
    temp_project_dir = TEMP_DIR / sanitize_name(project_name)
    temp_project_dir.mkdir(exist_ok=True)
    
    try:
        # Save files to temp location
        saved_files = []
        for file in files:
            local_path = temp_project_dir / file.filename
            with open(local_path, "wb") as f:
                content = await file.read()
                f.write(content)
            saved_files.append(local_path)
            print(f"[TEMP] Saved: {local_path}")
        
        # Upload files to Azure Blob input container
        blob_folder = make_blob_folder(project_name)
        for local_path in saved_files:
            blob_path = f"{blob_folder}{local_path.name}"
            upload_file_to_blob(local_path, blob_path)
        
        # Kick off background pipeline
        print(f"[PROJECT] Created: {project_name}")
        if background_tasks:
            background_tasks.add_task(run_pipeline, project_name, blob_folder)
        
        return {
            "status": "Project created and pipeline started",
            "project_name": project_name,
            "files_uploaded": len(saved_files),
            "message": "Files are being processed. Check back in a few minutes for Order A/B."
        }
    
    finally:
        # Clean up temp files
        shutil.rmtree(temp_project_dir, ignore_errors=True)

#Regenerate Order A and B for an existing project.
@app.post("/api/projects/{project_name}/regenerate")
async def regenerate_orders(project_name: str, background_tasks: BackgroundTasks):
    if background_tasks:
        background_tasks.add_task(trigger_order_generation, project_name)
    
    return {
        "status": "Order regeneration started",
        "project_name": project_name,
        "message": "Orders are being generated. Please wait 1–3 minutes and check back."
    }

#Download an order document from Azure Blob.
@app.get("/api/orders/download")
async def download_order(blob: str):

    from azure.storage.blob import BlobServiceClient
    from fastapi import Response
    
    try:
        blob_svc  = BlobServiceClient.from_connection_string(AZURE_CONN_STR)
        container = blob_svc.get_container_client(BLOB_DESIGN_DOCS_CONTAINER)
        
        # Download blob
        download_stream = container.download_blob(blob)
        blob_data = download_stream.readall()
        
        # Return the actual file, not JSON
        filename = blob.split('/')[-1]
        return Response(
            content=blob_data,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    
    except Exception as e:
        print(f" Error: {str(e)}\n")
        raise HTTPException(
            status_code=404, 
            detail=f"Blob not found or error: {str(e)}"
        )

#Simple test endpoint to verify backend is working
@app.get("/api/test-hello")
def test_hello():

    print("\n\n===== TEST ENDPOINT CALLED =====")
    return {"status": "Backend is working!", "message": "If you see this, the backend is responsive"}


@app.post("/api/chat")
async def chat(req: ChatRequest, background_tasks: BackgroundTasks):
    msg          = req.message.strip()
    msg_lower    = msg.lower()
    project_name = req.project_name

    if not msg:
        raise HTTPException(400, "Message cannot be empty.")

    # Resolve project name — from request body or parsed from message text
    if not project_name:
        project_name = extract_project_from_message(req.message)
        if not project_name:
            return {
                "reply": (
                    "Please specify the project name in your message.\n"
                    "Examples:\n"
                    "  • \"Energinet_VSR — what is the rated voltage?\"\n"
                    "  • \"Order A for TenneT_650MVA\""
                ),
                "action": "ask_project"
            }

    # Detect order type and transformer filter
    order_type = None
    if "order a" in msg_lower:
        order_type = "A"
    elif "order b" in msg_lower:
        order_type = "B"

    transformer_filter = None
    if "onshore" in msg_lower and "offshore" not in msg_lower:
        transformer_filter = "onshore"
    elif "offshore" in msg_lower and "onshore" not in msg_lower:
        transformer_filter = "offshore"

    print(f"[CHAT] project='{project_name}' | order={order_type} | filter={transformer_filter} | msg='{msg}'")

    # ── Order request ─────────────────────────────────────────────────────────
    if order_type:
        result = find_order_in_blob(order_type, project_name, transformer_filter)

        if result["found"]:
            from urllib.parse import quote
            encoded_blob = quote(result['blob_name'], safe='')
            return {
                "reply":        f"Order {order_type} for '{project_name}' is ready.",
                "action":       "download",
                "download_url": f"/api/orders/download?blob={encoded_blob}",
                "filename":     result["filename"]
            }

        # If not generated yet → trigger generation in background and inform user
        if result.get("reason") == "not_generated":
            print(f"[CHAT] Order {order_type} not found — triggering on-demand generation")
            background_tasks.add_task(trigger_order_generation, project_name)
            return {
                "reply": (
                    f"Order {order_type} for '{project_name}' is being generated now.\n"
                    f"This usually takes 1–3 minutes. Please ask again shortly."
                ),
                "action": "generating"
            }

        # No project at all, or ambiguous match
        return {"reply": result["message"], "action": "answer"}

    # ── General question → Azure AI Search + OpenAI ─────────────────────────────────
    print(f"[DEBUG] About to call answer_general_question...")
    result = answer_general_question(req.message, project_name)
    print(f"[DEBUG] answer_general_question returned: {result[:100]}")
    return {"reply": result, "action": "answer"}


# DIAGNOSTIC ENDPOINTS (for troubleshooting)
@app.get("/api/test-blob")
async def test_blob_connection():
    """Test Azure Blob connectivity and list available blobs."""
    try:
        from azure.storage.blob import BlobServiceClient
        
        blob_svc = BlobServiceClient.from_connection_string(AZURE_CONN_STR)
        container = blob_svc.get_container_client(BLOB_DESIGN_DOCS_CONTAINER)
        
        # Get container properties
        props = container.get_container_properties()
        
        # List first 10 blobs
        blobs = list(container.list_blobs())[:10]
        blob_names = [b.name for b in blobs]
        
        return {
            "status": " Connected to Azure Blob Storage",
            "container": BLOB_DESIGN_DOCS_CONTAINER,
            "total_blobs_in_container": len(list(container.list_blobs())),
            "sample_blobs": blob_names,
            "message": "Connection successful. Blobs are reachable."
        }
    except Exception as e:
        return {
            "status": " Failed to connect",
            "error": str(e),
            "container": BLOB_DESIGN_DOCS_CONTAINER,
        }

#Diagnostic endpoint to check backend configuration.
@app.get("/api/diagnose")
async def diagnose():
  
    import os
    
    return {
        "status": "Backend Configuration Check",
        "API_KEY_SET": bool(os.getenv("API_KEY")),
        "API_KEY_VALUE": "***" if os.getenv("API_KEY") else "NOT SET",
        "AZURE_STORAGE_SET": bool(os.getenv("AZURE_STORAGE_CONNECTION_STRING")),
        "AZURE_SEARCH_SET": bool(os.getenv("AZURE_SEARCH_ENDPOINT")),
        "OPENAI_SET": bool(os.getenv("OPENAI_KEY")),
        "BLOB_INPUT_CONTAINER": BLOB_INPUT_CONTAINER,
        "BLOB_OUTPUT_CONTAINER": BLOB_OUTPUT_CONTAINER,
        "BLOB_DESIGN_DOCS_CONTAINER": BLOB_DESIGN_DOCS_CONTAINER,
        "AZURE_SEARCH_INDEX": AZURE_SEARCH_INDEX,
        "CHAT_MODEL": CHAT_MODEL,
        "TEMP_DIR": str(TEMP_DIR),
        "TEMP_DIR_EXISTS": TEMP_DIR.exists(),
        "CORS_ENABLED": True,
        "CORS_ALLOWED_ORIGINS": [
            "http://localhost:8000",
            "http://127.0.0.1:8000",
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:8080",
            "http://127.0.0.1:8080",
        ],
        "EXPOSE_HEADERS": ["Content-Disposition", "Content-Type", "Content-Length"],
        "note": "Check these settings if downloads are not working"
    }

#
@app.get("/api/projects/{project_name}")
async def get_project(project_name: str):
    """Get project info including available orders — always returns 200."""
    safe_name = sanitize_name(project_name)
    
    try:
        from azure.storage.blob import BlobServiceClient
        blob_svc = BlobServiceClient.from_connection_string(AZURE_CONN_STR)
        container = blob_svc.get_container_client(BLOB_DESIGN_DOCS_CONTAINER)
        
        prefix = f"{safe_name}/"
        blobs = list(container.list_blobs(name_starts_with=prefix))
        
        orders = {"order_a": None, "order_b": None}
        for blob in blobs:
            
            blob_lower = blob.name.lower()
            
            if "order_a" in blob_lower or "order a" in blob_lower:
                orders["order_a"] = blob.name
            elif "order_b" in blob_lower or "order b" in blob_lower:
                orders["order_b"] = blob.name
        
        has_orders = any(orders.values())
        
        return {
            "name": project_name,
            "safe_name": safe_name,
            "orders": orders,
            "status": "ready" if has_orders else "processing",
            "orders_ready": has_orders,
            "available_blobs": [b.name for b in blobs],
            "exists": True,
            "last_updated": max((b.creation_time.isoformat() for b in blobs), default=None)
        }
    
    except Exception as e:
        print(f"Error getting project {project_name}: {e}")
        # Still return 200 — don't let frontend crash
        return {
            "name": project_name,
            "safe_name": safe_name,
            "orders": {"order_a": None, "order_b": None},
            "status": "processing",  # assume it's still starting
            "orders_ready": False,
            "available_blobs": [],
            "exists": False,
            "error": str(e) if str(e) else "Unknown error"
        }
# RUN- entry point
if __name__ == "__main__":
    import uvicorn
    print("\n" + "="*60)
    
    print("  Transformer Spec RAG  —  Local Dev Mode")
    print("  http://localhost:8000")
    print(f"  API Key: {'ON' if API_KEY else '⚠️  OFF  (set API_KEY in .env)'}")
    print("="*60 + "\n")
    uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=True)
