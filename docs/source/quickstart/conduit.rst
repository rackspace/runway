.. _qs-conduit:

Conduit (Serverless & CloudFront) Quickstart
============================================


Deploying the Conduit Web App
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `Medium.com-clone "RealWorld" demo app <https://github.com/gothinkster/realworld>`_
named Conduit provides a simple demonstration of using Runway to deploy a
Serverless Framework backend with an Angular frontend.


Prerequisites
^^^^^^^^^^^^^

- An AWS account, and configured terminal environment for interacting with it
  with an admin role.
- The following installed tools:

    - npm
    - yarn
    - git (Available out of the box on macOS)


Setup
^^^^^

#. Prepare the project directory. See :ref:`Repo Structure<repo-structure>`
   for more details.

   .. code-block:: shell

       mkdir conduit
       cd conduit
       git init
       git checkout -b ENV-dev

#. Download/install Runway. Here we are showing the :ref:`curl<install-curl>`
   option. To see other available install methods, see
   :ref:`Installation<install>`.

   .. rubric:: macOS

   .. code-block:: shell

       curl -L https://oni.ca/runway/latest/osx -o runway
       chmod +x runway

   .. rubric:: Ubuntu

   .. code-block:: shell

       curl -L https://oni.ca/runway/latest/linux -o runway
       chmod +x runway

   .. rubric:: Windows

   .. code-block:: shell

       iwr -Uri oni.ca/runway/latest/windows -OutFile runway.exe

#. Download the source files.

   .. rubric:: macOS/Linux

   .. code-block:: shell

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
       mkdir scripts
       cd scripts && { curl -O https://raw.githubusercontent.com/onicagroup/runway/master/quickstarts/conduit/build.js ; cd -; }
       sed -i 's/^\s*"build":\s.*$/    "build": "node scripts\/build",/' package.json
       sed -i 's/^\s*"rxjs":\s.*$/    "rxjs": "~6.3.3",/' package.json
       npm install
       curl -O https://raw.githubusercontent.com/onicagroup/runway/master/quickstarts/conduit/update_env_endpoint.py
       cd ..
       curl -O https://raw.githubusercontent.com/onicagroup/runway/master/quickstarts/conduit/runway.yml

   .. rubric:: Windows

   .. code-block:: powershell

       [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
       Invoke-WebRequest https://codeload.github.com/anishkny/realworld-dynamodb-lambda/zip/v1.0.0 -OutFile v1.0.0.zip
       Expand-Archive v1.0.0.zip .
       Remove-Item v1.0.0.zip -Force
       Rename-Item realworld-dynamodb-lambda-1.0.0 backend
       cd backend
       (gc .\.gitignore -raw).Replace("package-lock.json`n", "") | sc .\.gitignore
       ".dynamodb`r`n" | Out-File .\.gitignore -Append -Encoding UTF8
       $(gc .\package.json) -replace "dynamodb install .*$", "dynamodb install`"" | Out-File .\package.json -Force -Encoding UTF8
       npm install
       cd ..
       Invoke-WebRequest https://codeload.github.com/gothinkster/angular-realworld-example-app/zip/35a66d144d8def340278cd55080d5c745714aca4 -OutFile 35a66d144d8def340278cd55080d5c745714aca4.zip
       Expand-Archive 35a66d144d8def340278cd55080d5c745714aca4.zip .
       Remove-Item 35a66d144d8def340278cd55080d5c745714aca4.zip -Force
       Rename-Item angular-realworld-example-app-35a66d144d8def340278cd55080d5c745714aca4 frontend
       cd frontend
       (gc .\package.json -raw).Replace("`"rxjs`": `"^6.2.1`"", "`"rxjs`": `"~6.3.3`"") | sc .\package.json
       mkdir scripts
       Invoke-WebRequest https://raw.githubusercontent.com/onicagroup/runway/master/quickstarts/conduit/build.js -OutFile scripts/build.js
       $(gc .\package.json) -replace "^\s*`"build`":\s.*$", "    `"build`": `"node scripts/build`"," | Out-File .\package.json -Force -Encoding UTF8
       npm install
       Invoke-WebRequest https://raw.githubusercontent.com/onicagroup/runway/master/quickstarts/conduit/update_env_endpoint.py -OutFile update_env_endpoint.py
       cd ..
       Invoke-WebRequest https://raw.githubusercontent.com/onicagroup/runway/master/quickstarts/conduit/Pipfile -OutFile Pipfile
       Invoke-WebRequest https://raw.githubusercontent.com/onicagroup/runway/master/quickstarts/conduit/runway.yml -OutFile runway.yml


Deploying
^^^^^^^^^

Execute ``pipenv run runway deploy``, enter ``all`` (to deploy the backend
followed by the frontend). Deployment will take some time (mostly waiting for
the CloudFront distribution to stabilize).

The CloudFront domain at which the site can be reached will be displayed near
the last lines of output once deployment is complete, e.g.:

``staticsite: sync & CF invalidation of E17B5JWPMTX5Z8 (domain ddy1q4je03d7u.cloudfront.net) complete``


Teardown
^^^^^^^^

Execute ``pipenv run runway destroy``, enter ``all``.

The backend DynamoDB tables will still be retained after the destroy is
complete. They must be deleted separately:

On macOS/Linux:
::

    for i in realworld-dev-articles realworld-dev-comments realworld-dev-users; do aws dynamodb delete-table --region us-east-1 --table-name $i; done

On Windows:
::

    foreach($table in @("realworld-dev-articles", "realworld-dev-comments", "realworld-dev-users"))
    {
      CMD /C "pipenv run aws dynamodb delete-table --region us-east-1 --table-name $table"
    }


Next Steps / Additional Notes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `serverless-plugin-export-endpoints plugin <https://github.com/ar90n/serverless-plugin-export-endpoints>`_
is a good alternative to the custom update_env_endpoint.py script deployed
above to update the environment file.


Permissions
^^^^^^^^^^^
The specific IAM permissions required to manage the resources in this demo are
as follows

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
