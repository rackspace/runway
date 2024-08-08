.. _Runway blueprints: https://github.com/rackspace/runway/tree/master/runway/blueprints
.. _troposphere: https://github.com/cloudtools/troposphere

.. _Blueprint:
.. _Blueprints:

##########
Blueprints
##########

A |Blueprint| is a python classes that dynamically builds CloudFormation templates.
Where you would specify a raw Cloudformation template in a |stack| using the |template_path| key, you instead specify a |Blueprint| subclass using the |class_path| key.

Traditionally Blueprints are built using troposphere_, but that is not absolutely necessary.

Making your own should be easy, and you can take a lot of examples from `Runway blueprints`_.
In the end, all that is required is that the |Blueprint| is a subclass of :class:`runway.cfngin.blueprints.base.Blueprint` and it has the following method overridden:

.. code-block:: python

  # Updates self.template to create the actual template
  def create_template(self) -> None:
      """Create a template from the blueprint.

      Main method called by CFNgin when rendering a Blueprint into a template
      that is expected to be overridden.

      """


.. contents::
  :depth: 4


*********
Variables
*********

A |Blueprint| can define a :attr:`~runway.cfngin.blueprints.base.Blueprint.VARIABLES` :data:`~typing.ClassVar` that defines the variables it accepts from the :ref:`Config Variables <cfngin-variables>`.

:attr:`~runway.cfngin.blueprints.base.Blueprint.VARIABLES` should be a |Dict| of ``<variable name>: <variable definition>``.
The variable definition should be a :class:`~runway.cfngin.blueprints.type_defs.BlueprintVariableTypeDef`.

.. rubric:: Example
.. code-block:: python

    from __future__ import annotations

    from typing import TYPE_CHECKING, ClassVar, Dict

    from runway.cfngin.blueprints.base import Blueprint

    if TYPE_CHECKING:
        from runway.cfngin.blueprints.type_defs import BlueprintVariableTypeDef


    class ExampleClass(Blueprint):
        """Example Blueprint."""
        VARIABLES: ClassVar[Dict[str, BlueprintVariableTypeDef]] = {
            "ExampleVariable": {
                "default": "",
                "description": "Example variable.",
                "type": str,
            }
        }

.. seealso::
  :class:`runway.cfngin.blueprints.type_defs.BlueprintVariableTypeDef`
    Documentation for the contents of a |Blueprint| variable definition.


**************
Variable Types
**************

Any native python type can be specified as the :attr:`~runway.cfngin.blueprints.type_defs.BlueprintVariableTypeDef.type` for a variable.
You can also use the following custom types:


TroposphereType
===============

The :class:`~runway.cfngin.blueprints.variables.types.TroposphereType` can be used to generate resources for use in the :class:`~runway.cfngin.blueprints.base.Blueprint` directly from user-specified configuration.
Which of the below case applies depends on what ``defined_type`` was chosen, and how it would be normally used in the :ref:`Blueprint <term-blueprint>` (and CloudFormation in general).

Resource Types
--------------

When ``defined_type`` is a `Resource Type`_, the value specified by the user in the configuration file must be a dictionary, but with two possible structures.

When ``many`` is disabled, the top-level dictionary keys correspond to parameters of the ``defined_type`` constructor.
The key-value pairs will be used directly, and one object will be created and stored in the variable.

When ``many`` is enabled, the top-level dictionary *keys* are resource titles, and the corresponding *values* are themselves dictionaries, to be used as parameters for creating each of multiple ``defined_type`` objects.
A list of those objects will be stored in the variable.

.. _Resource Type: https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-template-resource-type-ref.html

Property Types
--------------

When ``defined_type`` is a property type the value specified by the user in the configuration file must be a dictionary or a list of dictionaries.

When ``many`` is disabled, the top-level dictionary keys correspond to parameters of the ``defined_type`` constructor.
The key-value pairs will be used directly, and one object will be created and stored in the variable.

When ``many`` is enabled, a list of dictionaries is expected.
For each element, one corresponding call will be made to the ``defined_type`` constructor, and all the objects produced will be stored (also as a list) in the variable.

Optional variables
------------------

In either case, when ``optional`` is enabled, the variable may have no value assigned, or be explicitly assigned a null value.
When that happens the variable's final value will be ``None``.

Example
-------

Below is an annotated example:

