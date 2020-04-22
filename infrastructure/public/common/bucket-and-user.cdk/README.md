# bucket-and-user.cdk

GitHub publishes artifacts to an S3 bucket created by the CloudFormation stack in the this repo, using IAM credentials from a user created in the same stack. (see lib/assets-stack.ts for the template source)
