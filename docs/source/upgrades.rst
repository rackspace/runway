.. _upgrades:

########
Upgrades
########

.. contents::
  :depth: 4

During a Runway upgrade (especially coming from a :code:`0.x` version) you may required to make changes to your configuration or modules. This page will describe common issues when upgrading and how to resolve them.

*******************************
Updating the Runway Config File
*******************************

You may need to update your Runway config file structure depending on how old of a Runway version you are upgrading from. Some config keys have changed in spelling, may make use of :code:`_` instead of :code:`-`, or have different functionality altogether. For example, compare this old config file:

.. code-block:: yaml

  deployments:
    - modules:
        - module-1.cfn
        - module-2.cfn
        - module-3.cfn
      regions:
        - us-east-1
      account-id:
        prod: 123412341234
      assume-role:
        post_deploy_env_revert: true
        prod: arn:aws:iam::123412341234:role/my-deployment-role
      environments:
        prod-ops:
          namespace: my-account
          environment: prod

To this newer version:

.. code-block:: yaml

  variables:
    account_id:
      prod: 123412341234
    assume_role:
      prod: arn:aws:iam::123412341234:role/my-deployment-role
    parameters:
      prod:
        namespace: my-account
        environment: prod

  deployments:
    - modules:
        - module-1.cfn
        - module-2.cfn
        - module-3.cfn
      regions:
        - us-east-1
      account_id: ${var account_id.${env DEPLOY_ENVIRONMENT}}
      assume_role:
        arn: ${var assume_role.${env DEPLOY_ENVIRONMENT}}
        post_deploy_env_revert: true
      environments:
        prod: true
      parameters: ${var parameters.${env DEPLOY_ENVIRONMENT}}

In the above example, we've taken advantage of Runway's :code:`variables` key and we dynamically reference it based on our :code:`DEPLOY_ENVIRONMENT`. We also updated :code:`account-id` and :code:`assume-role` to :code:`account_id` and :code:`assume_role`.

Runway is very flexible about how you can structure your config, the above is only an example of one way to adjust it. Just keep in mind while upgrading that if you receive errors as soon as you start a :code:`runway` command, it is likely due to a config file error or no longer supported directive.

********************************
Migration from Stacker to CFNgin
********************************

Older versions of Runway used Stacker, which was then forked and included into the Runway project as CFNgin. This causes a few concerns while migrating older deployments.

------------------------------
Update References to Stacker
------------------------------

See :doc:`cfngin/migrating` for info on converting your older Stacker modules into CFNgin compatible versions.

-------------------------------
Migration of Stacker Blueprints
-------------------------------

In some environments, you may see usage of Stacker "Blueprints". These are Python scripts leveraging Troposphere to generate CloudFormation templates programmatically. While these can be incredibly powerful, they also come with a Python experience dependency and are prone to breaking due to AWS or Runway changes. In older deployments if the blueprint contains references to :code:`stacker` it will also need to be updated to use the new :code:`cfngin` library after a Runway upgrade, as described in :doc:`cfngin/migrating`.

In most cases it is easiest to:

1. Navigate to the AWS CloudFormation Console,
2. find the stack that was deployed using the blueprint,
3. copy its CloudFormation template data (optionally converting it to YAML on the way); and,
4. convert the deployment in Runway to use that static template so you can eliminate the blueprint.

This process leaves you with a much more simple to manage static template.

------------------------------------
A Note on Tagging in Stacker Modules
------------------------------------

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
stacker_namespace / cfngin_namespace tag
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If a Stacker/CFNgin deployment doesn't have a :code:`tags` key defined, a default value is used:

Stacker::

    stacker_namespace: ${namespace}

CFNgin::

    cfngin_namespace: ${namespace}

Because of this if you are upgrading a Stacker module without the :code:`tags` key defined, you'll see Runway attempting to adjust the tags on every resource in the module. This is because it is updating the default :code:`stacker_namespace` tag to a :code:`cfngin_namespace` tag. If you'd like to prevent this behavior, you can add a :code:`tags` key as follows::

    tags:
      stacker_namespace: ${namespace}

The above usage will cause CFNgin to keep the old :code:`stacker_namespace` tag with its original value, eliminating the need for changes to tags on resources.

^^^^^^^^^^^^^^^^^^^^
Int to String Errors
^^^^^^^^^^^^^^^^^^^^

When defining a :code:`tags` key directly onto a CFNgin stack definition (not the top level :code:`tags` key in the CFNgin config file), you may see an error regarding using an :code:`int` instead of a :code:`string`. For instance:

.. code-block:: yaml

  # This may return a "must be of type string" error
  my-stack-definition:
    template_path: ./my-templates/my-cloudformation-template.yaml
    tags:
      CostCenter: 1234

This can be resolved by enclosing your numerical value in quotes:

.. code-block:: yaml

  # This may return a "must be of type string" error
  my-stack-definition:
    template_path: ./my-templates/my-cloudformation-template.yaml
    tags:
      CostCenter: "1234"

******************
Updates to Lookups
******************

Some lookup usage may have changed slightly. Here's some examples:

.. code-block:: yaml

  # This generates a deprecation warning in newer Runway versions
  VpcId: ${rxref vpc::VpcId}

  # This is the new usage
  VpcId: ${rxref vpc.VpcId}

.. code-block:: yaml

  # This generates an unknown lookup error
  SlackUrl: ${ssmstore us-east-1@/devops/slack_hook}

  # This is the new usage
  SlackUrl: ${ssm /devops/slack_hook}