.. code-block:: python

  """Example Blueprint."""
  from __future__ import annotations

  from typing import TYPE_CHECKING, ClassVar, Dict

  from troposphere import s3, sns

  from runway.cfngin.blueprints.base import Blueprint
  from runway.cfngin.blueprints.variables.types import TroposphereType

  if TYPE_CHECKING:
      from runway.cfngin.blueprints.type_defs import BlueprintVariableTypeDef


  class Buckets(Blueprint):
      """S3 Buckets."""

      VARIABLES: ClassVar[Dict[str, BlueprintVariableTypeDef]] = {
          # Specify that Buckets will be a list of s3.Bucket types.
          # This means the config should a dictionary of dictionaries
          # which will be converted into troposphere buckets.
          "Buckets": {
              "type": TroposphereType(s3.Bucket, many=True),
              "description": "S3 Buckets to create.",
          },
          # Specify that only a single bucket can be passed.
          "SingleBucket": {
              "type": TroposphereType(s3.Bucket),
              "description": "A single S3 bucket",
          },
          # Specify that Subscriptions will be a list of sns.Subscription types.
          # Note: sns.Subscription is the property type, not the standalone
          # sns.SubscriptionResource.
          "Subscriptions": {
              "type": TroposphereType(sns.Subscription, many=True),
              "description": "Multiple SNS subscription designations",
          },
          # Specify that only a single subscription can be passed, and that it
          # is made optional.
          "SingleOptionalSubscription": {
              "type": TroposphereType(sns.Subscription, optional=True),
              "description": "A single, optional SNS subscription designation",
          },
      }

      def create_template(self) -> None:
          """Create a template from the blueprint."""
          # The Troposphere s3 buckets have already been created when we
          # access self.variables["Buckets"], we just need to add them as
          # resources to the template.
          for bucket in self.variables["Buckets"]:
              self.template.add_resource(bucket)

          # Add the single bucket to the template. You can use
          # `Ref(single_bucket)` to pass CloudFormation references to the
          # bucket just as you would with any other Troposphere type.
          self.template.add_resource(self.variables["SingleBucket"])

          subscriptions = self.variables["Subscriptions"]
          optional_subscription = self.variables["SingleOptionalSubscription"]
          # Handle it in some special way...
          if optional_subscription is not None:
              subscriptions.append(optional_subscription)

          self.template.add_resource(
              sns.Topic("ExampleTopic", TopicName="Example", Subscriptions=subscriptions)
          )

A sample config for the above:

.. code-block:: yaml

  stacks:
    - name: buckets
      class_path: path.to.above.Buckets
      variables:
        Buckets:
          # resource name (title) that will be added to CloudFormation.
          FirstBucket:
            # name of the s3 bucket
            BucketName: my-first-bucket
          SecondBucket:
            BucketName: my-second-bucket
        SingleBucket:
          # resource name (title) that will be added to CloudFormation.
          MySingleBucket:
            BucketName: my-single-bucket
        Subscriptions:
          - Endpoint: one-lambda
            Protocol: lambda
          - Endpoint: another-lambda
            Protocol: lambda
        # The following could be omitted entirely
        SingleOptionalSubscription:
          Endpoint: a-third-lambda
          Protocol: lambda


CFNType
=======

The :class:`~runway.cfngin.blueprints.variables.types.CFNType` can be used to signal that a variable should be submitted to CloudFormation as a Parameter instead of only available to the |Blueprint| when rendering.
This is useful if you want to leverage AWS-Specific Parameter types (e.g. ``List<AWS::EC2::Image::Id>``) or Systems Manager Parameter Store values (e.g. ``AWS::SSM::Parameter::Value<String>``).

See :mod:`runway.cfngin.blueprints.variables.types` for available subclasses of the :class:`~runway.cfngin.blueprints.variables.types.CFNType`.

.. rubric:: Example
.. code-block:: python

  """Example Blueprint."""
  from __future__ import annotations

  from typing import TYPE_CHECKING, ClassVar, Dict

  from runway.cfngin.blueprints.base import Blueprint
  from runway.cfngin.blueprints.variables.types import (
      CFNString,
      EC2AvailabilityZoneNameList,
  )

  if TYPE_CHECKING:
      from runway.cfngin.blueprints.type_defs import BlueprintVariableTypeDef


  class ExampleBlueprint(Blueprint):
      """Example Blueprint."""

      VARIABLES: ClassVar[Dict[str, BlueprintVariableTypeDef]] = {
          "String": {"type": str, "description": "Simple string variable"},
          "List": {"type": list, "description": "Simple list variable"},
          "CloudFormationString": {
              "type": CFNString,
              "description": "A variable which will create a CloudFormation "
              "Parameter of type String",
          },
          "CloudFormationSpecificType": {
              "type": EC2AvailabilityZoneNameList,
              "description": "A variable which will create a CloudFormation "
              "Parameter of type List<AWS::EC2::AvailabilityZone::Name>",
          },
      }

      def create_template(self) -> None:
          """Create a template from the blueprint."""
          # `self.variables` returns a dictionary of <variable name>: <variable value>.
          # For the subclasses of `CFNType`, the values are
          # instances of `CFNParameter` which have a `ref` helper property
          # which will return a troposphere `Ref` to the parameter name.
          self.add_output("StringOutput", self.variables["String"])

          # self.variables["List"] is a native list
          for index, value in enumerate(self.variables["List"]):
              self.add_output("ListOutput:{}".format(index), value)

          # `CFNParameter` values (which wrap variables with a `type`
          # that is a `CFNType` subclass) can be converted to troposphere
          # `Ref` objects with the `ref` property
          self.add_output(
              "CloudFormationStringOutput", self.variables["CloudFormationString"].ref
          )
          self.add_output(
              "CloudFormationSpecificTypeOutput",
              self.variables["CloudFormationSpecificType"].ref,
          )


