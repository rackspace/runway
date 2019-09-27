## Overview
Each .sls folder contains an entire serverless project. Each folder also contains
a `runway.yml` file that needs to have 2 environments; `dev` and `test`

The way the tests work right now is each folder is deployed with the `DEPLOY_ENVIRONMENT`
set to `dev` and then it switches to `test` and deploys again.
