Quickstart Guides
=================

CloudFormation
^^^^^^^^^^^^^^
For production use, or persistent daily use on a development workstation, consider the full Runway installation `here <installation.html>`_. 
To quickly evaluate Runway without installing anything, a number of resources are available:

- A `CloudFormation template <https://github.com/onicagroup/runway/blob/master/quickstarts/runway/runway-quickstart.yml>`_. 
  This is probably the easiest way to go from "zero to Runway" as quickly as possible, 
  as it allows for using an IAM Role which eliminates the need to configure API keys. The template will deploy your 
  preference of Linux or Windows Runway host. Windows Runway host includes vsCode, which some users may find easier 
  for manipulating Runway config files.
- A `Dockerfile <https://github.com/onicagroup/runway/blob/master/quickstarts/runway/Dockerfile>`_. Docker users can 
  build their own Docker image to run a local Runway container, or modify the Dockerfile 
  to build a Runway image to suit specific needs. Requires an AWS Access/Secret keypair to use Runway.
- A prebuilt Docker image. Docker users can run the following to spin up a local Docker Runway container. 
  Requires an AWS Access/Secret keypair to use Runway.

``$ docker run -it --rm onica/runway-quickstart``

Walkthrough - Deploy a CloudFormation Stack
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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

| Now our stack is available at mydemo-dev-sampleapp, e.g.:
| ``aws cloudformation describe-stack-resources --region us-east-1 --stack-name mydemo-dev-sampleapp``

Conduit (Serverless & CloudFront)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


Deploying the Conduit Web App
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The `Medium.com-clone "RealWorld" demo app <https://github.com/gothinkster/realworld>`_ named Conduit provides a 
simple demonstration of using Runway to deploy a Serverless Framework backend with an Angular frontend.

| **Prerequisites**
| 1. An AWS account, and configured terminal environment for interacting with it with an admin role.
| 2. The following installed tools:

    - pipenv (e.g. ``pip install --user pipenv``)
    - npm
    - yarn
    - git (Available out of the box on macOS)

| **Setup**
| Execute the following to setup your Conduit repo:

**macOS/Linux**
::

    mkdir conduit
    cd conduit
    git init
    git checkout -b ENV-dev
    curl -O https://codeload.github.com/anishkny/realworld-dynamodb-lambda/zip/v1.0.0
    unzip v1.0.0
    rm v1.0.0
    mv realworld-dynamodb-lambda-1.0.0 backend
    cd backend
    sed -i '/package-lock\.json/d' .gitignore
    echo '.dynamodb' >> .gitignore
    npm install
    cd ..
    curl -O https://codeload.github.com/gothinkster/angular-realworld-example-app/zip/35a66d144d8def340278cd55080d5c745714aca4
    unzip 35a66d144d8def340278cd55080d5c745714aca4
    rm 35a66d144d8def340278cd55080d5c745714aca4
    mv angular-realworld-example-app-35a66d144d8def340278cd55080d5c745714aca4 frontend
    cd frontend
    sed -i 's/^\s*"build":\s.*$/    "build": "if test \\"$(pipenv run runway whichenv)\\" = \\"prod\\" ; then ng build --prod --base-href .\/ \&\& cp CNAME dist\/CNAME; else ng build --base-href .\/ \&\& cp CNAME dist\/CNAME; fi",/' package.json
    npm install
    curl -O https://raw.githubusercontent.com/onicagroup/runway/master/quickstarts/conduit/update_env_endpoint.py
    cd ..
    curl -O https://raw.githubusercontent.com/onicagroup/runway/master/quickstarts/conduit/Pipfile
    curl -O https://raw.githubusercontent.com/onicagroup/runway/master/quickstarts/conduit/runway.yml
    pipenv update

**Windows**
::

    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    mkdir conduit
    cd conduit
    git init
    git checkout -b ENV-dev
    Invoke-WebRequest https://codeload.github.com/anishkny/realworld-dynamodb-lambda/zip/v1.0.0 -OutFile v1.0.0.zip
    Expand-Archive v1.0.0.zip .
    Remove-Item v1.0.0.zip -Force
    Rename-Item realworld-dynamodb-lambda-1.0.0 backend
    cd backend
    (gc .\.gitignore -raw).Replace("package-lock.json`r`n", "") | sc .\.gitignore
    ".dynamodb`r`n" | Out-File .\.gitignore -Append -Encoding UTF8
    $(gc .\package.json) -replace "dynamodb install .*$", "dynamodb install`"" | Out-File .\package.json -Force -Encoding UTF8
    npm install
    cd ..
    Invoke-WebRequest https://codeload.github.com/gothinkster/angular-realworld-example-app/zip/35a66d144d8def340278cd55080d5c745714aca4 -OutFile 35a66d144d8def340278cd55080d5c745714aca4.zip
    Expand-Archive 35a66d144d8def340278cd55080d5c745714aca4.zip .
    Remove-Item 35a66d144d8def340278cd55080d5c745714aca4.zip -Force
    Rename-Item angular-realworld-example-app-35a66d144d8def340278cd55080d5c745714aca4 frontend
    cd frontend
    $(gc .\package.json) -replace "^\s*`"build`":\s.*$", "    `"build`": `"if test \`"`$(pipenv run runway whichenv)\`" = \`"prod\`" ; then ng build --prod --base-href .\/ && cp CNAME dist\/CNAME; else ng build --base-href .\/ && cp CNAME dist\/CNAME; fi`"," | Out-File .\package.json -Force -Encoding UTF8
    npm install
    Invoke-WebRequest https://raw.githubusercontent.com/onicagroup/runway/master/quickstarts/conduit/update_env_endpoint.py -OutFile update_env_endpoint.py
    cd ..
    Invoke-WebRequest https://raw.githubusercontent.com/onicagroup/runway/master/quickstarts/conduit/Pipfile -OutFile Pipfile
    Invoke-WebRequest https://raw.githubusercontent.com/onicagroup/runway/master/quickstarts/conduit/runway.yml -OutFile runway.yml
    pipenv update