******************************************
Utilizing Stack name within your Blueprint
******************************************

Sometimes your |Blueprint| might want to utilize the already existing :attr:`stack.name <cfngin.stack.name>` within your |Blueprint|.
Runway's CFNgin provides access to both the fully qualified stack name matching what’s shown in the CloudFormation console, in addition to the stack's short name you have set in your YAML config.


Referencing Fully Qualified Stack name
======================================

The fully qualified name is a combination of the CFNgin namespace + the short name (what you set as ``name`` in your YAML config file).
If your CFNgin |namespace| is ``CFNginIsCool`` and the stack's short name is ``myAwesomeEC2Instance``, the fully qualified name would be ``CFNginIsCool-myAwesomeEC2Instance``.

To use this in your |Blueprint|, you can get the name from context using ``self.context.get_fqn(self.name)``.


Referencing the Stack short name
================================

The |Stack| short name is the name you specified for the |stack| within your YAML config.
It does not include the |namespace|.
If your CFNgin namespace is ``CFNginIsCool`` and the stack's short name is ``myAwesomeEC2Instance``, the short name would be ``myAwesomeEC2Instance``.

To use this in your |Blueprint|, you can get the name from the :attr:`~runway.cfngin.blueprints.base.Blueprint.name` attribute.

.. rubric:: Example
.. code-block:: python

  """Example Blueprint."""
  from __future__ import annotations

  from typing import TYPE_CHECKING, ClassVar, Dict

  from troposphere import Tags, ec2

  from runway.cfngin.blueprints.base import Blueprint
  from runway.cfngin.blueprints.variables.types import CFNString

  if TYPE_CHECKING:
      from runway.cfngin.blueprints.type_defs import BlueprintVariableTypeDef


  class ExampleBlueprint(Blueprint):
      """Example Blueprint."""

      # VpcId set here to allow for Blueprint to be reused
      VARIABLES: ClassVar[Dict[str, BlueprintVariableTypeDef]] = {
          "VpcId": {
              "type": CFNString,
              "description": "The VPC to create the Security group in",
          }
      }

      def create_template(self) -> None:
          """Create a template from the blueprint."""
          # now adding a SecurityGroup resource named `SecurityGroup` to the CFN template
          self.template.add_resource(
              ec2.SecurityGroup(
                  "SecurityGroup",
                  # Referencing the VpcId set as the variable
                  VpcId=self.variables["VpcId"].ref,
                  # Setting the group description as the fully qualified name
                  GroupDescription=self.context.get_fqn(self.name),
                  # setting the Name tag to be the stack short name
                  Tags=Tags(Name=self.name),
              )
          )



******************
Testing Blueprints
******************

When writing your own |Blueprint| it is useful to write tests for them in order to make sure they behave the way you expect they would, especially if there is any complex logic inside.

To this end, a sub-class of the ``unittest.TestCase`` class has been provided: :class:`runway.cfngin.blueprints.testutil.BlueprintTestCase`.
You use it like the regular TestCase class, but it comes with an addition assertion: ``assertRenderedBlueprint``.
This assertion takes a |Blueprint| object and renders it, then compares it to an expected output, usually in ``tests/fixtures/blueprints``.


Yaml (CFNgin) format tests
==========================

In order to wrap the :class:`~runway.cfngin.blueprints.testutil.BlueprintTestCase` tests in a format similar to CFNgin's stack format, the :class:`~runway.cfngin.blueprints.testutil.YamlDirTestGenerator` class is provided.
When subclassed in a directory, it will search for yaml files in that directory with certain structure and execute a test case for it.

.. rubric:: Example
.. code-block:: yaml

  namespace: test

  stacks:
    - name: test_stack
      class_path: cfngin_blueprints.s3.Buckets
      variables:
        var1: val1

When run from tests, this will create a template fixture file called ``test_stack.json`` containing the output from the ``cfngin_blueprints.s3.Buckets`` template.
