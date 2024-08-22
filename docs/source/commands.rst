.. _kubectl: https://kubernetes.io/docs/reference/kubectl/overview/
.. _Serverless Framework: https://serverless.com/
.. _Terraform: https://www.terraform.io

.. _commands:

########
Commands
########

.. command-output:: runway --help
  :ellipsis: 13


******
deploy
******

.. file://./../../runway/_cli/commands/_deploy.py

.. command-output:: runway deploy --help

.. rubric:: Example
.. code-block:: sh

  $ runway deploy
  $ runway deploy --ci --deploy-environment example
  $ runway deploy --tag tag1 --tag tag2

----



*******
destroy
*******

.. file://./../../runway/_cli/commands/_destroy.py

.. command-output:: runway destroy --help

.. rubric:: Example
.. code-block:: sh

  $ runway destroy
  $ runway destroy --ci --deploy-environment example
  $ runway destroy --tag tag1 --tag tag2

----



*********
dismantle
*********

.. file://./../../runway/_cli/commands/_dismantle.py

.. command-output:: runway dismantle --help

.. rubric:: Example
.. code-block:: sh

  $ runway dismantle
  $ runway dismantle --ci --deploy-environment example
  $ runway dismantle --tag tag1 --tag tag2

----



****
docs
****

.. file://./../../runway/_cli/commands/_docs.py

.. command-output:: runway docs --help

.. rubric:: Example
.. code-block:: sh

  $ runway docs

----



*******
envvars
*******

.. file://./../../runway/_cli/commands/_envvars.py

.. command-output:: runway envvars --help

.. rubric:: Example
.. code-block:: sh

  $ runway envvars
  $ eval "$(runway envvars)"
  $ runway envvars --deploy-environment example

----



**********
gen-sample
**********

.. file://./../../runway/_cli/commands/_gen_sample/__init__.py

.. command-output:: runway gen-sample --help

.. rubric:: Example
.. code-block:: sh

  $ runway gen-sample cfngin
  $ runway gen-sample static-react

----



****
init
****

.. file://./../../runway/_cli/commands/_init.py

.. command-output:: runway init --help

.. rubric:: Example
.. code-block:: sh

  $ runway init
  $ runway init --ci --deploy-environment example
  $ runway init --tag tag1 --tag tag2

----



*************
kbenv install
*************

.. file://./../../runway/_cli/commands/_kbenv/_install.py

.. command-output:: runway kbenv install --help

.. rubric:: Example
.. code-block:: sh

  $ runway kbenv install
  $ runway kbenv install v1.14.0

----



**********
kbenv list
**********

.. file://./../../runway/_cli/commands/_kbenv/_list.py

.. command-output:: runway kbenv list --help

.. rubric:: Example
.. code-block:: sh

  $ runway kbenv list

----



*********
kbenv run
*********

.. file://./../../runway/_cli/commands/_kbenv/_install.py

.. command-output:: runway kbenv run --help

.. rubric:: Example
.. code-block:: sh

  $ runway kbenv run version --client
  $ runway kbenv run -- --help

----



***************
kbenv uninstall
***************

.. file://./../../runway/_cli/commands/_kbenv/_uninstall.py

.. command-output:: runway kbenv uninstall --help

.. rubric:: Example
.. code-block:: sh

  $ runway kbenv uninstall v1.21.0
  $ runway kbenv uninstall --all

----



****
new
****

.. file://./../../runway/_cli/commands/_new.py

.. command-output:: runway new --help

.. rubric:: Example
.. code-block:: sh

  $ runway new
  $ runway new --debug

----



****
plan
****

.. file://./../../runway/_cli/commands/_plan.py

.. note:: Currently only supported for :ref:`index:AWS Cloud Development Kit (CDK)`, :ref:`index:CloudFormation & Troposphere`, and :ref:`index:Terraform`.

.. command-output:: runway new --help

.. rubric:: Example
.. code-block:: sh

  $ runway plan
  $ runway plan --ci --deploy-environment example
  $ runway plan --tag tag1 --tag tag2

----



*********
preflight
*********

.. file://./../../runway/_cli/commands/_preflight.py

.. command-output:: runway preflight --help

.. rubric:: Example
.. code-block:: sh

  $ runway preflight

----



**********
run-python
**********

.. file://./../../runway/_cli/commands/_run_python.py

.. command-output:: runway run-python --help

.. rubric:: Example
.. code-block:: sh

  $ runway run-python my_script.py

----



*************
schema cfngin
*************

.. file://./../../runway/_cli/commands/_schema/_cfngin.py

.. command-output:: runway schema cfngin --help

.. rubric:: Example
.. code-block:: sh

  $ runway schema cfngin --output cfngin-schema.json

----



*************
schema runway
*************

.. file://./../../runway/_cli/commands/_schema/_runway.py

.. command-output:: runway schema runway --help

.. rubric:: Example
.. code-block:: sh

  $ runway schema runway --output runway-schema.json

----



*******
takeoff
*******

.. file://./../../runway/_cli/commands/_takeoff.py

.. command-output:: runway takeoff --help

.. rubric:: Example
.. code-block:: sh

  $ runway takeoff
  $ runway takeoff --ci --deploy-environment example
  $ runway takeoff --tag tag1 --tag tag2

----



****
taxi
****

.. file://./../../runway/_cli/commands/_taxi.py

.. command-output:: runway taxi --help

.. rubric:: Example
.. code-block:: sh

  $ runway taxi
  $ runway taxi --ci --deploy-environment example
  $ runway taxi --tag tag1 --tag tag2

----



****
test
****

.. file://./../../runway/_cli/commands/_test.py

.. command-output:: runway test --help

.. rubric:: Example
.. code-block:: sh

  $ runway test

----



*************
tfenv install
*************

.. file://./../../runway/_cli/commands/_tfenv/_install.py

.. command-output:: runway tfenv install --help

.. rubric:: Example
.. code-block:: sh

  $ runway tfenv install 0.12.0

----



**********
tfenv list
**********

.. file://./../../runway/_cli/commands/_tfenv/_list.py

.. command-output:: runway tfenv list --help

.. rubric:: Example
.. code-block:: sh

  $ runway tfenv list

----



*********
tfenv run
*********

.. file://./../../runway/_cli/commands/_tfenv/_run.py

.. command-output:: runway tfenv run --help

.. rubric:: Example
.. code-block:: sh

  $ runway tfenv run --version
  $ runway tfenv run -- --help

----



***************
tfenv uninstall
***************

.. file://./../../runway/_cli/commands/_tfenv/_uninstall.py

.. command-output:: runway tfenv uninstall --help

.. rubric:: Example
.. code-block:: sh

  $ runway tfenv uninstall 1.0.0
  $ runway tfenv uninstall --all

----



********
whichenv
********

.. file://./../../runway/_cli/commands/_whichenv.py

.. command-output:: runway whichenv --help

.. rubric:: Example
.. code-block:: sh

  $ runway whichenv
