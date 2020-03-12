######
Labels
######

Definitions for each label and how they are/should be used.

Proper application of labels is important for the correct, automated actions to be taken.
For example, PRs need to be labeled for release descriptions to be generated correctly.


***
bug
***

Something isn't working.

.. rubric:: Issue

Automatically applied to bug reports when they are opened.
Can be manually added if the issue is determined to be a bug report after further investigation.

Should only have one of bug_, documentation_, feature_, maintenance_, question_, or release_.

.. rubric:: Pull Request

Should be added manually when the intent is to fix functionality that is not working as expected.

Should only have one of bug_, documentation_, feature_, maintenance_, or release_.


*************
documentation
*************

Changes to documentation.

.. rubric:: Issue

Should be added manually to any requests for improving documentation.

Should only have one of bug_, documentation_, feature_, maintenance_, question_, or release_.

.. rubric:: Pull Request

Should be added manually if the only changes are documentation updates.
This includes the ReadTheDoc source files and any README.

Should only have one of bug_, documentation_, feature_, maintenance_, or release_.


*********
duplicate
*********

This issue or pull request already exists.

.. rubric:: Issue

Should be manually added to any issue where the feature request, bug report, question, etc is already covered by an existing issue, PR, or task.
When applying this label, add the appropriate links to the original item then close.

.. rubric:: Pull Request

Should be manually added if the feature or bug fix is covered in another PR.
Discuss with both parties and determine the best approach to move forward with, closing the other.


*******
feature
*******

Request, pull request, or task for new functionality or a change to existing functionality.

.. rubric:: Issue

Automatically applied to any feature request.
Can manually added if the issue is determined to be feature request after further investigation.

Should only have one of bug_, documentation_, feature_, maintenance_, question_, or release_.

.. rubric:: Pull Request

Should be manually added for any new functionality or changes to existing functionality.

Should only have one of bug_, documentation_, feature_, maintenance_, or release_.


****************
good first issue
****************

Issue or task that would be a good place to start for any new contributors.

.. rubric:: Issue

Should be manually added to any issue that can be completed with limited experience with this project.


***********
help wanted
***********

Extra attention is needed.

.. rubric:: Issue

Should be manually added if further guidance by a maintainer is required or feedback is needed from a wider audience.

.. rubric:: Pull Request

Should be manually added if further guidance by a maintainer is required or feedback is needed from a wider audience.


*******
invalid
*******

This doesn't seem right.

.. rubric:: Issue

Does not pertain to this project or is unintelligible beyond hope.

.. rubric:: Pull Request

Does not pertain to this project, is unintelligible beyond hope, or is not a direction the project should go.


***********
maintenance
***********

General upkeep, does not impact the functionally of the application itself.

.. rubric:: Issue

Should be manually added if it pertains to changing a dependency version, repo script, GitHub Action, etc.

Should only have one of bug_, documentation_, feature_, maintenance_, question_, or release_.

.. rubric:: Pull Request

Should be manually added if it pertains to changing a dependency version, repo script, GitHub Action, etc.

Should only have one of bug_, documentation_, feature_, maintenance_, or release_.


*****************
priority:critical
*****************

Critical issue or pull request.

.. rubric:: Issue

Should be added manually to any catastrophic bug reports for core functionality that is broken or compromised security.

Should only have one of priority:critical_, priority:high_, priority:medium_ or priority:low_.

.. rubric:: Pull Request

Should be added manually to any catastrophic bugs for core functionality that is broken or compromised security.

Should only have one of priority:critical_, priority:high_, priority:medium_ or priority:low_.


*************
priority:high
*************

High priority issue or pull request.

.. rubric:: Issue

Should be added manually if deemed high priority.

Should only have one of priority:critical_, priority:high_, priority:medium_ or priority:low_.

.. rubric:: Pull Request

Should be added manually if deemed high priority.

Should only have one of priority:critical_, priority:high_, priority:medium_ or priority:low_.


************
priority:low
************

Low priority issue or pull request.

.. rubric:: Issue

Automatically added to all new issues when they are opened.

Should only have one of priority:critical_, priority:high_, priority:medium_ or priority:low_.

.. rubric:: Pull Request

Should only have one of priority:critical_, priority:high_, priority:medium_ or priority:low_.


***************
priority:medium
***************

Medium priority issue or pull request.

.. rubric:: Issue

Should be added manually if deemed medium priority.

Should only have one of priority:critical_, priority:high_, priority:medium_ or priority:low_.

.. rubric:: Pull Request

Should be added manually if deemed medium priority.

Should only have one of priority:critical_, priority:high_, priority:medium_ or priority:low_.


********
question
********

Information is needed about how something should be done.

.. rubric:: Issue

Automatically added to issues opened as questions.
Can be manually added if the issue is determined to be just a question after further investigation.

