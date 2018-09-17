## Deploying the Conduit Web App

The [Medium.com-clone "RealWorld" demo app](https://github.com/gothinkster/realworld) named Conduit provides a simple demonstration of using Runway to deploy a Serverless Framework backend with an Angular frontend.

### Prerequisites

1. An AWS account, and configured terminal environment for interacting with it with an admin role.
2. The following installed tools:
    * [pipenv](https://docs.pipenv.org/) (e.g. `pip install --user pipenv`)
    * [npm](https://nodejs.org/en/)
    * [yarn](https://yarnpkg.com)
    * [curl](https://curl.haxx.se/)  (Available out of the box on macOS)
    * [git](https://git-scm.com/)  (Available out of the box on macOS)
    * [sed](https://www.gnu.org/software/sed/)  (Available out of the box on macOS)

### Setup

Execute the following to setup your Conduit repo:
```
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
```

Notes:
  * The [serverless-plugin-export-endpoints plugin](https://github.com/ar90n/serverless-plugin-export-endpoints) is a good alternative to the custom `update_env_endpoint.py` script deployed above to update the environment file.

### Deploying

Execute `pipenv run runway deploy`, enter `all` (to deploy the backend followed by the frontend). Deployment will take some time (mostly waiting for the CloudFront distribution to stabilize).

The CloudFront domain at which the site can be reached will be displayed near the last lines of output once deployment is complete, e.g.:
```
staticsite: sync & CF invalidation of E17B5JWPMTX5Z8 (domain ddy1q4je03d7u.cloudfront.net) complete
```

### Teardown

Execute `pipenv run runway destroy`, enter `all`.

The backend DynamoDB tables will still be retained after the destroy is complete. They must be deleted separately, e.g.:
```
for i in realworld-dev-articles realworld-dev-comments realworld-dev-users; do aws dynamodb delete-table --region us-east-1 --table-name $i; done
```

### Permissions

The specific IAM permissions required to manage the resources in this demo are as follows:
```
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
```
