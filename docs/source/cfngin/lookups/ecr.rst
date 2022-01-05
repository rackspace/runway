###
ecr
###

Retrieve a value from AWS Elastic Container Registry (ECR).

This Lookup only supports very specific queries.

.. versionadded:: 1.18.0



*****************
Supported Queries
*****************


login-password
==============

Get a password to login to ECR registry.

The returned value can be passed to the login command of the container client of your preference, such as the CFNgin :ref:`docker.login hook`.
After you have authenticated to an Amazon ECR registry with this Lookup, you can use the client to push and pull images from that registry as long as your IAM principal has access to do so until the token expires.
The authorization token is valid for **12 hours**.

Arguments
---------

This Lookup does not support any arguments.

Example
-------

.. code-block:: yaml

  pre_deploy:
    - path: runway.cfngin.hooks.docker.login
      args:
        password: ${ecr login-password}
        ...
