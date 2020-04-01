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

       $ curl -L https://oni.ca/r4y/latest/osx -o r4y
       $ chmod +x r4y

   .. rubric:: Ubuntu

   .. code-block:: shell

       $ curl -L https://oni.ca/r4y/latest/linux -o r4y
       $ chmod +x r4y

   .. rubric:: Windows

   .. code-block:: shell

       > iwr -Uri oni.ca/r4y/latest/windows -OutFile r4y.exe

#. Use Runway to :ref:`generate a sample<command-gen-sample>` `CloudFormation`_
   :ref:`module<r4y-module>`, edit the values in the environment file, and
   create a :ref:`Runway config file<r4y-config>` to use the
   :ref:`module<r4y-module>`.

   .. rubric:: macOS/Linux

   .. code-block:: shell

       $ r4y gen-sample cfn
       $ sed -i -e "s/CUSTOMERNAMEHERE/mydemo/g; s/ENVIRONMENTNAMEHERE/dev/g; s/stacker-/stacker-$(uuidgen|tr "[:upper:]" "[:lower:]")-/g" sampleapp.cfn/dev-us-east-1.env
       $ cat <<EOF >> r4y.yml
       ---
       # Full syntax at https://github.com/onicagroup/r4y
       deployments:
         - modules:
             - sampleapp.cfn
           regions:
             - us-east-1
       EOF

   .. rubric:: Windows

   .. code-block:: shell

       $ r4y gen-sample cfn
       $ (Get-Content sampleapp.cfn\dev-us-east-1.env).replace('CUSTOMERNAMEHERE', 'mydemo') | Set-Content sampleapp.cfn\dev-us-east-1.env
       $ (Get-Content sampleapp.cfn\dev-us-east-1.env).replace('ENVIRONMENTNAMEHERE', 'dev') | Set-Content sampleapp.cfn\dev-us-east-1.env
       $ (Get-Content sampleapp.cfn\dev-us-east-1.env).replace('stacker-', 'stacker-' + [guid]::NewGuid() + '-') | Set-Content sampleapp.cfn\dev-us-east-1.env
       $ $RunwayTemplate = @"
       ---
       # Full syntax at https://github.com/onicagroup/r4y
       deployments:
         - modules:
             - sampleapp.cfn
           regions:
             - us-east-1
       "@
       $RunwayTemplate | Out-File -FilePath r4y.yml -Encoding ASCII

#. :ref:`Deploy<command-deploy>` the stack.

   .. code-block:: shell

       $ r4y deploy


Now our stack is available at ``mydemo-dev-sampleapp``, e.g.:
``aws cloudformation describe-stack-resources --region us-east-1 --stack-name
mydemo-dev-sampleapp``
