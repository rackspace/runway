.. _sls-directory-structure:

###################
Directory Structure
###################

Example directory structures for a Serverless module.



**************
Python Example
**************

.. code-block::

  .
  ├── __init__.py
  ├── _gitignore
  ├── config-dev-us-east-1.json
  ├── hello_world
  │   └── __init__.py
  ├── package.json
  ├── poetry.lock
  ├── pyproject.toml
  └── serverless.yml


******************
TypeScript Example
******************

.. code-block::

  .
  ├── .gitignore
  ├── env
  │   └── dev-us-east-1
  ├── jest.config.js
  ├── package.json
  ├── package-lock.json
  ├── serverless.yml
  ├── src
  │   ├── helloWorld.test.ts
  │   └── helloWorld.ts
  ├── tsconfig.json
  ├── tslint.json
  └── webpack.config.js
