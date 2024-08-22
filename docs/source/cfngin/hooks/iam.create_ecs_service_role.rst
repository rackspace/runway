###########################
iam.create_ecs_service_role
###########################

:Hook Path: ``runway.cfngin.hooks.iam.create_ecs_service_role``


Create ecsServiceRole IAM role.

.. seealso::
  `AWS Documentation describing the Role <https://docs.aws.amazon.com/AmazonECS/latest/developerguide/using-service-linked-roles.html>`__



****
Args
****

.. data:: role_name
  :type: str | None
  :value: "ecsServiceRole"
  :noindex:

  Name of the role to create.
