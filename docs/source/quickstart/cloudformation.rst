.. _qs-cfn:

#########################
CloudFormation Quickstart
#########################

#. Prepare the project directory. See :ref:`repo_structure:Repo Structure` for more details.

   .. code-block:: sh

    $ mkdir my-app && cd my-app
    $ git init && git checkout -b ENV-dev

#. Download/install Runway.
   To see available install methods, see :ref:`installation:Installation`.

#. Use Runway to :ref:`generate a sample <commands:gen-sample>` CloudFormation :ref:`Module <runway_config:Module>`, edit the values in the environment file, and create a :ref:`runway_config:Runway Config File` to use the :term:`Module`.

   .. tab-set::

    .. tab-item:: POSIX

      .. code-block:: sh

        $ runway gen-sample cfn
        $ sed -i -e "s/CUSTOMERNAMEHERE/mydemo/g; s/ENVIRONMENTNAMEHERE/dev/g; s/cfngin-/cfngin-$(uuidgen|tr "[:upper:]" "[:lower:]")-/g" sampleapp.cfn/dev-us-east-1.env
        $ cat <<EOF >> runway.yml
        ---
        # Full syntax at https://github.com/onicagroup/runway
        deployments:
          - modules:
              - sampleapp.cfn
            regions:
              - us-east-1
        EOF

    .. tab-item:: Windows

      .. code-block:: powershell

        $ runway gen-sample cfn
        $ (Get-Content sampleapp.cfn\dev-us-east-1.env).replace('CUSTOMERNAMEHERE', 'mydemo') | Set-Content sampleapp.cfn\dev-us-east-1.env
        $ (Get-Content sampleapp.cfn\dev-us-east-1.env).replace('ENVIRONMENTNAMEHERE', 'dev') | Set-Content sampleapp.cfn\dev-us-east-1.env
        $ (Get-Content sampleapp.cfn\dev-us-east-1.env).replace('cfngin-', 'cfngin-' + [guid]::NewGuid() + '-') | Set-Content sampleapp.cfn\dev-us-east-1.env
        $ $RunwayTemplate = @"
        ---
        # Full syntax at https://github.com/onicagroup/runway
        deployments:
          - modules:
              - sampleapp.cfn
            regions:
              - us-east-1
        "@
        $RunwayTemplate | Out-File -FilePath runway.yml -Encoding ASCII

#. :ref:`Deploy <commands:deploy>` the stack.

   .. code-block:: sh

    $ runway deploy


Now our stack is available at ``mydemo-dev-sampleapp``, e.g.:

.. code-block:: sh

  $ aws cloudformation describe-stack-resources --region us-east-1 --stack-name mydemo-dev-sampleapp
