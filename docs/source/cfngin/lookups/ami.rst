###
ami
###

:Query Syntax: ``[<region>@]<argument>:<argument-value> <argument>:<argument-value>,<argument-value>``

The ami_ lookup is meant to search for the most recent AMI created that matches the given filters.

*********
Arguments
*********

Any other arguments specified but not listed below are sent as filters to the AWS API.
For example, ``architecture:x86_64`` would add a filter.

.. data:: region
  :type: str | None
  :noindex:

  AWS region to search (e.g. ``us-east-1``). Defaults to the current region.

.. data:: owners
  :type: List[str] | str | None
  :noindex:

  At least one owner must be specified in the query (e.g. ``amazon``, ``self``, or an AWS account ID).
  Multiple owners can be provided by using a comma to delimitate the list.

.. data:: name_regex
  :type: str
  :noindex:

  Regex pattern for the name of the AMI (e.g. ``my-ubuntu-server-[0-9]+``).

.. data:: executable_users
  :type: str | None
  :noindex:

  ``amazon``, ``self``, or an AWS account ID.



*******
Example
*******

.. code-block:: yaml

  # Grabs the most recently created AMI that is owned by either this account,
  # amazon, or the account id 888888888888 that has a name that matches
  # the regex "server[0-9]+" and has "i386" as its architecture.

  # Note: The region is optional, and defaults to the current CFNgin region
  ImageId: ${ami [<region>@]owners:self,888888888888,amazon name_regex:server[0-9]+ architecture:i386}
