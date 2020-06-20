# Useful commands

* `npm run build`   compile typescript to js
* `npm run watch`   watch for changes and compile
* `npx cdk deploy`  deploy this stack to your default AWS account/region
* `npx cdk diff`    compare deployed stack with current state
* `npx cdk synth`   emits the synthesized CloudFormation template

# Add CDK Output to .gitignore

AWS CDK has temp output that it created that should not be commited into the repo

If you build a sample from 'runway gen-sample cdk-tsc' to use as your model add the follow code block to your .gitignore

This will prevent tmp output that cdk creates from being commited to your repo

```
*.js
!jest.config.js
*.d.ts
node_modules

# CDK asset staging directory
.cdk.staging
cdk.out
cdk.context.json
```
