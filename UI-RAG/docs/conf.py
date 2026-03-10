# Configuration file for Sphinx documentation builder.

project = 'Transformer Spec RAG'
copyright = '2024, Your Name'
author = 'Your Name'

release = '1.0.0'
version = '1.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',
    'sphinx_rtd_theme',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']

source_encoding = 'utf-8'
master_doc = 'index'
language = 'en'

# Theme options
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