| **Deploying**
| Execute ``pipenv run runway deploy``, enter ``all`` (to deploy the backend followed by the frontend). 
| Deployment will take some time (mostly waiting for the CloudFront distribution to stabilize).
|
| The CloudFront domain at which the site can be reached will be displayed near the last lines of output 
| once deployment is complete, e.g.:

``staticsite: sync & CF invalidation of E17B5JWPMTX5Z8 (domain ddy1q4je03d7u.cloudfront.net) complete``

| **Teardown**
| Execute ``pipenv run runway destroy``, enter ``all``.
|
| The backend DynamoDB tables will still be retained after the destroy is complete. They must be deleted separately:

On macOS/Linux:
::

    for i in realworld-dev-articles realworld-dev-comments realworld-dev-users; do aws dynamodb delete-table --region us-east-1 --table-name $i; done

On Windows:
::

    foreach($table in @("realworld-dev-articles", "realworld-dev-comments", "realworld-dev-users"))
    {
      CMD /C "pipenv run aws dynamodb delete-table --region us-east-1 --table-name $table"
    }

| **Next Steps / Additional Notes**
| The `serverless-plugin-export-endpoints plugin <https://github.com/ar90n/serverless-plugin-export-endpoints>`_ is a good alternative 
| to the custom update_env_endpoint.py script deployed above to update the environment file.

| **Permissions**
| The specific IAM permissions required to manage the resources in this demo are as follows

::

    # CloudFormation
    - cloudformation:CreateStack
    - cloudformation:DeleteStack
    - cloudformation:CreateChangeSet
    - cloudformation:DescribeChangeSet
    - cloudformation:DeleteChangeSet
    - cloudformation:DescribeStackResource
    - cloudformation:DescribeStackResources
    - cloudformation:DescribeStacks
    - cloudformation:DescribeStackEvents
    - cloudformation:GetTemplate
    - cloudformation:UpdateStack
    - cloudformation:ExecuteChangeSet
    - cloudformation:ValidateTemplate
    # Serverless
    - apigateway:GET
    - apigateway:DELETE
    - apigateway:POST
    - apigateway:PUT
    - lambda:AddPermission
    - lambda:CreateAlias
    - lambda:CreateFunction
    - lambda:DeleteAlias
    - lambda:DeleteFunction
    - lambda:GetFunction
    - lambda:GetFunctionConfiguration
    - lambda:ListVersionsByFunction
    - lambda:PublishVersion
    - lambda:UpdateAlias
    - lambda:UpdateFunctionCode
    - lambda:UpdateFunctionConfiguration
    - iam:CreateRole
    - iam:DeleteRole
    - iam:DeleteRolePolicy
    - iam:GetRole
    - iam:PassRole
    - iam:PutRolePolicy
    - logs:CreateLogGroup
    - logs:DeleteLogGroup
    - logs:DescribeLogGroups
    - s3:CreateBucket
    - s3:DeleteBucket
    - s3:DeleteBucketPolicy
    - s3:DeleteObject
    - s3:DeleteObjectVersion
    - s3:GetObjectVersion
    - s3:ListBucket
    - s3:ListBucketVersions
    - s3:PutBucketVersioning
    - s3:PutBucketPolicy
    - s3:PutLifecycleConfiguration
    # Frontend
    - cloudfront:CreateCloudFrontOriginAccessIdentity
    - cloudfront:CreateDistribution
    - cloudfront:CreateInvalidation
    - cloudfront:DeleteCloudFrontOriginAccessIdentity
    - cloudfront:DeleteDistribution
    - cloudfront:GetCloudFrontOriginAccessIdentity
    - cloudfront:GetCloudFrontOriginAccessIdentityConfig
    - cloudfront:GetDistribution
    - cloudfront:GetDistributionConfig
    - cloudfront:GetInvalidation
    - cloudfront:ListDistributions
    - cloudfront:TagResource
    - cloudfront:UntagResource
    - cloudfront:UpdateCloudFrontOriginAccessIdentity
    - cloudfront:UpdateDistribution
    - s3:DeleteBucketWebsite
    - s3:GetBucketAcl
    - s3:GetObject
    - s3:PutBucketAcl
    - s3:GetBucketWebsite
    - s3:PutBucketWebsite
    - s3:PutObject
    - ssm:GetParameter
    - ssm:PutParameter
    # Backend
    - dynamodb:CreateTable
    - dynamodb:DeleteTable
    - dynamodb:DescribeTable
    - dynamodb:TagResource
    - dynamodb:UntagResource
    - dynamodb:UpdateTable
