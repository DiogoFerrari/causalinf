# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
#Location of Sphinx files
import os
import sys
sys.path.insert(0, os.path.abspath('..'))

project = 'causalinf'
copyright = '2023, Diogo Ferrari'
author = 'Diogo Ferrari'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
   "sphinx.ext.autodoc"
]


templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
# html_theme = 'alabaster'
html_static_path = ['_static']

# html_theme_path = sphinx_bootstrap_theme.get_html_theme_path()
# html_theme = 'sphinx_material'
# pip install pydata-sphinx-theme
# html_theme = 'pydata_sphinx_theme' ## pretty good
# html_theme = 'bootstrap'
# html_theme = 'bootstrap'
html_theme = 'python_docs_theme'


# ----------
def skip(app, what, name, obj, would_skip, options):
    if name == "__init__":
        return False
    return would_skip

def setup(app):
    app.connect("autodoc-skip-member", skip)

