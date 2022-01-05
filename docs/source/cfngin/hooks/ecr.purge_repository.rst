####################
ecr.purge_repository
####################

:Hook Path: ``runway.cfngin.hooks.ecr.purge_repository``


Purge all images from an ECR repository.


.. versionadded:: 1.18.0



****
Args
****

.. data:: repository_name
  :type: str
  :noindex:

  The name of the ECR repository to purge.



*******
Example
*******

.. code-block:: yaml

  pre_destroy:
    - path: runway.cfngin.hooks.ecr.purge_repository
      args:
        repository_name: example-repo
