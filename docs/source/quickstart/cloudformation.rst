CloudFormation Quickstart
=========================

For production use, or persistent daily use on a development workstation,
consider the full Runway installation found `here <installation.html>`_. To
quickly evaluate Runway without installing anything a number of resources are
available:

- A `CloudFormation template
  <https://github.com/onicagroup/runway/blob/master/quickstarts/runway/runway-quickstart.yml>`_:
  This is probably the easiest and quickest way to go from "zero to Runway"
  as it allows for using an IAM Role eliminate the need to configure API keys.
  The template will deploy your preference of Linux or Windows Runway host.
  Windows Runway host includes vsCode, which some users may find easier for
  manipulating Runway config files.
- A `Dockerfile
  <https://github.com/onicagroup/runway/blob/master/quickstarts/runway/Dockerfile>`_:
  Docker users can build their own Docker image to run a local Runway
  container, or modify the Dockerfile to build a Runway image to suit specific
  needs. Requires an AWS Access/Secret keypair to use Runway.
- A prebuilt Docker image: Docker users can run the following to spin up a
  local Docker Runway container. Requires an AWS Access/Secret keypair to use
  Runway.

``$ docker run -it --rm onica/runway-quickstart``


Walkthrough - Deploy a CloudFormation Stack
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Mac/Linux**
::

    mkdir my-app
    cd my-app
    git init
    git checkout -b ENV-dev
    runway gen-sample cfn
    sed -i -e "s/CUSTOMERNAMEHERE/mydemo/g; s/ENVIRONMENTNAMEHERE/dev/g; s/stacker-/stacker-$(uuidgen|tr "[:upper:]" "[:lower:]")-/g" sampleapp.cfn/dev-us-east-1.env
    cat <<EOF >> runway.yml
    ---
    # Full syntax at https://github.com/onicagroup/runway
    deployments:
      - modules:
          - sampleapp.cfn
        regions:
          - us-east-1
    EOF
    runway takeoff

**Windows**
::

    mkdir my-app
    cd my-app
    git init
    git checkout -b ENV-dev
    runway gen-sample cfn
    (Get-Content sampleapp.cfn\dev-us-east-1.env).replace('CUSTOMERNAMEHERE', 'mydemo') | Set-Content sampleapp.cfn\dev-us-east-1.env
    (Get-Content sampleapp.cfn\dev-us-east-1.env).replace('ENVIRONMENTNAMEHERE', 'dev') | Set-Content sampleapp.cfn\dev-us-east-1.env
    (Get-Content sampleapp.cfn\dev-us-east-1.env).replace('stacker-', 'stacker-' + [guid]::NewGuid() + '-') | Set-Content sampleapp.cfn\dev-us-east-1.env
    $RunwayTemplate = @"
    ---
    # Full syntax at https://github.com/onicagroup/runway
    deployments:
      - modules:
          - sampleapp.cfn
        regions:
          - us-east-1
    "@
    $RunwayTemplate | Out-File -FilePath runway.yml -Encoding ASCII
    runway takeoff

| Now our stack is available at ``mydemo-dev-sampleapp``, e.g.:
| ``aws cloudformation describe-stack-resources --region us-east-1 --stack-name mydemo-dev-sampleapp``
