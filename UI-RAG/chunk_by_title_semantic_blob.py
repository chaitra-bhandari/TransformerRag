"""
By-Title Semantic Chunker for Azure

Features:
  Removes document noise (headers, footers, doc numbers)
  Keeps all meaningful data intact
  Correct page numbers
  Clean metadata: source_document, project_name, page
  Works with Azure Blob Storage

Usage:
  from chunk_by_title_semantic_blob import DocumentChunker
  chunker = DocumentChunker()
  chunks = chunker.process_all_projects()
  chunker.save_chunks()
"""

import json
import re
import os
import tempfile
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
from azure.storage.blob import BlobServiceClient

#Azure Config
AZURE_CONN_STR      = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
DI_OUTPUT_CONTAINER = os.getenv("BLOB_OUTPUT_CONTAINER",  "output-of-di")
CHUNK_CONTAINER     = os.getenv("BLOB_CHUNK_CONTAINER",   "chunked-output")

try:
    import tiktoken
    _ENC = tiktoken.get_encoding("cl100k_base")
    def _count_tokens(text: str) -> int:
        return len(_ENC.encode(text))
except ImportError:
    def _count_tokens(text: str) -> int:
        return max(1, len(text) // 4)

#Tracks section hierarchy
class HierarchicalContext:
    def __init__(self):
        self.levels = {}
        
    def update(self, level: int, text: str, page: int) -> None:
        self.levels[level] = (text, page)
        keys_to_remove = [k for k in self.levels if k > level]
        for k in keys_to_remove:
            del self.levels[k]
    
    def get(self, level: int) -> str:
        if level in self.levels:
            return self.levels[level][0]
        return ""


_NUMBERED_HEADING = re.compile(r"^(\d+(?:\.\d+){0,3})[\s.]\s*\S")
_HEADING_ROLES = {"title", "sectionHeading", "heading"}
_MAX_HEADING_LEN = 80
_VALUE_PATTERN = re.compile(r"(=|≥|≤|>|<)\s*[\d.,]+\s*(kV|kA|kW|MW|MVA|Hz|°C|K\b|m\b|mm|cm|dB|%|A\b|V\b|Ω|ohm|bar|N\b)", re.IGNORECASE)
_PERCENT_RATED = re.compile(r"\d+[\d.,]*\s*(%|x)\s*(Ur|Un|In|Ir|Uc|Um)\b", re.IGNORECASE)
_PROSE_START = re.compile(r"^(The|A\s|An\s|All|In\s|For\s|If\s|It\s|This|These|Each|When|Where|No\s|Not|Any|Both|Such|Upon|After|Before|During|Note|See\s|Refer|Unless|Should|Shall|Must|May\s|Per\s)\b", re.IGNORECASE)
_ENDS_WITH_PERIOD = re.compile(r"\.\s*$")
_HAS_MID_COMMA = re.compile(r".{10,},.{5,}")
_HAS_WORD = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ]{2,}")
_SYMBOL_ONLY = re.compile(r"^[A-Z][a-z]?\s*(=|≥|≤|>|<|\d)")

#Enhanced noise pattern
_NOISE_PATTERNS = [
    #Page numbers: "1/7", "page 5 of 12"
    re.compile(r"^\d+/\d+\s*$"),
    re.compile(r"page\s*:?\s*\d+\s*(of\s*\d+)?", re.IGNORECASE),
    
    #Document numbers: "22/10231-12", "Doc. no. 21/10231-14"
    re.compile(r"doc\.?\s*(?:no|number)[\s.:]*\d+/\d+", re.IGNORECASE),
    re.compile(r"^\d+/\d+[-/]\d+\s*$"),
    
    #Revision, date, version
    re.compile(r"revision\s*:?\s*[\d.]+", re.IGNORECASE),
    re.compile(r"date\s*:?\s*\d{1,2}[./-]\d{1,2}[./-]\d{2,4}", re.IGNORECASE),
    re.compile(r"version\s*:?\s*[\d.]+", re.IGNORECASE),
    re.compile(r"klassificering", re.IGNORECASE),
    
    #Company/document headers
    re.compile(r"^(ENERGINET|energinet)\s*$"),
    re.compile(r"^(Document\s+title|document\s+summary)\s*$", re.IGNORECASE),
    re.compile(r"^Shunt\s+Reactor", re.IGNORECASE),
    re.compile(r"^Restricted|Til\s+arbejdsbrug", re.IGNORECASE),
    
    #Footers
    re.compile(r"taking power further", re.IGNORECASE),
    re.compile(r"confidential", re.IGNORECASE),
    
    #Lines with just numbers/symbols
    re.compile(r"^\s*\d+\s*$"),
    re.compile(r"^[-_=|]{5,}$"),
]

#Check if text is noise (headers, footers, page numbers, etc).
def _is_noise(text: str) -> bool:
    t = text.strip()
    if not t:
        return True
    
    # Check against all noise patterns
    for pattern in _NOISE_PATTERNS:
        if pattern.search(t):
            return True
    
    return False

