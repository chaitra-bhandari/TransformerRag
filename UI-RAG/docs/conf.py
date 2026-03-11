# Configuration file for Sphinx documentation builder
import sys
import os
from pathlib import Path
from datetime import datetime

# ============================================================================
# PATH SETUP - Handle both local and ReadTheDocs environments
# ============================================================================

# Get the absolute path to the project root
docs_dir = Path(__file__).parent.absolute()
project_root = docs_dir.parent.absolute()

print(f"\n{'='*70}")
print(f"SPHINX CONFIGURATION")
print(f"{'='*70}")
print(f"Docs directory: {docs_dir}")
print(f"Project root: {project_root}")

# Add to Python path
sys.path.insert(0, str(project_root))
print(f"Added to sys.path: {project_root}")

# ============================================================================
# VERIFY PYTHON FILES EXIST
# ============================================================================

python_files = [
    'app.py',
    'rag_query.py',
    'doc_extraction_using_di.py',
    'chunk_by_title_semantic_blob.py',
    'doc_filling_blob.py'
]

print(f"\nChecking Python files:")
for py_file in python_files:
    filepath = project_root / py_file
    exists = filepath.exists()
    status = "✓" if exists else "✗"
    print(f"  {status} {py_file}")

print(f"{'='*70}\n")

# ============================================================================
# PROJECT INFORMATION
# ============================================================================

project = 'Transformer Spec RAG'
author = 'Your Team'
copyright = f'{datetime.now().year}, Your Team'
release = '1.0.0'
version = '1.0'

# ============================================================================
# SPHINX EXTENSIONS
# ============================================================================

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinx.ext.todo',
    'sphinx_rtd_theme',
]

# ============================================================================
# NAPOLEON SETTINGS (For Google/NumPy docstrings)
# ============================================================================

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = True
napoleon_use_rtype = True

# ============================================================================
# THEME SETTINGS
# ============================================================================

html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': '',
    'style_nav_header_background': '#2980B9',
}

# ============================================================================
# AUTODOC SETTINGS - THIS IS CRITICAL FOR SHOWING CODE
# ============================================================================

autodoc_member_order = 'bysource'
autodoc_typehints = 'description'
autodoc_typehints_format = 'short'

# Default options for all modules
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'show-inheritance': True,
    'private-members': False,
}

# ============================================================================
# MOCK IMPORTS - CRITICAL FOR ReadTheDocs!
# ============================================================================
# ReadTheDocs doesn't have Azure packages installed
# We need to mock them so autodoc doesn't fail on import

autodoc_mock_imports = [
    # Azure packages
    'azure',
    'azure.storage',
    'azure.storage.blob',
    'azure.ai',
    'azure.ai.formrecognizer',
    'azure.core',
    'azure.core.credentials',
    'azure.identity',
    
    # ML/Vector packages
    'faiss',
    'numpy',
    'sentence_transformers',
    'sklearn',
    'scikit-learn',
    
    # Document processing
    'pdf2image',
    'PyPDF2',
    'Pillow',
    'PIL',
    
    # OpenAI
    'openai',
    
    # Web framework
    'fastapi',
    'uvicorn',
    'pydantic',
    
    # Document handling
    'docx',
    'python-docx',
    
    # Text processing
    'rank_bm25',
    'bm25',
    
    # Other
    'dotenv',
    'requests',
    'concurrent',
    'pickle',
    're',
]

# ============================================================================
# HTML OUTPUT SETTINGS
# ============================================================================

html_static_path = []
html_logo = None
html_favicon = None

# ============================================================================
# EXCLUDE PATTERNS
# ============================================================================

exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '*.egg-info']

# ============================================================================
# SOURCE & MASTER SETTINGS
# ============================================================================

source_suffix = '.rst'
master_doc = 'index'

# ============================================================================
# LANGUAGE & STYLE
# ============================================================================

language = 'en'
pygments_style = 'sphinx'

# ============================================================================
# HTML OPTIONS
# ============================================================================

html_use_smartypants = True
html_last_updated_fmt = '%b %d, %Y'
html_show_sourcelink = True
html_show_sphinx = True

# ============================================================================
# INTERSPHINX MAPPING
# ============================================================================

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}

