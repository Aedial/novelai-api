# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import datetime
import inspect
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import List

from sphinx.application import Sphinx
from sphinx.ext.autodoc import Options

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "NovelAI API"
copyright = f"{datetime.datetime.now().year}, Aedial"  # noqa (built-in), pylint: disable=W0622
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

autodoc_class_signature = "separated"
autodoc_member_order = "bysource"
autodoc_typehints_format = "fully-qualified"
autodoc_preserve_defaults = True
autodoc_inherit_docstrings = False

extlinks = {"issue": ("https://github.com/Aedial/novelai-api/issues/%s", "[issue %s]")}

myst_all_links_external = True
myst_relative_links_base = "https://github.com/Aedial/novelai-api/tree/main/"

suppress_warnings = ["myst.header", "git.too_shallow"]

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


# -- Hooks -------------------------------------------------------------------


def format_docstring(_app: Sphinx, what: str, name: str, obj: ModuleType, _options: Options, lines: List[str]):
    kwargs = {
        "obj_type": what,
        "obj_name": name,
    }

    try:
        path = Path(inspect.getfile(obj))

        kwargs.update(abspath=str(path.resolve()), filename=path.name, filestem=path.stem)
    except TypeError:
        pass

    for i, line in enumerate(lines):
        if "{" in line and "}" in line:
            lines[i] = line.format(**kwargs)


def setup(app):
    app.connect("autodoc-process-docstring", format_docstring)
