# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import datetime
import inspect
import os
import sys
from pathlib import Path
from types import FunctionType
from typing import List, Union

import tomlkit as toml
from sphinx.application import Sphinx
from sphinx.ext.autodoc import Options

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "NovelAI API"
copyright = f"{datetime.datetime.now().year}, Aedial"  # noqa (built-in), pylint: disable=W0622
author = "Aedial"

PYPROJECT_PATH = Path(__file__).parent.parent.parent / "pyproject.toml"
release = str(toml.loads(PYPROJECT_PATH.read_text("utf-8"))["tool"]["poetry"]["version"])

sys.path.insert(0, os.path.abspath("../.."))
sys.path.insert(0, os.path.abspath(".."))
sys.path.insert(0, os.path.abspath("."))


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.extlinks",
    "sphinx.ext.viewcode",
    "myst_parser",
    "sphinx_copybutton",
    "sphinx_last_updated_by_git",
    "hoverxref.extension",
]

add_module_names = False

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
    "attr": "tooltip",  # for Python Sphinx Domain
    "meth": "tooltip",  # for Python Sphinx Domain
}


templates_path = ["_templates"]
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "classic"
# no asset yet
# html_static_path = ['_static']


# -- Hooks -------------------------------------------------------------------


def format_docstring(_app: Sphinx, what: str, name: str, obj, _options: Options, lines: List[str]):
    """
    Inject metadata in docstrings if necessary
    """

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


def hide_test_signature(
    _app: Sphinx,
    what: str,
    name: str,
    _obj: FunctionType,
    _options: Options,
    signature: str,
    return_annotation: Union[str, None],
):
    if what == "function":
        module_name, *_, file_name, _func_name = name.split(".")

        # erase signature for functions from test files
        if module_name == "tests" and file_name.startswith("test_"):
            return "", None

    return signature, return_annotation


def setup(app):
    app.connect("autodoc-process-docstring", format_docstring)
    app.connect("autodoc-process-signature", hide_test_signature)
