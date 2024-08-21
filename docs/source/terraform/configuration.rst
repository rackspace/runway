.. _tf-configuration:

#############
Configuration
#############



*******
Options
*******

Options specific to Terraform Modules.

.. data:: args
  :type: dict[str, list[str]] | list[str] | None
  :value: None
  :noindex:

  List of CLI arguments/options to pass to Terraform.
  See :ref:`Specifying Terraform CLI Arguments/Options <tf-args>` for more details.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      args:
        - '-parallelism=25'

  .. versionadded:: 1.8.1

.. data:: terraform_backend_config
  :type: dict[str, str] | None
  :value: {}
  :noindex:

  Mapping to configure Terraform backend.
  See :ref:`Backend <tf-backend>` for more details.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      terraform_backend_config:
        bucket: mybucket
        dynamodb_table: mytable
        region: us-east-1

  .. versionchanged:: 1.11.0
    Added support for any *key: value*.

.. data:: terraform_version
  :type: str | None
  :value: None
  :noindex:

  String containing the Terraform version or a mapping of deploy environment to a Terraform version.
  See :ref:`Version Management <tf-version>` for more details.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      terraform_version: 0.11.13

.. data:: terraform_write_auto_tfvars
  :type: str | None
  :value: False
  :noindex:

  Optionally write parameters to a tfvars file instead of updating variables.
  This can be useful in cases where Runway may not be parsing/passing parameters as expected.

  When ``True``, Runway creates a temporary ``runway-parameters.auto.tfvars.json`` file in the module directory.
  This file contains all of the modules parameters in JSON format.
  This file is then automatically loaded by Terraform as needed.
  If using a remote backend, use of this file to pass variables is required as environment variables are not available from the CLI and ``-var-file`` currently cannot be used.
  Once the module has finished processing, the file is deleted.

  .. rubric:: Example
  .. code-block:: yaml

    options:
      terraform_write_auto_tfvars: true

  .. versionadded:: 1.11.0


*********
Variables
*********

Variables can be defined per-environment using one or both of the following options.

tfvars
======

Standard Terraform `tfvars <https://www.terraform.io/docs/configuration/variables.html#variable-definitions-tfvars-files>`__ files can be used, exactly as one normally would with ``terraform apply -var-file``.
Runway will automatically detect them when named like ``ENV-REGION.tfvars`` or ``ENV.tfvars``.

.. rubric:: Example
.. code-block:: text
  :caption: common-us-east-1.tfvars

  region = "us-east-1"
  image_id = "ami-abc123"


runway.yml
==========

Variable values can also be specified as :attr:`deployment.parameters`/:attr:`module.parameters` values in runway.yml.
It is recommended to use :ref:`Lookups` in the ``parameters`` section to assist in selecting the appropriate values for the deploy environment and/or region being deployed to but, this is not a requirement if the value will remain the same.

.. code-block:: yaml

  deployments:
    - modules:
        - path: sampleapp-01.tf
          parameters:
            region: ${env AWS_REGION}
            image_id: ${var image_id.${env AWS_REGION}}
            my_list:
              - item1
              - item2
            my_map:
              key1: value1
              key2: value1
    - modules:
        - path: sampleapp-02.tf
      parameters:
        region: ${env AWS_REGION}
        image_id: ${var image_id.${env AWS_REGION}}
        my_list:
          - item1
          - item2
        my_map:
          key1: value1
          key2: value1
