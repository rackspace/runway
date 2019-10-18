.. _repo-structure:

Repo Structure
==============

Projects deployed via Runway can be structured in a few ways; some examples
follow:

Git Branches as Environments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^
This example shows two :ref:`modules<runway-module>` using environment git
branches (these same files would be present in each environment branch, with
changes to any environment promoted through branches)::

    .
    ├── myapp.cfn
    │   ├── dev-us-west-2.env
    │   ├── prod-us-west-2.env
    │   ├── myapp.yaml
    │   └── templates
    │       └── foo.json
    ├── myapp.tf
    │   ├── backend.tfvars
    │   ├── dev-us-east-1.tfvars
    │   ├── prod-us-east-1.tfvars
    │   └── main.tf
    └── runway.yml

Directories as Environments
^^^^^^^^^^^^^^^^^^^^^^^^^^^
The same two :ref:`modules<runway-module>` from the above `Git Branches as
Environments`_ structure can instead be stored in a normal single-branch git
repo. Each directory correlates with an environment (dev and prod in this
example).

Environment changes are done by copying the environments' contents between
each other. E.g., promotion from dev to prod could be as simple as
``diff -u dev/ prod/`` followed by ``rsync -r --delete dev/ prod/``

Enabling that automated promotion is one of the reasons this example below has
prod config files in the dev folder and vice versa. When promotions between
environments are more hand managed, this is not technically required::

    .
    ├── dev
    │   ├── myapp.cfn
    │   │   ├── dev-us-west-2.env
    |   │   ├── prod-us-west-2.env
    │   │   ├── myapp.yaml
    │   │   └── templates
    │   │       └── myapp_cf_template.json
    │   ├── myapp.tf
    │   │   ├── backend.tfvars
    │   │   ├── dev-us-east-1.tfvars
    |   │   ├── prod-us-east-1.tfvars
    │   │   └── main.tf
    │   └── runway.yml
    └── prod
        ├── myapp.cfn
        │   ├── dev-us-west-2.env
        │   ├── prod-us-west-2.env
        │   ├── myapp.yaml
        │   └── templates
        │       └── myapp_cf_template.json
        ├── myapp.tf
        │   ├── backend.tfvars
        │   ├── dev-us-east-1.tfvars
        │   ├── prod-us-east-1.tfvars
        │   └── main.tf
        └── runway.yml

Directories as Environments with a Single Module
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Another sample repo structure, showing environment folders containing a single
CloudFormation :ref:`modules<runway-module>` at their root (using the
``ignore_git_branch`` :ref:`Runway config file
<runway-config>` option and a single declared module of ``./`` to merge the
Environment & Module folders).

See the `Directories as Environments`_ example above for more information on
why this shows prod config files in the dev folder and vice versa::

    .
    ├── dev
    │   ├── dev-us-west-2.env
    │   ├── prod-us-west-2.env
    │   ├── myapp.yaml
    │   ├── runway.yml
    │   └── templates
    │       └── myapp_cf_template.json
    └── prod
        ├── dev-us-west-2.env
        ├── prod-us-west-2.env
        ├── myapp.yaml
        ├── runway.yml
        └── templates
            └── myapp_cf_template.json
