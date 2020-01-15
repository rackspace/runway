.. _CloudFormation: https://aws.amazon.com/cloudformation/

.. _qs-cfn:

CloudFormation Quickstart
=========================

#. Prepare the project directory. See :ref:`Repo Structure<repo-structure>`
   for more details.

   .. code-block:: shell

       mkdir my-app
       cd my-app
       git init
       git checkout -b ENV-dev

#. Download/install Runway. Here we are showing the :ref:`curl<install-curl>`
   option. To see other available install methods, see
   :ref:`Installation<install>`.

   .. rubric:: macOS

   .. code-block:: shell

       $ curl -L https://oni.ca/runway/latest/osx -o runway
       $ chmod +x runway

   .. rubric:: Ubuntu

   .. code-block:: shell

       $ curl -L https://oni.ca/runway/latest/linux -o runway
       $ chmod +x runway

   .. rubric:: Windows

   .. code-block:: shell

       > iwr -Uri oni.ca/runway/latest/windows -OutFile runway.exe

#. Use Runway to :ref:`generate a sample<command-gen-sample>` `CloudFormation`_
   :ref:`module<runway-module>`, edit the values in the environment file, and
   create a :ref:`Runway config file<runway-config>` to use the
   :ref:`module<runway-module>`.

   .. rubric:: macOS/Linux

   .. code-block:: shell

       $ runway gen-sample cfn
       $ sed -i -e "s/CUSTOMERNAMEHERE/mydemo/g; s/ENVIRONMENTNAMEHERE/dev/g; s/stacker-/stacker-$(uuidgen|tr "[:upper:]" "[:lower:]")-/g" sampleapp.cfn/dev-us-east-1.env
       $ cat <<EOF >> runway.yml
       ---
       # Full syntax at https://github.com/onicagroup/runway
       deployments:
         - modules:
             - sampleapp.cfn
           regions:
             - us-east-1
       EOF

   .. rubric:: Windows

   .. code-block:: shell

       $ runway gen-sample cfn
       $ (Get-Content sampleapp.cfn\dev-us-east-1.env).replace('CUSTOMERNAMEHERE', 'mydemo') | Set-Content sampleapp.cfn\dev-us-east-1.env
       $ (Get-Content sampleapp.cfn\dev-us-east-1.env).replace('ENVIRONMENTNAMEHERE', 'dev') | Set-Content sampleapp.cfn\dev-us-east-1.env
       $ (Get-Content sampleapp.cfn\dev-us-east-1.env).replace('stacker-', 'stacker-' + [guid]::NewGuid() + '-') | Set-Content sampleapp.cfn\dev-us-east-1.env
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

#. :ref:`Deploy<command-deploy>` the stack.

   .. code-block:: shell

       $ runway deploy


Now our stack is available at ``mydemo-dev-sampleapp``, e.g.:
``aws cloudformation describe-stack-resources --region us-east-1 --stack-name
mydemo-dev-sampleapp``
