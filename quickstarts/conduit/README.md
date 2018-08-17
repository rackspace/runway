## Deploying the Conduit Web App

The [Medium.com-clone "RealWorld" demo app](https://github.com/gothinkster/realworld) named Conduit provides a simple demonstration of using Runway to deploy Serverless Framework backend with an Angular frontend.

### Prerequisites

1. An AWS account, and configured terminal environment for interacting with it with an admin role.
2. The following installed tools:

  * [pipenv](https://docs.pipenv.org/) (e.g. `pip install --user pipenv`)
  * [npm](https://nodejs.org/en/)
  * [yarn](https://yarnpkg.com)
  * [curl](https://curl.haxx.se/)  (Available out of the box on macOS)
  * [git](https://git-scm.com/)  (Available out of the box on macOS)

### Setup

Execute the following to setup your conduit repo:
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

Execute `runway deploy`, enter `all` (to deploy the backend followed by the frontend). Deployment will take some time (mostly waiting for the CloudFront distribution to stabilize).

The CloudFront domain at which the site can be reached will be displayed near the last lines of output once deployment is complete, e.g.:
```
staticsite: sync & CF invalidation of E17B5JWPMTX5Z8 (domain ddy1q4je03d7u.cloudfront.net) complete
```

### Teardown

Execute `runway destroy`, enter `all`.

The backend DynamoDB tables will still be retained after the destroy is complete. They must be deleted separately, e.g.:
````
for i in realworld-dev-articles realworld-dev-comments realworld-dev-users; do aws dynamodb delete-table --region us-east-1 --table-name $i; done
```
