.. _Pyinstaller: https://pypi.org/project/PyInstaller/
.. _fork this repo: https://help.github.com/en/github/getting-started-with-github/fork-a-repo
.. _clone your fork: https://help.github.com/en/github/creating-cloning-and-archiving-repositories/cloning-a-repository

.. _developers:
.. highlight:: shell

Developer Guide
===============

Getting Started
---------------

Before getting started, `fork this repo`_ and `clone your fork`_.

Development Environment
~~~~~~~~~~~~~~~~~~~~~~~

This project uses ``pipenv`` to create Python virtual environment. This must be installed on your system before setting up your dev environment.


With pipenv installed, run ``make sync_all`` to setup your development environment. This will create all the requred virtual environments to work on runway, build docs locally, and run integration tests locally. The virtual environments all have Runway installed as editable meaning as you make changes to the code of your local clone, it will be reflected in all the virtual environments.

Branch Requirements
~~~~~~~~~~~~~~~~~~~

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

PR Requirements
~~~~~~~~~~~~~~~

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


GitHub Actions
--------------

GitHub Actions are used to manage issues, pull requests, and releases.

Branch Name
~~~~~~~~~~~

Runs on PR open/reopen to check that the incoming branch is using one of the correct prefixes for labels to be applied.

### Accepted Prefixes

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

Issue Management
~~~~~~~~~~~~~~~~

Assigns first responders to a newly opened issue and applies initial labels of `status:review_required` and `priority:low` to denote that one of the first responders has not reviewed the issue yet and set initial triage level.

This will also try to identify if the issue is a feature request, bug report, or question based by looking for keywords and apply the appropriate label. The issue templates will result in the corresponding label being applied.

Release Management
~~~~~~~~~~~~~~~~~~

When a commit is pushed to **release** (tag is pushed, PR is merged) a release draft is created (if one does not exist) and PRs since the last tag are added following the included template. Changes are categorized based on PR labels.


Building Pyinstaller Packages Locally
-------------------------------------

We use Pyinstaller_ to build executables that do not require Python to be installed on a system.
These are built by Travis CI for distribution to ensure a consistent environment but they can also be build locally for testing.

Prerequisites
~~~~~~~~~~~~~

These need to be installed globally so they are not included in the Pipfile.

* ``setuptools==45.2.0``
* ``virtualenv==16.7.9``
* ``pipenv==2018.11.26``

Process
~~~~~~~

1. Export ``TRAVIS_OS_NAME`` environment variable for your system (``linux``, ``osx``, or ``windows``).
2. Execute ``make travisbuild_file`` or ``make travisbuild_folder`` from the root of the repo.

The output of these commands can be found in ``../artifacts``


Travis CI
---------

If you would like to simulate a fully build/deploy of runway on your fork,
you can do so by first signing up and `Travis CI <https://travis-ci.org/>`_
and linking it to your GitHub account. After doing so, there are a few
environment variables that can be setup for your environment.

Travis CI Environment Variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

+---------------------------+----------------------------------------------+
| ``AWS_ACCESS_KEY_ID``     | Credentials required to deploy build         |
|                           | artifacts to S3 at the end of the build      |
|                           | stage. See below for permission requirements.|
+---------------------------+----------------------------------------------+
| ``AWS_BUCKET``            | S3 bucket name where build artifacts will be |
|                           | pushed.                                      |
+---------------------------+----------------------------------------------+
| ``AWS_BUCKET_PREFIX``     | Prefix for all build artifacts published to  |
|                           | S3.                                          |
+---------------------------+----------------------------------------------+
| ``AWS_DEFAULT_REGION``    | Region where S3 bucket is located.           |
+---------------------------+----------------------------------------------+
| ``AWS_SECRET_ACCESS_KEY`` | Credentials required to deploy build         |
|                           | artifacts to S3 at the end of the build      |
|                           | stage. See below for permission requirements.|
+---------------------------+----------------------------------------------+
| ``FORKED``                | Used to enable the deploy steps in a forked  |
|                           | repo.                                        |
+---------------------------+----------------------------------------------+
| ``NPM_API_KEY``           | API key from NPM.                            |
+---------------------------+----------------------------------------------+
| ``NPM_EMAIL``             | Your email address tied to the API key.      |
+---------------------------+----------------------------------------------+
| ``NPM_PACKAGE_NAME``      | Name to use when publishing an npm package.  |
+---------------------------+----------------------------------------------+
| ``NPM_PACKAGE_VERSION``   | Override the version number used for npm.    |
+---------------------------+----------------------------------------------+

**Travis CI User Permissions Example**

.. code-block:: json

    {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject",
                    "s3:PutObjectVersionAcl",
                    "s3:PutObjectTagging",
                    "s3:PutObjectAcl",
                    "s3:GetObject"
                ],
                "Resource": "arn:aws:s3:::$BUCKET_NAME/$PREFIX/*"
            },
            {
                "Sid": "RequiredForCliSyncCommand",
                "Effect": "Allow",
                "Action": [
                    "s3:ListBucket"
                ],
                "Resource": [
                    "arn:aws:s3:::$BUCKET_NAME"
                ]
            }
        ]
    }