Should only have one of bug_, documentation_, feature_, maintenance_, question_, or release_.

.. rubric:: Pull Request

Should not be used.


*******
release
*******

A release task or pull request.

.. rubric:: Issue

Should be manually added if the issue is being used to track the release process.

Should only have one of bug_, documentation_, feature_, maintenance_, question_, or release_.

.. rubric:: Pull Request

Should be manually added to PR related to a release.
Should only be merged if the ``master`` branch is the target, never the ``release`` branch.
PRs intended to run integration tests with the source set as ``master`` and target of ``release`` are acceptable but should never be merged, only closed.

Should only have one of bug_, documentation_, feature_, maintenance_, or release_.


**************
skip-changelog
**************

Do not include on the release change log.

.. rubric:: Issue

Should not be used.

.. rubric:: Pull Request

Should be manually added if the PR does not change the application or application documentation to keep the release changelog clean of any PRs that do not impact the application.
Primarily only used for changes to GitHub Actions, scripts, or repository management.


****************
status:abandoned
****************

Issue or pull request was abandoned by the author.

.. rubric:: Issue

Should be manually added if a request for more information was made but not provided for >=2 weeks.
After applying this label and a short comment, the issue should be closed.

.. rubric:: Pull Request

Should be manually added if a request for more information or changes was made but not provided for >=2 weeks.
If the PR is not worth assigning someone else to finish, a short comment should be left and the PR closed.


***************
status:accepted
***************

Issue or pull request was accepted by a maintainer.

.. rubric:: Issue

Should be manually added if the issue is something that a maintainer would like to pursue.

If an issue was not created by a maintainer and does not have this label, it should not be worked on as there is a high chance any associated PRs will be denied.

.. rubric:: Pull Request

Should be manually added if a PR was not created by a maintainer, is not associated with an issue, but is something a maintainer would like to pursue.


****************
status:available
****************

Task available for assignment.

.. rubric:: Issue

Should be manually added to an issue after it has been accepted and open for assignment to anyone who would like to contribute. Once assigned to someone, it should be removed.

.. rubric:: Pull Request

Should be manually added to a PR that was abandoned by the author and should be finished. Once assigned to someone, it should be removed.


**************
status:blocked
**************

Issue or pull request is blocked by something.

.. rubric:: Issue

Should be manually added if the issue requires another issue, PR, etc to be complete before it can be started or completed.
Once unblocked, it should be removed.

.. rubric:: Pull Request

Should be manually added if the PR requires another issue, PR, etc to be complete before it can be merged.
Once unblocked, it should be removed.


****************
status:completed
****************

Task is complete.

.. rubric:: Issue

TBD

.. rubric:: Pull Request

TBD


******************
status:in_progress
******************

Task is actively being worked on.

.. rubric:: Issue

Should be manually added if the issue is accepted, assigned, and is actively being worked on.
Should not be used if the issue is status:blocked_ or status:on_hold_.

.. rubric:: Pull Request

Should be manually added if the PR is accepted, assigned, and is actively being worked on.
Should not be used if the PR is status:blocked_ or status:on_hold_.


**************
status:on_hold
**************

Task was recently worked on but is now on hold.

.. rubric:: Issue

Should be manually added if the issue is accepted and assigned but is not actively being worked on and is not blocked.
Should be removed once work has continued.
Primarily used when switching tasks to something of higher priority.

.. rubric:: Pull Request

Should be manually added if the PR is accepted and assigned but is not actively being worked on and is not blocked.
Should be removed once work has continued.
Primarily used when switching tasks to something of higher priority.


**************
status:pending
**************

Task is pending review or something else.

.. rubric:: Issue

TBD

.. rubric:: Pull Request

TBD


********************
status:review_needed
********************

Issue or pull request needs to be reviewed by a maintainer.

.. rubric:: Issue

Automatically applied to issues when they are opened.
Should be manually added when a maintainer needs to re-review.
Should be removed after the issue has been accepted or rejected.

.. rubric:: Pull Request

Should be manually added when a maintainer needs to review or re-review for acceptance.
Should be removed after the issue has been accepted or rejected.


**********************
status:revision_needed
**********************

Issue or pull request needs to be revised by the author.

.. rubric:: Issue

Should be manually added when the issue if it needs to be revised by the author to add more information, examples, etc.
Should be removed once the issue is fixed.

.. rubric:: Pull Request

Should be manually added when the PR needs to be revised by the author to add more information, examples, etc, or it does not meet requirements.
Should be removed once the PR is fixed.


*******
wontfix
*******

This will not be worked on.

.. rubric:: Issue

Should be manually added when the issue has been rejected by a maintainer.

.. rubric:: Pull Request

Should be manually added when the PR has been rejected by a maintainer.
