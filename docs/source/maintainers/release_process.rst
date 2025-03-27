.. _Releases: https://github.com/rackspace/runway/releases

###############
Release Process
###############

Steps that should be taken when preparing for and executing a release.

**************
Default Branch
**************

Releases from the branch being actively developed (e.g. ``master``).

Preparation
===========

#. Merge all PRs that should be included in the release.
#. Ensure that all checks have completed and passed on the *master* branch.

Execution
=========

#. Navigate to the Releases_ section of the repository on GitHub.
   There should be a *Draft* already started that was automatically generated from PRs that were merged since the last release.
#. Enter the *Edit* screen of the *Draft*.
#. The *Title* and *Tag* fields should already be filled in with the correct values (e.g. ``v<major>.<minor>.<patch>``).
   Ensure these values match what is expected.
   The *Tag* should also be targeting the *master* branch.
#. Edit the description of the release as needed but, there should be little to no changes required if all PRs were properly labeled.
#. Mark the release as a *pre-release* if applicable (alpha, beta, release candidate, etc).
#. Publish the release.


At this point, GitHub Actions will begin building the deployment package & automatically publishing it to PyPI.
The **Publish Release** workflow can be monitored for progress.


-------------------------------------------------------------------------------


******************
Maintenance Branch
******************

Release from a branch created to patch previous major releases (e.g. ``release/v2``) until they reach end of life.

Prepararing A Maintenance Release
=================================

#. Merge all PRs based on and targeting the maintenance branch that should be included in the release.
#. Ensure that all checks have completed and passed on the maintenance branch.

Executing A Maintenance Release
===============================

#. Navigate to the Releases_ section of the repository on GitHub.
   There should be a *Draft* already started that was automatically generated from PRs that were merged since the last release from the maintenance branch.
#. Enter the *Edit* screen of the *Draft*.
#. The *Title* and *Tag* fields should already be filled in with the correct values (e.g. ``v<major>.<minor>.<patch>``).
   Ensure these values match what is expected.
   The *Tag* should also be targeting the *master* branch.
#. Edit the description of the release as needed but, there should be little to no changes required if all PRs were properly labeled.
#. Publish the release.
