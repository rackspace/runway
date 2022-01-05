########################
cleanup_ssm.delete_param
########################

:Hook Path: ``runway.cfngin.hooks.cleanup_ssm.delete_param``


Delete SSM parameter.
Primarily used when an SSM parameter is created by a hook rather than CloudFormation.


.. versionchanged:: 2.0.0
  Moved from ``runway.hooks`` to ``runway.cfngin.hooks``.



****
Args
****

.. data:: parameter_name
  :type: str
  :noindex:

  Name of an SSM parameter.
