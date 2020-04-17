#########################
Contribution Requirements
#########################


*******************
Branch Requirements
*******************

Branches must start with one of the following prefixes (e.g. ``<prefix>/<your-branch-name>``).
This is due to how labels are applied to PRs.
If the branch does not meet the requirement, any PRs from it will be blocked from being merged.

**bugfix | fix | hotfix**
  The branch contains a fix for a big.

**feature | feat**
  The branch contains a new feature or enhancement to an existing feature.

**docs | documentation**
  The branch only contains updates to documentation.

**maintain | maint | maintenance**
  The branch does not contain changes to the project itself to is aimed at maintaining the repo, CI/CD, or testing infrastructure. (e.g. README, GitHub action, integration test infrastructure)

**release**
  Reserved for maintainers to prepare for the release of a new version.


**************************
Documentation Requirements
**************************

Docstrings
==========

In general, we loosely follow the `Google Python Style Guide for Comments and Docstrings`.

We use the ``napoleon`` extension for Sphinx to parse docstrings.
Napoleon provides an `Example Google Style Python Docstring`_ that can be referenced.


.. _Example Google Style Python Docstring: https://sphinxcontrib-napoleon.readthedocs.io/en/latest/example_google.html
.. _Google Python Style Guide for Comments and Docstrings: http://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings

reStructuredText Formatting
===========================

In general, we loosely follow the `Python Style Guide for documentation`_.

.. note:: Not all documentation pages follow this yet. If the page you are updating deviates from this format, adapt to the format of the page.

.. _Python Style Guide for documentation: https://devguide.python.org/documenting/#style-guide

Headings
--------

Section headers are created by underlining (and optionally overlining) the section title with a punctuation character, at least as long as the text.

1. ``#`` with overline, for **h1** (generally only one per file, at the top of the file)
2. ``*`` with overline, for **h2**
3. ``=``, for **h3**
4. ``-``, for **h4**
5. ``^``, for **h5**
6. ``"``, for **h6**

**h1** and **h2** should have two blank lines separating them from sections with headings of the same level or higher.

A ''rubric'' directive can be used to create a non-indexed heading.

.. rubric:: Example
.. code-block:: rst

  #########
  Heading 1
  #########


  *********
  Heading 2
  *********

  Heading 3
  =========

  Heading 4
  ---------

  Heading 5
  ^^^^^^^^^

  Heading 6
  """""""""

  .. rubric:: Non-indexed Heading


  *********
  Heading 2
  *********

  Heading 3
  =========


***************
PR Requirements
***************

In order for a PR to be merged it must be passing all checks and be approved by at least one maintainer.
Some of the checks can be run locally using ``make lint`` and ``make test``.

To be considered for approval, the PR must meet the following requirements.

- Title must be a brief explanation of what was done in the PR (think commit message).
- A summary of was done.
- Explain why this change is needed.
- Detail the changes that were made (think CHANGELOG).
- Screenshot if applicable.
- Include tests for any new features or changes to existing features. (unit tests and integration tests depending on the nature of the change)
- Documentation was updated for any new feature or changes to existing features.
