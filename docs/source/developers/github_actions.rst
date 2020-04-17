##############
GitHub Actions
##############

GitHub Actions are used to manage issues, pull requests, test, releases, and publishing.


***********
Branch Name
***********

Runs on PR open/reopen to check that the incoming branch is using one of the correct prefixes for labels to be applied.

Accepted Prefixes
=================

- ``bugfix/``
- ``chore/``
- ``docs/``
- ``enhancement/``
- ``feat/``
- ``feature/``
- ``fix/``
- ``hotfix/``
- ``maint/``
- ``maintain/``
- ``maintenance/``
- ``release/``


*****
CI/CD
*****

Based on the execution environment, this workflow will run different steps.

.. rubric:: PR Branch

- Lint & test
- build & upload Pyinstaller_ artifacts
- build & upload python artifacts

.. rubric:: Master Branch

- Lint & test
- build & upload Pyinstaller_ artifacts
- build & upload PyPi_ & npm_ artifacts
- publish a development version to `Test PyPi`_ and npm_

.. rubric:: Tag

- Lint & test
- build & upload Pyinstaller_ artifacts
- build & upload PyPi_ & npm_ artifacts
- publish a development version to `Test PyPi`_
- publish a release to AWS S3, PyPi_, & npm_

.. _npm: https://www.npmjs.com/package/@onica/runway
.. _Pyinstaller: https://pypi.org/project/PyInstaller/
.. _PyPi: https://pypi.org/project/runway/
.. _Test PyPi: https://test.pypi.org/project/runway/

Linting & Tests
===============

Linting and tests are run on Ubuntu and Windows for the following python versions:

- 2.7
- 3.5
- 3.6
- 3.7

All version and OS combinations are run in parallel. If any of them fail, all the other tests will fail immediately.

We are not currently running linting & tests on macOS due to the limited concurrent runner count of macOS runners.
There are also enough similarities between macOS and Ubuntu in regards to the functionality of Runway that it is not deemed to be a necessity at this time.

Secrets
=======

These are the secrets_ used by this workflow that have been added to the repo and how to generate them.
They can be added to any any fork to enable *similar* results but, you will need to change the name of the application for publishing to succeed.

**aws_access_key & aws_secret_key**
  AWS access key ID and secret access key for an IAM user that has the permissions required to publish to AWS S3.

**npm_api_token**
  An npm authentication token.
  For steps on how to create the authentication token, see the `Creating an npm authentication token`_ documentation.

**pypi_password**
  A PyPi API token. It is recommended to scope the token to the project contained in the repo.
  For steps on how to create the API token, see the `Creating a PyPi API token`_ documentation.

**test_pypi_password**
  A Test PyPi API token. It is recommended to scope the token to the project contained in the repo.
  For steps on how to create the API token, see the `Creating a PyPi API token`_ documentation.

.. _Creating a PyPi API token: https://packaging.python.org/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/#saving-credentials-on-github
.. _Creating an npm authentication token: https://docs.npmjs.com/creating-and-viewing-authentication-tokens
.. _secrets: https://help.github.com/en/actions/configuring-and-managing-workflows/creating-and-storing-encrypted-secrets


****************
Issue Management
****************

Assigns first responders to a newly opened issue and applies initial labels of ``status:review_required`` and ``priority:low`` to denote that one of the first responders has not reviewed the issue yet and set initial triage level.

This will also try to identify if the issue is a feature request, bug report, or question based by looking for keywords and apply the appropriate label. The issue templates will result in the corresponding label being applied.


******************
Release Management
******************

When a commit is pushed to **release** (tag is pushed, PR is merged) a release draft is created (if one does not exist) and PRs since the last tag are added following the included template. Changes are categorized based on PR labels.
