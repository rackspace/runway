===================
Maintenance Branchs
===================

A maintenance branch is a branch created to publish patches for releases that are no longer being actively developed (e.g. past major releases).
For Runway, the naming format of these branches is ``release/v<major>``.

-------------------------------------------------------------------------------


*****************************
Creating A Maintenance Branch
*****************************

A new maintenance branch should be created prior to beginning work on a new major release.
It is best to create the branch prior to the final planned release (minor or patch) of the outgoing major version.
This enables `release-drafter <https://github.com/release-drafter/release-drafter>`__ to create drafts for future releases.

.. important::
  When releasing the final release of the outgoing major version, create the tag on the maintenance branch.

#. Clone the repo locally.
#. Ensure that the default branch (e.g. ``master``) is up to date.
#. Create the new maintenance branch locally.
#. Push the maintenance branch to GitHub.


Enable Documentation For A Maintenance Branch
=============================================

To be completed after the creation of a new maintenance branch.

#. Navigate to the `ReadTheDocs project page <https://app.readthedocs.org/projects/runway/>`__
#. Click **Add version**.
#. Input the name of the maintenance branch, activate it, and click **Update version**.


-------------------------------------------------------------------------------


*****************************
Patching A Maintenance Branch
*****************************

#. Clone the repo locally.
#. Checkout the maintenance branch and ensure it is up to date.
#. Create a new branch for the patch, make the required changes, commit the changes, and push to GitHub.
#. Open a new PR ensuring the **change the base branch** to the desired maintenance branch.
#. Merge the PR once all requirements are met.
#. Refer to the :ref:`maintainers/release_process:Maintenance Branch` release process.


-------------------------------------------------------------------------------


******************************
Maintenance Branch End Of Life
******************************

TBD
