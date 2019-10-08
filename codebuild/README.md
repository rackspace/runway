## How To Deploy
1. Go to the AWS Console and select CodeBuild
2. Click on "Create project"
3. In the source section select the GitHub provider
4. Click on "Connect to GitHub"
5. A new window will open
6. Log in to GitHub and under the "Organization access" select "Request" next to "onicagroup"
7. Once access has been granted under the `codebuild` directory run `DEPLOY_ENVIRONMENT=common pipenv run runway deploy`
