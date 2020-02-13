# Integration Test Infrastructure

## Initial Setup

### CodeBuild Repo Access

1. Login to the Runway testing account
2. Go to the AWS Console and select CodeBuild
3. Click on "Create project"
4. In the source section select the GitHub provider
5. Click on "Connect to GitHub"
6. A new window will open
7. Log in to GitHub and under the "Organization access" select "Request" next to "onicagroup"
8. Complete the request to create the CodeBuild source credential, then cancel the project creation

### Deployment/Updates

1. `pipenv sync`
2. Login to the alt testing account
3. `cd alt_account_role/common && pipenv run runway deploy`
4. Login to the testing account
5. `cd ../../codebuild/common && pipenv run runway deploy`
