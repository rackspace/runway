.. _defining-tests:

##############
Defining Tests
##############

:ref:`Tests<runway-test>` can be defined in the :ref:`runway config file<runway-config>` to test your modules in any way you desire before deploying.
They are run by using the ``runway test`` :ref:`command<command-test>`.
Tests are run in the order they are defined.

.. rubric:: Example:

.. code-block:: yaml

  tests:
    - name: example-test
      type: script
      args:
        commands:
          - echo "Success!"



*************
Test Failures
*************

The default behavior if a test failed is to continue running the rest of the tests and return a non-zero exit code at the end.
This behavior can be modified to stop testing on failure by setting ``required: true`` in the test definition.
This will terminate execution if a test fails; no further tests will be run.

.. rubric:: Example
.. code-block:: yaml

  tests:
    - name: hello-world
      type: script
      required: true
      args:
        commands:
          - echo "Hello World!"  && exit 1


.. _built-in-test-types:

*******************
Built-in Test Types
*******************

.. _built-in-test-cfn-lint:

cfn-lint
========

:Source Tool: https://github.com/aws-cloudformation/cfn-python-lint
:Description:
  *Validate CloudFormation yaml/json templates against the CloudFormation spec*
  *and additional checks. Includes checking valid values for resource properties*
  *and best practices*.

In order to use this test, there must be a ``.cfnlintrc`` file in the same directory as the :ref:`Runway config file<runway-config>`.

.. rubric:: Example:
.. code-block:: yaml

  tests:
    - name: cfn-lint-example
      type: cfn-lint


.. _built-in-test-script:

script
======

Executes a list of provided commands.
Each command is run in its own subprocess.

Commands are passed into the test using the ``commands`` argument.

.. rubric:: Example:
.. code-block:: yaml

  tests:
    - name: hello-world
      type: script
      args:
        commands:
          - echo "Hello World!"


.. _built-in-test-yamllint:

yamllint
========

:Source Tool: https://github.com/adrienverge/yamllint
:Description:
  *A linter for YAML files. yamllint does not only check for syntax*
  *validity, but for weirdnesses like key repetition and cosmetic*
  *problems such as lines length, trailing spaces, indentation, etc*.

A ``.yamllint`` file can be placed at in the same directory as the
:ref:`Runway config file<runway-config>` to customize the linter or,
the Runway provided template will be used.

.. rubric:: Example:
.. code-block:: yaml

  tests:
    - name: yamllint-example
      type: yamllint
