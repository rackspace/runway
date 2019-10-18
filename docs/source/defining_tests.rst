.. _defining-tests:
.. highlight:: yaml

==============
Defining Tests
==============

Overview
========

:ref:`Tests<runway-test>` can be defined in the
:ref:`runway config file<runway-config>` to test your
:ref:`modules<runway-module>` in any way you desire before deploying. They are
run by using the ``runway test`` :ref:`command<command-test>`.
:ref:`Tests<runway-test>` are run in the order they are defined.

.. rubric:: Example:

::

    tests:
      - name: example-test
        type: script
        args:
          commands:
            - echo "Success!"

Test Failures
-------------

The default behavior if one of the :ref:`tests<runway-test>` fails is to
terminate execution. The subsequent commands will not be run and a non-zero
exit code returned. This behavior can modified to continue testing and not
result in a non-zero exit code on a per-test basis by adding ``required: false``
to the :ref:`test definition<runway-test>`.

.. rubric:: Example:

::

    tests:
      - name: hello-world
        type: script
        required: false
        args:
          commands:
            - echo "Hello World!"  && exit 1


.. _built-in-test-types:

Built-in Test Types
===================

cfn-lint
--------

Source: https://github.com/aws-cloudformation/cfn-python-lint

  *Validate CloudFormation yaml/json templates against the CloudFormation spec*
  *and additional checks. Includes checking valid values for resource properties*
  *and best practices*.

In order to use this :ref:`test<runway-test>`, there must be a ``.cfnlintrc``
file in the same directory as the :ref:`Runway config file<runway-config>`.

.. rubric:: Example:

::

    tests:
      - name: cfn-lint-example
        type: cfn-lint


script
------

Executes a list of provided commands. Each command is run in its own
subprocess.

Commands are passed into the test using the ``commands`` argument.

.. rubric:: Example:

::

    tests:
      - name: hello-world
        type: script
        args:
          commands:
            - echo "Hello World!"


yamllint
--------

Source: https://github.com/adrienverge/yamllint

  *A linter for YAML files. yamllint does not only check for syntax*
  *validity, but for weirdnesses like key repetition and cosmetic*
  *problems such as lines length, trailing spaces, indentation, etc*.

A ``.yamllint`` file can be placed at in the same directory as the
:ref:`Runway config file<runway-config>` to customize the linter or, the Runway
provided template will be used.

.. rubric:: Example:

::

    tests:
      - name: yamllint-example
        type: yamllint
