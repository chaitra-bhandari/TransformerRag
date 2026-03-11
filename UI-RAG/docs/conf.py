# Configuration file for Sphinx documentation builder
import sys
import os
from pathlib import Path
from datetime import datetime

# DEBUG: Show what path we're using
print(f"Current file: {__file__}")
print(f"Current dir: {os.getcwd()}")

# Get the absolute path to the project root
# conf.py is in docs/, so we go up one level (..)
project_root = str(Path(__file__).parent.parent.absolute())
print(f"Project root: {project_root}")

# Add to Python path so imports work
sys.path.insert(0, project_root)
print(f"Added to sys.path: {project_root}")
print(f"Python path[0]: {sys.path[0]}")

# Verify app.py exists
app_path = os.path.join(project_root, 'app.py')
print(f"Looking for app.py at: {app_path}")
print(f"app.py exists: {os.path.exists(app_path)}")

# Project information
project = 'Transformer Spec RAG'
author = 'Your Team'
copyright = f'{datetime.now().year}, Your Team'
release = '1.0.0'
version = '1.0'

# Sphinx extensions
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.intersphinx',
    'sphinx.ext.viewcode',
    'sphinx.ext.todo',
    'sphinx_rtd_theme',
]

# Napoleon settings for docstring parsing
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

# Theme settings
html_theme = 'sphinx_rtd_theme'
html_theme_options = {
    'logo_only': False,
    'display_version': True,
    'prev_next_buttons_location': 'bottom',
    'style_external_links': False,
    'vcs_pageview_mode': '',
    'style_nav_header_background': '#2980B9',
}

# Autodoc settings
autodoc_member_order = 'bysource'
autodoc_typehints = 'description'
autodoc_typehints_format = 'short'

# Autodoc default options - SHOW FULL CODE
autodoc_default_options = {
    'members': True,
    'member-order': 'bysource',
    'special-members': '__init__',
    'undoc-members': True,
    'show-inheritance': True,
    'private-members': False,
}

# Mock imports for packages that might not be installed
autodoc_mock_imports = [
    'azure',
    'azure.storage',
    'azure.storage.blob',
    'azure.ai',
    'azure.ai.formrecognizer',
    'azure.core',
    'azure.core.credentials',
    'faiss',
    'numpy',
    'openai',
    'fastapi',
    'docx',
    'pdf2image',
    'PyPDF2',
    'rank_bm25',
    'sentence_transformers',
]

# HTML output settings
html_static_path = []
html_logo = None
html_favicon = None

# Exclude patterns
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store', '*.egg-info']

# Source suffix
source_suffix = '.rst'

# Master document
master_doc = 'index'

# Language
language = 'en'

# Pygments style
pygments_style = 'sphinx'

# HTML options
html_use_smartypants = True
html_last_updated_fmt = '%b %d, %Y'
html_show_sourcelink = True
html_show_sphinx = True

# Intersphinx mapping
intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
}