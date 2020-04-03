###################
Directory Structure
###################

Example directory structures for a CDK module.


**********
C# Example
**********

.. code-block::

  .
  ├── add-project.hook.d.ts
  ├── cdk.json
  ├── package.json
  ├── package-lock.json
  └── src
      ├── HelloCdk
      │   ├── HelloCdk.csproj
      │   ├── HelloConstruct.cs
      │   ├── HelloStack.cs
      │   └── Program.cs
      └── HelloCdk.sln


**************
Python Example
**************

.. code-block::

  .
  ├── Pipfile
  ├── Pipfile.lock
  ├── app.py
  ├── cdk.json
  ├── hello
  │   ├── __init__.py
  │   ├── hello_construct.py
  │   └── hello_stack.py
  ├── package.json
  └── package-lock.json


******************
TypeScript Example
******************

.. code-block::

  .
  ├── bin
  │   └── sample.ts
  ├── cdk.json
  ├── lib
  │   └── sample-stack.ts
  ├── package.json
  ├── package.json
  └── tsconfig.json
