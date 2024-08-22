#######
Secrets
#######

Information about the secrets used by this project.



******
GitHub
******

GitHub secrets are set in the settings of the repository for use by GitHub Actions.


Environment Secrets
===================

Secrets specific to the repository, specific to a single environment.

.. envvar:: DEPLOY_AWS_ACCESS_KEY_ID

  AWS Access Key for the IAM user used to deploy infrastructure to accounts.
  This is **not** the user used when running tests but for deploying infrastructure used by tests (including the IAM user running the tests).

.. envvar:: DEPLOY_AWS_SECRET_ACCESS_KEY

  AWS Secret Access Key for the IAM user used to deploy infrastructure to accounts.
  This is **not** the user used when running tests but for deploying infrastructure used by tests (including the IAM user running the tests).


Repository Secrets
===================

Secrets specific to the repository, available to all environments.

.. envvar:: AWS_ACCESS_KEY

  AWS Access Key for the IAM user used to publish artifacts to S3.
  This IAM user exists in the **public** AWS account.

.. envvar:: AWS_SECRET_KEY

  AWS Secret Access Key for the IAM user used to publish artifacts to S3.
  This IAM user exists in the **public** AWS account.

.. envvar:: NPM_API_TOKEN

  API `access token <https://docs.npmjs.com/about-access-tokens>`__ used to publish Runway to NPM.

.. envvar:: PYPI_PASSWORD

  `API token <https://pypi.org/help/#apitoken>`__ used to publish Runway to PyPi.
  This should be scoped to only the Runway project.

.. envvar:: TEST_PYPI_PASSWORD

  Similar to :envvar:`PYPI_PASSWORD` but for :link:`Test PyPI`.

.. envvar:: TEST_RUNNER_AWS_ACCESS_KEY_ID

  AWS Access Key for the IAM user used to run tests.

.. envvar:: TEST_RUNNER_AWS_SECRET_ACCESS_KEY

  AWS Secret Access Key for the IAM user used to run tests.



***********
ReadTheDocs
***********

Secrets are set as `environment variables <https://docs.readthedocs.io/page/environment-variables.html>`__ for ReadTheDocs to use when building documentation.

.. envvar:: SPHINX_GITHUB_CHANGELOG_TOKEN

  Used by `sphinx-github-changelog <https://pypi.org/project/sphinx-github-changelog/>`__ to generate a changelog for GitHub Releases.
  The `GitHub personal access token <https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token>`__ scope only needs to include ``repo.public_repo``.