def _passes_text_rules(text: str) -> bool:
    t = text.strip()
    if not t or len(t) > _MAX_HEADING_LEN:
        return False
    if _VALUE_PATTERN.search(t) or _PERCENT_RATED.search(t) or _PROSE_START.match(t):
        return False
    if _ENDS_WITH_PERIOD.search(t) or _HAS_MID_COMMA.search(t) or not _HAS_WORD.search(t):
        return False
    if _SYMBOL_ONLY.match(t):
        return False
    return True

def _heading_level_from_number(text: str) -> Optional[int]:
    m = _NUMBERED_HEADING.match(text.strip())
    if not m:
        return None
    return min(m.group(1).count(".") + 1, 4)

def classify_heading(text: str, role: str, spans: List[Dict], page_num: int) -> Optional[int]:
    if not _passes_text_rules(text):
        return None
    num_level = _heading_level_from_number(text)
    if num_level is not None:
        return num_level
    if role in _HEADING_ROLES:
        return {"title": 1, "sectionHeading": 2, "heading": 3}.get(role, 3)
    return None

#By-Title Semantic Chunker for Azure Blob Storage.
class DocumentChunker:
    def __init__(
        self,
        min_tokens: int = 10,
        max_characters: int = 4000,
        new_after_n_chars: int = 3800,
        combine_text_under_n_chars: int = 2000,
    ):
        self.min_tokens = min_tokens
        self.max_characters = max_characters
        self.new_after_n_chars = new_after_n_chars
        self.combine_text_under_n_chars = combine_text_under_n_chars
        self.all_chunks: List[Dict] = []
        
        # Azure setup
        self.blob_client = BlobServiceClient.from_connection_string(AZURE_CONN_STR)
        self.di_container = self.blob_client.get_container_client(DI_OUTPUT_CONTAINER)
        self.chunk_container = self.blob_client.get_container_client(CHUNK_CONTAINER)
        
        # Create container if doesn't exist
        try:
            self.chunk_container.create_container()
        except Exception:
            pass

    #Download all DI JSONs from Azure blob and return file info
    def find_all_di_jsons(self, temp_dir: str) -> List[Dict]:
        results = []
        
        for blob in self.di_container.list_blobs():
            if not blob.name.endswith("_di_result.json"):
                continue
            
            #Extract project and document names
            parts = blob.name.split("/")
            project_name = parts[0]
            doc_name = Path(blob.name).stem.replace("_di_result", "")
            
            #Download to temp
            local_path = Path(temp_dir) / f"{project_name}_{Path(blob.name).name}"
            with open(local_path, "wb") as f:
                self.di_container.get_blob_client(blob.name).download_blob().readinto(f)
            
            results.append({
                "project_name": project_name,
                "doc_name": doc_name,
                "json_path": local_path
            })
        
        results.sort(key=lambda x: (x["project_name"], x["doc_name"]))
        return results

    def _extract_tables(self, tables: List[Dict], page_offset: int) -> Dict[int, List[Dict]]:
        tables_by_page: Dict[int, List[Dict]] = {}

        for table in tables:
            if not table.get("cells"):
                continue

            page = table["bounding_regions"][0]["page_number"] + page_offset
            if page not in tables_by_page:
                tables_by_page[page] = []

            row_dict: Dict[int, Dict[int, str]] = {}
            max_row, max_col = 0, 0

            for cell in table["cells"]:
                r, c = cell.get("row_index", 0), cell.get("column_index", 0)
                content = cell.get("content", "").strip()
                if r not in row_dict:
                    row_dict[r] = {}
                row_dict[r][c] = content
                max_row = max(max_row, r)
                max_col = max(max_col, c)

            rows = []
            for r in range(max_row + 1):
                row = []
                for c in range(max_col + 1):
                    cell_text = row_dict.get(r, {}).get(c, "")
                    row.append(cell_text)
                rows.append(row)

            tables_by_page[page].append({"rows": rows})

        return tables_by_page

    def process_single_json(self, json_path: Path, project_name: str, doc_name: str) -> List[Dict]:
        print(f"\n    Processing: {json_path.name}")

        with open(json_path, "r", encoding="utf-8") as f:
            di_result = json.load(f)

        pages = di_result.get("pages", [])
        paragraphs_temp = [p for p in di_result.get("paragraphs", []) if p.get("bounding_regions")]
        
        page_offset = 0
        if pages and pages[0].get("page_number") == 0:
            page_offset = 1
            print(f"0-based → 1-based")
        elif paragraphs_temp and paragraphs_temp[0]["bounding_regions"][0]["page_number"] == 0:
            page_offset = 1
            print(f"0-based → 1-based")

        tables = di_result.get("tables", [])
        tables_by_page = self._extract_tables(tables, page_offset)

        paragraphs: List[Dict] = []
        for para in di_result.get("paragraphs", []):
            if para.get("content"):
                paragraphs.append(para)

        if not paragraphs:
            return []

        chunks: List[Dict] = []
        section_lines: List[str] = []
        section_chars = 0
        current_heading_text = ""
        last_page = 0
        pending_small_section: Optional[Dict] = None
        emitted_tables: set = set()

        ctx = HierarchicalContext()

        def _make_chunk(content: str, page: int) -> Optional[Dict]:
            tokens = _count_tokens(content)
            if tokens < self.min_tokens:
                return None

            chunk_id = f"{doc_name}_p{page}_t{int(datetime.now().timestamp() * 1000)}"

            return {
                "chunk_id": chunk_id,
                "content": content,
                "metadata": {
                    "source_document": doc_name,
                    "project_name": project_name,
                    "page": page,
                },
            }

        def flush_section(page: int) -> None:
            nonlocal section_lines, section_chars, current_heading_text, pending_small_section

            if not section_lines:
                return

            full_content = ""
            if current_heading_text:
                full_content = f"{current_heading_text}: "
            full_content += "\n".join(section_lines)

            if len(full_content) < self.combine_text_under_n_chars:
                pending_small_section = {
                    "heading": current_heading_text,
                    "content": full_content,
                    "lines": section_lines,
                    "page": page,
                }
            else:
                result = _make_chunk(full_content, page)
                if result is not None:
                    chunks.append(result)

            section_lines = []
            section_chars = 0
            current_heading_text = ""

        def emit_tables_for_page(page_num: int) -> None:
            nonlocal emitted_tables
            
            if page_num not in tables_by_page:
                return

            for idx, table in enumerate(tables_by_page[page_num]):
                table_id = f"{doc_name}_p{page_num}_t{idx}"
                if table_id in emitted_tables:
                    continue
                emitted_tables.add(table_id)
                
                rows = table["rows"]
                table_text = "\n".join(" | ".join(row) for row in rows)
                result = _make_chunk(table_text, page_num)
                if result is not None:
                    chunks.append(result)

        for para in paragraphs:
            if not para.get("bounding_regions"):
                continue

            page = para["bounding_regions"][0]["page_number"] + page_offset
            text = para.get("content", "").strip()
            role = para.get("role", "")
            spans = para.get("spans", [])

            # Filter out noise
            if not text or _is_noise(text):
                continue

            if page != last_page:
                for pg in range(last_page + 1, page + 1):
                    emit_tables_for_page(pg)
                last_page = page

            h_level = classify_heading(text, role, spans, page)

            if h_level is not None:
                flush_section(page)
                
                if pending_small_section is not None:
                    current_heading_text = pending_small_section["heading"]
                    section_lines = pending_small_section["lines"] + [text]
                    section_chars = pending_small_section["page"]
                    pending_small_section = None
                else:
                    ctx.update(h_level, text, page)
                    current_heading_text = text
                    section_lines = []
                    section_chars = 0
                continue

            line_chars = len(text)
            
            if section_chars + line_chars > self.max_characters:
                flush_section(page)
                section_lines = [text]
                section_chars = line_chars
            elif section_chars >= self.new_after_n_chars:
                flush_section(page)
                section_lines = [text]
                section_chars = line_chars
            else:
                section_lines.append(text)
                section_chars += line_chars + 1

        flush_section(last_page)
        
        if pending_small_section is not None:
            result = _make_chunk(pending_small_section["content"], pending_small_section["page"])
            if result is not None:
                chunks.append(result)
        
        for pg in sorted(tables_by_page):
            emit_tables_for_page(pg)

        chunks.sort(key=lambda c: c["metadata"].get("page", 0))
        print(f"    → {len(chunks)} chunks")
        return chunks

    def process_all_projects(self) -> List[Dict]:
        print("=" * 80)
        print("BY-TITLE SEMANTIC CHUNKING")
        print("=" * 80)

        with tempfile.TemporaryDirectory() as temp_dir:
            di_files = self.find_all_di_jsons(temp_dir)
            
            if not di_files:
                print("No DI JSON files found!")
                return []

            all_chunks: List[Dict] = []
            for fi in di_files:
                all_chunks.extend(self.process_single_json(fi["json_path"], fi["project_name"], fi["doc_name"]))

        print(f"\n{'=' * 80}")
        print(f"TOTAL CHUNKS: {len(all_chunks)}")
        self.all_chunks = all_chunks
        return all_chunks

    #Upload chunks to Azure Blob Storage.
    def save_chunks(self, output_blob_name: str = "all_chunks.json") -> None:
        data = json.dumps(self.all_chunks, indent=2, ensure_ascii=False).encode("utf-8")
        size_kb = len(data) / 1024

        self.chunk_container.upload_blob(
            name=output_blob_name, data=data, overwrite=True
        )

        print(f"\nSaved → {CHUNK_CONTAINER}/{output_blob_name} ({size_kb:.1f} KB)")
