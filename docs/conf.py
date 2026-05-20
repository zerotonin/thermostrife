# Configuration file for the Sphinx documentation builder.

import os
import sys

sys.path.insert(0, os.path.abspath(".."))

# -- Project information -----------------------------------------------------
project = "ThermoStrife"
copyright = "2026, Bart R.H. Geurten"
author = "Bart R.H. Geurten"
release = "0.1.0"

# -- General configuration ---------------------------------------------------
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.githubpages",
    "sphinx.ext.intersphinx",
    "myst_parser",
    "sphinx_copybutton",
]

# Napoleon — support Google and NumPy style docstrings
napoleon_google_docstrings = True
napoleon_numpy_docstrings = True
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False

# Autodoc
autodoc_member_order = "bysource"
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
}

# Mock heavy / optional imports so docs build on cheap CI runners
autodoc_mock_imports = [
    "matplotlib", "numpy", "pandas", "scipy", "statsmodels",
    "meteostat", "cdsapi", "xarray", "netCDF4", "requests", "tqdm",
]

# MyST settings (Markdown)
myst_enable_extensions = [
    "colon_fence",
    "deflist",
    "tasklist",
]
source_suffix = {
    ".rst": "restructuredtext",
    ".md": "markdown",
}

# Intersphinx
intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "pandas": ("https://pandas.pydata.org/docs/", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/", None),
}

templates_path = []
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# -- HTML output -------------------------------------------------------------
html_theme = "furo"
html_title = f"ThermoStrife {release}"
html_short_title = "ThermoStrife"
html_static_path = []
html_theme_options = {
    "source_repository": "https://github.com/zerotonin/thermostrife",
    "source_branch": "main",
    "source_directory": "docs/",
    "navigation_with_keys": True,
    "top_of_page_buttons": ["view", "edit"],
}
