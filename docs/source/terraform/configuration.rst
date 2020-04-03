#############
Configuration
#############


*******
Options
*******

Options specific to Terraform Modules.

**terraform_backend_config (Optional[Dict[str, str]])**
  Mapping to configure Terraform backend. See :ref:`Backend <tf-backend>` for more details.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      terraform_backend_config:
        bucket: mybucket
        dynamodb_table: mytable
        region: us-east-1

**terraform_version (Optional[Dict[str, str]])**
  Mapping of deploy environment to a Terraform version. See :ref:`Versions <tf-version>` for more details.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      terraform_version:
        "*": 0.11.13  # applies to all environments
        # prod: 0.9.0  # can also be specified for a specific environment
