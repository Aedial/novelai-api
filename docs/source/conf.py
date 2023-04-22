# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "NovelAI API"
# pylint: disable=W0622
copyright = "2023, Aedial"  # noqa (built-in)
author = "Aedial"
release = "0.11.6"

sys.path.insert(0, os.path.abspath("../.."))
sys.path.insert(0, os.path.abspath(".."))
sys.path.insert(0, os.path.abspath("."))


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.extlinks",
    "sphinx.ext.viewcode",
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_last_updated_by_git",
    "hoverxref.extension",
]

autodoc_member_order = "bysource"

extlinks = {"issue": ("https://github.com/sphinx-doc/sphinx/issues/%s", "[issue %s]")}

suppress_warnings = ["myst.header"]

copybutton_exclude = ".linenos, .gp, .go"

hoverxref_auto_ref = True
hoverxref_domains = ["py"]
hoverxref_role_types = {
    "hoverxref": "modal",
    "ref": "modal",  # for hoverxref_auto_ref config
    "confval": "modal",  # for custom object
    "mod": "modal",  # for Python Sphinx Domain
    "class": "modal",  # for Python Sphinx Domain
}


templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "classic"
# no asset yet
# html_static_path = ['_static']
