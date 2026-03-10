"""
Transformer Document Processor:
- Reads files from:   input-document-center/{project_folder}/
- Writes results to:  output-of-di/{project_folder}/
- Skips project if output already exists in output-of-di

Project folder name comes from the UI:
    standalone → ProjectName_onshore/   or  ProjectName_offshore/
    combined   → ProjectName_onshore_offshore/
"""

import os
import json
import hashlib
import tempfile
from pathlib import Path
from typing import List, Dict, Tuple
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
from azure.storage.blob import BlobServiceClient
from pdf2image import convert_from_path
import PyPDF2
import numpy as np

#Config — from .env 
AZURE_DI_ENDPOINT   = os.getenv("AZURE_DI_ENDPOINT",   "")
AZURE_DI_API_KEY    = os.getenv("AZURE_DI_API_KEY",    "")
AZURE_CONN_STR      = os.getenv("AZURE_STORAGE_CONNECTION_STRING", "")
INPUT_CONTAINER     = os.getenv("BLOB_INPUT_CONTAINER",  "input-document-center")
OUTPUT_CONTAINER    = os.getenv("BLOB_OUTPUT_CONTAINER", "output-of-di")

class TransformerDocumentProcessor:
    """
    Process all files from a project folder in Azure Blob Storage.

    Flow:
        input-document-center/ProjectName_onshore_offshore/file.pdf
                    ↓  download to temp
                    ↓  run Azure DI
                    ↓  upload result JSON
        output-of-di/ProjectName_onshore_offshore/file_di_result.json
    """

    def __init__(self):
        #Azure DI client
        self.di_client = DocumentAnalysisClient(
            endpoint   = AZURE_DI_ENDPOINT,
            credential = AzureKeyCredential(AZURE_DI_API_KEY)
        )

        #Azure Blob client
        self.blob_client      = BlobServiceClient.from_connection_string(AZURE_CONN_STR)
        self.input_container  = self.blob_client.get_container_client(INPUT_CONTAINER)
        self.output_container = self.blob_client.get_container_client(OUTPUT_CONTAINER)

        #Duplicate tracking (within a single run)
        self.duplicate_tracker = {}
        self.processing_log    = []

    # SKIP CHECK  —  has this project already been processed?
    def project_already_processed(self, project_folder: str) -> bool:
        """
        Check if output-of-di already has results for this project folder.
        If any result JSON exists under that folder → skip the whole project.

        Args:
            project_folder: e.g. "Energinet_onshore_offshore"

        Returns:
            True if already processed, False if needs processing
        """
        prefix   = f"{project_folder.rstrip('/')}/"
        existing = list(self.output_container.list_blobs(name_starts_with=prefix))

        if existing:
            print(f"   Project '{project_folder}' already processed "
                  f"({len(existing)} output files found in '{OUTPUT_CONTAINER}'). Skipping.")
            return True

        return False

    #LIST INPUT FILES FROM BLOB
    def list_project_files(self, project_folder: str) -> List[Dict]:
        """
        List all PDF/DOCX/XLSX files in the project folder in input-document-center.

        Args:
            project_folder: e.g. "Energinet_onshore_offshore"

        Returns:
            List of file info dicts
        """
        prefix = f"{project_folder.rstrip('/')}/"
        blobs  = list(self.input_container.list_blobs(name_starts_with=prefix))

        allowed = {".pdf", ".docx", ".xlsx"}
        files   = []

        for blob in blobs:
            ext = Path(blob.name).suffix.lower()
            if ext not in allowed:
                continue

            files.append({
                'project_name':  project_folder,
                'blob_name':     blob.name,               # full path in blob e.g. "Energinet_onshore/spec.pdf"
                'filename':      Path(blob.name).name,    # just "spec.pdf"
                'file_size':     blob.size,
                'ext':           ext
            })

        print(f" Found {len(files)} files in '{INPUT_CONTAINER}/{prefix}'")
        return files

    #Downlosd the files from blob to temp
    def download_to_temp(self, blob_name: str, temp_dir: str) -> str:
        """
        Download a blob file to a local temp folder for processing.

        Returns:
            Local path of downloaded file
        """
        local_path = Path(temp_dir) / Path(blob_name).name
        blob       = self.input_container.get_blob_client(blob_name)

        with open(local_path, "wb") as f:
            stream = blob.download_blob()
            stream.readinto(f)

        return str(local_path)

    #Upload results to output blob
    def upload_result_to_blob(self, local_path: str, project_folder: str, filename: str):
        """
        Upload a DI result JSON to output-of-di/{project_folder}/filename.

        Args:
            local_path:     Local path of the result JSON
            project_folder: e.g. "Energinet_onshore_offshore"
            filename:       e.g. "spec_di_result.json"
        """
        blob_path = f"{project_folder.rstrip('/')}/{filename}"

        with open(local_path, "rb") as f:
            self.output_container.upload_blob(name=blob_path, data=f, overwrite=True)

        print(f"  Uploaded: {OUTPUT_CONTAINER}/{blob_path}")


    # DUPLICATE CHECK (within a run)
    def calculate_hash(self, filepath: str) -> str:
        h = hashlib.md5()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                h.update(chunk)
        return h.hexdigest()

    def is_duplicate(self, local_path: str) -> Tuple[bool, str]:
        file_hash = self.calculate_hash(local_path)
        if file_hash in self.duplicate_tracker:
            return True, self.duplicate_tracker[file_hash]
        self.duplicate_tracker[file_hash] = local_path
        return False, ""

    # IMAGE PAGE DETECTION
    def detect_image_pages(self, pdf_path: str) -> List[int]:
        image_pages = []
        try:
            images = convert_from_path(pdf_path, dpi=72)

            # Open PdfReader ONCE outside the loop — not per page
            try:
                with open(pdf_path, 'rb') as f:
                    reader = PyPDF2.PdfReader(f)
                    pdf_pages = reader.pages
            except Exception:
                pdf_pages = None

            for page_num, img in enumerate(images, 1):
                img_array = np.array(img.convert('L'))
                variance  = np.var(img_array)

                # High variance = image-heavy page (lots of pixel variation from image content)
                # Low variance  = blank or near-blank page
                if variance > 1000:
                    image_pages.append(page_num)

                # Also flag pages with very little extractable text as image pages
                if pdf_pages is not None:
                    try:
                        text = pdf_pages[page_num - 1].extract_text() or ""
                        if len(text.strip()) < 50 and page_num not in image_pages:
                            image_pages.append(page_num)
                    except Exception:
                        pass

        except Exception as e:
            print(f"  Image detection failed: {e}")
        return image_pages

    # DI processing
    def process_with_di(self, local_path: str, file_info: Dict,
                        temp_dir: str) -> Dict:
        """
        Run Azure Document Intelligence on a local file.
        Saves result JSON locally, then uploads to output-of-di blob.

        Returns:
            result dict with success flag and output blob path
        """
        result_data = {
            'success':          False,
            'di_result_path':   None,
            'output_blob_path': None,
            'pages_processed':  0,
            'tables_found':     0,
            'error':            None
        }

        try:
            print(f"Running Azure DI on: {file_info['filename']}")

            with open(local_path, "rb") as f:
                poller    = self.di_client.begin_analyze_document("prebuilt-layout", f)
                di_result = poller.result()

            # Save result JSON to temp folder
            result_filename = f"{Path(file_info['filename']).stem}_di_result.json"
            result_local    = Path(temp_dir) / result_filename

            with open(result_local, 'w') as f:
                json.dump(di_result.to_dict(), f, indent=2)

            # Upload to output-of-di blob
            self.upload_result_to_blob(
                local_path     = str(result_local),
                project_folder = file_info['project_name'],
                filename       = result_filename
            )

            output_blob_path = f"{file_info['project_name'].rstrip('/')}/{result_filename}"

            result_data.update({
                'success':          True,
                'di_result_path':   str(result_local),
                'output_blob_path': output_blob_path,
                'pages_processed':  len(di_result.pages),
                'tables_found':     len(di_result.tables)
            })

            print(f"DI complete — pages: {len(di_result.pages)}, "
                  f"tables: {len(di_result.tables)}")

        except Exception as e:
            result_data['error'] = str(e)
            print(f"       DI failed: {e}")

        return result_data

    # PROCESS SINGLE FILE
    def process_single_file(self, file_info: Dict, temp_dir: str) -> Dict:
        """
        Full pipeline for one file:
            Download from blob → duplicate check → DI → upload result
        """
        print(f"\n {file_info['project_name']}/{file_info['filename']}")

        summary = {
            'file_info':   file_info,
            'timestamp':   datetime.now().isoformat(),
            'duplicate':   False,
            'image_pages': [],
            'di_result':   None,
            'status':      'pending'
        }

        # Download file to temp
        local_path = self.download_to_temp(file_info['blob_name'], temp_dir)
        print(f"Downloaded to temp")

        # Duplicate check
        is_dup, original = self.is_duplicate(local_path)
        if is_dup:
            print(f"Duplicate of: {Path(original).name} — skipping")
            summary['duplicate'] = True
            summary['status']    = 'skipped_duplicate'
            return summary

        # Image page detection (PDF only)
        if file_info['ext'] == '.pdf':
            print(f"Detecting image pages...")
            image_pages          = self.detect_image_pages(local_path)
            summary['image_pages'] = image_pages
            if image_pages:
                print(f"Image-heavy pages: {image_pages}")

        # Run DI
        di_result = self.process_with_di(local_path, file_info, temp_dir)
        summary['di_result'] = di_result
        summary['status']    = 'success' if di_result['success'] else 'failed'

        return summary

        #Main entry to the code
    def process_project(self, project_folder: str):
        """
        Process all files for one project folder from Azure Blob.

        Args:
            project_folder: Folder name in input-document-center blob,
                            e.g. "Energinet_onshore_offshore"
                            This comes directly from what the UI created.
        """
        print("=" * 70)
        print(f"PROCESSING PROJECT: {project_folder}")
        print(f"Input:  {INPUT_CONTAINER}/{project_folder}/")
        print(f"Output: {OUTPUT_CONTAINER}/{project_folder}/")
        print("=" * 70)

        #Step 1: Skip if already processed
        if self.project_already_processed(project_folder):
            return

        #Step 2: List files in input blob
        files = self.list_project_files(project_folder)
        if not files:
            print(f"No processable files found in '{project_folder}'")
            return

        #Step 3: Process each file in a temp directory
        results    = []
        start_time = datetime.now()

        with tempfile.TemporaryDirectory() as temp_dir:
            print(f"\n Using temp dir: {temp_dir}")

            for idx, file_info in enumerate(files, 1):
                print(f"\n[{idx}/{len(files)}]")
                result = self.process_single_file(file_info, temp_dir)
                results.append(result)
                self.processing_log.append(result)

        #Step 4: Report 
        self._report(results, project_folder, start_time)

    def _report(self, results: List[Dict], project_folder: str, start_time: datetime):
        duration   = (datetime.now() - start_time).total_seconds()
        total      = len(results)
        successful = sum(1 for r in results if r['status'] == 'success')
        duplicates = sum(1 for r in results if r['duplicate'])
        failed     = sum(1 for r in results if r['status'] == 'failed')

        print("\n" + "=" * 70)
        print(f" DONE: {project_folder}")
        print(f"Total files:   {total}")
        print(f"Processed:     {successful}")
        print(f"Duplicates:    {duplicates}")
        print(f"Failed:        {failed}")
        print(f"Time:          {duration:.1f}s")
        print(f"\n   Results in:  {OUTPUT_CONTAINER}/{project_folder}/")
        print("=" * 70)