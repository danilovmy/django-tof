# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
import django
from django.conf import ENVIRONMENT_VARIABLE
from pathlib import Path

if not os.getenv(ENVIRONMENT_VARIABLE):
    sys.path.insert(0, str(Path(__file__).parent.absolute()))
    sys.path.insert(0, str(Path(__file__).parent.parent.absolute()))
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.absolute()))
    os.environ[ENVIRONMENT_VARIABLE] = "tof.tests.settings"
    django.setup()

# -- Project information -----------------------------------------------------

project = 'django-tof'
copyright = '2024, Maxim Danilov aka danilovmy'
author = 'Maxim Danilov'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.autosummary",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.githubpages",
    "sphinx_rtd_theme"
]
autosectionlabel_prefix_document = True

# Add any paths that contain templates here, relative to this directory.
# templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
# exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.

html_static_path = ['_static']
html_theme = "sphinx_rtd_theme"
# html_theme_path = ["_themes"]

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".

# html_css_files = ['custom.css',]

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
add_module_names = False
htmlhelp_basename = "django-TOF: translations on fly"

# intersphinx documentation
intersphinx_mapping = {"tablib": ("https://tablib.readthedocs.io/en/stable/", None)}
