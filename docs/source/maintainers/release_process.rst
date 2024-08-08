.. _Releases: https://github.com/rackspace/runway/releases

###############
Release Process
###############

Steps that should be taken when preparing for and executing a release.

.. contents::
  :depth: 4


***********
Preparation
***********

#. Merge all PRs that should be included in the release.
#. Ensure that all checks have completed and passed on the *master* branch.


*********
Execution
*********

#. Navigate to the Releases_ section of the repository on GitHub.
   There should be a *Draft* already started that was automatically generated from PRs that were merged since the last release.
#. Enter the *Edit* screen of the *Draft*.

#. The *Title* and *Tag* fields should already be filled in with the correct values (e.g. ``v<major>.<minor>.<patch>``).
   Ensure these values match what is expected.
   The *Tag* should also be targeting the *master* branch.
#. Edit the description of the release as needed but, there should be little to no changes required if all PRs were properly labeled.
#. Mark the release as a *pre-release* if applicable (alpha, beta, release candidate, etc).
#. Publish the release.


At this point, GitHub Actions will begin building the deployment packages & automatically publishing them to npm, PyPi, and AWS S3.
The **Publish Release** workflow can be monitored for progress.
It can take around 20 minutes for the process to complete.
At which time, the logs and package repositories should be checked to verify that the release was published successfully.
