"""Sphinx config file.

https://www.sphinx-doc.org/en/master/usage/configuration.html

"""

# pylint: skip-file
import os
from pathlib import Path

from dunamai import Style, Version

DOCS_DIR = Path(__file__).parent.parent.resolve()
ROOT_DIR = DOCS_DIR.parent
SRC_DIR = DOCS_DIR / "source"


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
project = "Runway"
copyright = "2021, Onica Group"
author = "Onica Group"
release = Version.from_git().serialize(metadata=False, style=Style.SemVer)
version = ".".join(release.split(".")[:2])  # short X.Y version


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration
add_function_parentheses = True
add_module_names = True
default_role = None
exclude_patterns = []
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_github_changelog",
    "sphinx_tabs.tabs",
    "sphinxcontrib.apidoc",
    "sphinxcontrib.programoutput",
]
highlight_language = "default"
intersphinx_mapping = {
    "docker": (
        "https://docker-py.readthedocs.io/en/stable/",
        None,
    ),  # link to docker docs
    "python": ("https://docs.python.org/3", None),  # link to python docs
}
language = None
master_doc = "index"
needs_extensions = {}
needs_sphinx = "3.5"
nitpicky = False  # TODO enable nitpicky
primary_domain = "py"
pygments_style = "material"  # syntax highlighting style
# Appended to the end of each rendered file
rst_epilog = """
.. |Blueprint| replace::
  :class:`~runway.cfngin.blueprints.base.Blueprint`

.. |Dict| replace::
  :class:`~typing.Dict`

.. |Protocol| replace::
  :class:`~typing.Protocol`

.. |Stack| replace::
  :class:`~runway.cfngin.stack.Stack`

.. |cfngin_bucket| replace::
  :attr:`~cfngin.config.cfngin_bucket`

.. |class_path| replace::
  :attr:`~cfngin.stack.class_path`

.. |namespace| replace::
  :attr:`~cfngin.config.namespace`

.. |stack| replace::
  :class:`~cfngin.stack`

.. |template_path| replace::
  :attr:`~cfngin.stack.template_path`

"""
rst_prolog = ""

source_suffix = {".rst": "restructuredtext"}
templates_path = ["_templates"]  # template dir relative to this dir


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
html_codeblock_linenos_style = "inline"
html_css_files = ["css/custom.css"]  # files relative to html_static_path
html_favicon = None
html_logo = None
html_theme = "sphinx_rtd_theme"  # theme to use for HTML and HTML Help pages
html_theme_options = {
    "navigation_depth": -1,  # unlimited depth
}
html_short_title = f"{project} v{release}"
html_title = f"{project} v{release}"
html_show_copyright = True
html_show_sphinx = True
html_static_path = ["_static"]  # dir with static files relative to this dir


# -- Options for HTMLHelp output ---------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-help-output
htmlhelp_basename = "runwaydoc"


# -- Options for LaTeX output ------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-latex-output
latex_documents = [
    (master_doc, "runway.tex", "runway Documentation", "Onica Group", "manual"),
]
latex_elements = {}


# -- Options for manual page output ------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-manual-page-output
man_pages = [(master_doc, "runway", "runway Documentation", [author], 1)]


# -- Options for Texinfo output ----------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-texinfo-output
texinfo_documents = [
    (
        master_doc,
        "runway",
        "runway Documentation",
        author,
        "runway",
        "One line description of project.",
        "Miscellaneous",
    ),
]


# -- Options for Epub output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-epub-output
epub_exclude_files = ["search.html"]
epub_title = project


# -- Options for sphinx-apidoc -----------------------------------------------
# https://www.sphinx-doc.org/en/master/man/sphinx-apidoc.html#environment
os.environ["SPHINX_APIDOC_OPTIONS"] = "members"

# -- Options for sphinx-github-changelog -------------------------------------
# GitHub PAT with "repo.public_repo" access provided by @ITProKyle
changelog_github_token = os.getenv("SPHINX_GITHUB_CHANGELOG_TOKEN", "")

# -- Options of sphinx.ext.autodoc -------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#configuration
autoclass_content = "class"
autodoc_class_signature = "separated"
autodoc_default_options = {
    "inherited-members": "dict",  # show all inherited members
    "member-order": "bysource",
    "members": True,
    "show-inheritance": True,
}
autodoc_type_aliases = {
    "CfnginContext": "runway.context.CfnginContext",
    "DirectoryPath": "Path",
    "FilePath": "Path",
    "RunwayConfig": "runway.config.RunwayConfig",
    "RunwayContext": "runway.context.RunwayContext",
}
autodoc_typehints = "signature"

# -- Options for napoleon  ---------------------------------------------------
# https://www.sphinx-doc.org/en/3.x/usage/extensions/napoleon.html#configuration
napoleon_attr_annotations = True
napoleon_google_docstring = True
napoleon_include_init_with_doc = False
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_type_aliases = autodoc_type_aliases
napoleon_use_admonition_for_examples = False
napoleon_use_admonition_for_notes = False
napoleon_use_admonition_for_references = False
napoleon_use_ivar = False
napoleon_use_param = False
napoleon_use_rtype = True

# -- Options for sphinxcontrib.apidoc  ---------------------------------------
# https://github.com/sphinx-contrib/apidoc
apidoc_excluded_paths = [
    "cfngin/hooks/staticsite/auth_at_edge/templates",
    "templates",
]
apidoc_extra_args = [f"--templatedir={SRC_DIR / '_templates/apidocs'}"]
apidoc_module_dir = "../../runway"
apidoc_module_first = True
apidoc_output_dir = "apidocs"
apidoc_separate_modules = True
apidoc_toc_file = "index"
