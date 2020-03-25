###################
Directory Structure
###################

Example directory structures for a CloudFormation module.


**********
Blueprints
**********

.. important:: Blueprints must be importable by python. (e.g. directory contains ``__init__.py``)


.. code-block::

  .
  ├── Pipfile
  ├── Pipfile.lock
  ├── runway.variables.yml
  ├── runway.yml
  └── sampleapp.cfn
      ├── blueprints
      │   ├── __init__.py
      │   └── my_blueprint.py
      ├── dev-us-east-1.env
      └── cfngin.yml


************************
Cloudformation Templates
************************

.. important::
  CloudFormation templates can't be stored in the root of the module directory.
  They must be in a subdirectory or external to the module.

.. code-block::

  .
  ├── Pipfile
  ├── Pipfile.lock
  ├── runway.variables.yml
  ├── runway.yml
  └── sampleapp.cfn
      ├── templates
      │   ├── template-01.yml
      │   └── template-02.json
      ├── dev-us-east-1.env
      ├── 01-cfngin.yml
      └── 02-cfngin.yml
