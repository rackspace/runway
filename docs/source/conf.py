"""Sphinx config file.

https://www.sphinx-doc.org/en/master/usage/configuration.html

"""  # noqa: INP001

import os
import sys
from datetime import date
from pathlib import Path

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

DOCS_DIR = Path(__file__).parent.parent.resolve()
ROOT_DIR = DOCS_DIR.parent
SRC_DIR = DOCS_DIR / "source"

PYPROJECT_TOML = tomllib.loads((ROOT_DIR / "pyproject.toml").read_text())
"""Read in the contents of ``../../pyproject.toml`` to reuse it's values."""


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information
project = PYPROJECT_TOML["tool"]["poetry"]["name"].title()
copyright = f"{date.today().year}, Onica Group"  # noqa: A001
author = PYPROJECT_TOML["tool"]["poetry"]["authors"][0]
release = PYPROJECT_TOML["tool"]["poetry"]["version"]
version = ".".join(release.split(".")[:2])  # short X.Y version


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration
add_function_parentheses = True
add_module_names = True
default_role = None
exclude_patterns = []
extensions = [
    "notfound.extension",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosectionlabel",
    "sphinx.ext.intersphinx",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_github_changelog",
    "sphinxcontrib.apidoc",
    "sphinxcontrib.external_links",
    "sphinxcontrib.jquery",
    "sphinxcontrib.programoutput",
]
highlight_language = "default"
language = "en"
master_doc = "index"
needs_extensions = {}
needs_sphinx = "7.4"
nitpicky = False  # TODO (kyle): enable nitpicky
primary_domain = "py"
pygments_style = "one-dark"  # syntax highlighting style
pygments_dark_style = "one-dark"  # syntax highlighting style
source_suffix = {".rst": "restructuredtext"}
templates_path = ["_templates"]  # template dir relative to this dir


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output
html_codeblock_linenos_style = "inline"
html_css_files = []  # files relative to html_static_path
html_favicon = None
html_logo = None
html_theme = "furo"  # theme to use for HTML and HTML Help pages
html_theme_options = {
    "dark_css_variables": {
        "font-stack--monospace": "Inconsolata, monospace",
        "color-inline-code-background": "#24242d",
    },
    "light_css_variables": {
        "font-stack--monospace": "Inconsolata, monospace",
    },
}
html_short_title = f"{project} v{release}"
html_title = f"{project} v{release}"
html_show_copyright = False
html_show_sphinx = False
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


# -- Options of sphinx.ext.autosectionlabel ----------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/autosectionlabel.html
autosectionlabel_maxdepth = 2
autosectionlabel_prefix_document = True


# -- Options of sphinx.ext.autodoc -------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/autodoc.html#configuration
autoclass_content = "class"
autodoc_class_signature = "separated"
autodoc_default_options = {
    "inherited-members": "dict",  # show all inherited members
    "member-order": "alphabetical",
    "members": True,
    "show-inheritance": True,
}
autodoc_inherit_docstrings = True
autodoc_member_order = "alphabetical"
autodoc_type_aliases = {
    "CfnginContext": "runway.context.CfnginContext",
    "DirectoryPath": "Path",
    "FilePath": "Path",
    "RunwayConfig": "runway.config.RunwayConfig",
    "RunwayContext": "runway.context.RunwayContext",
}
autodoc_typehints = "signature"
autodoc_typehints_format = "short"


# -- Options of sphinx.ext.intersphinx ------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/intersphinx.html
intersphinx_mapping = {
    "docker": (
        "https://docker-py.readthedocs.io/en/stable/",
        None,
    ),  # link to docker docs
    "packaging": ("https://packaging.pypa.io/en/stable/", None),
    "python": ("https://docs.python.org/3", None),  # link to python docs
}


# -- Options for sphinx.ext.napoleon  ----------------------------------------
# https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html#configuration
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


# -- Options for sphinx_copybutton ---------------------------------
# https://sphinx-copybutton.readthedocs.io/en/latest/index.html
copybutton_prompt_text = r">>> |\.\.\. |\$ |In \[\d*\]: | {2,5}\.\.\.: | {5,8}: "
copybutton_prompt_is_regexp = True
copybutton_remove_prompts = True
copybutton_line_continuation_character = "\\"


# -- Options for sphinx-github-changelog -------------------------------------
# GitHub PAT with "repo.public_repo" access provided by @ITProKyle
changelog_github_token = os.getenv("SPHINX_GITHUB_CHANGELOG_TOKEN", "")


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


# -- Options for sphinxcontrib.external_links   ------------------------------
# https://sphinxcontribexternal-links.readthedocs.io/latest/configuration.html
external_links: dict[str, str] = {
    "CloudFormation": "https://aws.amazon.com/cloudformation",
    "troposphere": "https://github.com/cloudtools/troposphere",
}
external_links_substitutions: dict[str, str] = {
    "Blueprint": ":class:`Blueprint <runway.cfngin.blueprints.base.GenericBlueprint>`",
    "Dict": ":class:`~typing.Dict`",
    "dict": ":class:`~typing.Dict`",
    "Protocol": ":class:`~typing.Protocol`",
    "Stack": ":class:`~cfngin.stack`",
    "cfngin_bucket": ":attr:`~cfngin.config.cfngin_bucket`",
    "class_path": ":attr:`~cfngin.stack.class_path`",
    "namespace": ":attr:`~cfngin.config.namespace`",
    "template_path": ":attr:`~cfngin.stack.template_path`",
}
