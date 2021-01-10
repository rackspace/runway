# Overview

This repo represents a sample Terraform infrastructure deployment of EKS & Flux. Terraform is used to manage the base infrastructure components, including a CodeCommit git repo configured for continous deployment via Flux.

## Pre-reqs

* Runway
* Docker
* awscli

## Setup

### Deployment

#### Part 1: Deploying Flux

Update the kubectl-access-role-arn to specify the IAM role to which cluster admin access should be granted. E.g., if you assume an IAM role for operating in your account `aws sts get-caller-identity --query 'Arn' --output text` will show you the assumed role principal like:

```
arn:aws:sts::123456789012:assumed-role/myIamRole/guy.incognito
```

You can use that arn to determine the IAM role arn for runway.yml:

```
        kubectl-access-role-arn: arn:aws:iam::123456789012:role/myIamRole
```

(to use IAM users instead, see `mapUsers` in `eks-base.tf/main.tf`)

After updating the role ARN, deploy to the dev environment via:

macOS/Linux:

```
export DEPLOY_ENVIRONMENT=dev
runway deploy
```

Windows:

```
$env:DEPLOY_ENVIRONMENT = dev
runway deploy
```

#### Part 2: Pushing to the Flux repo

Setup and push an initial commit to the AWS CodeCommit git repository called `flux-dev`, e.g.:

macOS/Linux:

```bash
CC_REPO_URL=https://git-codecommit.us-west-2.amazonaws.com/v1/repos/flux-dev
cd flux-dev
git init
git config credential."$CC_REPO_URL".helper '!aws codecommit credential-helper $@'
git config credential."$CC_REPO_URL".UseHttpPath true
git remote add origin $CC_REPO_URL
git add *
git commit -m "initial commit"
git push --set-upstream origin master
```

Windows:

```powershell
cd $home
$CC_REPO_URL = "https://git-codecommit.us-west-2.amazonaws.com/v1/repos/flux-dev"
cd flux-dev
git init
git config credential."$CC_REPO_URL".helper '!aws codecommit credential-helper $@'
git config credential."$CC_REPO_URL".UseHttpPath true
git remote add origin $CC_REPO_URL
git add *
git commit -m "initial commit"
git push --set-upstream origin master
```

[Wait 5 minutes](https://docs.fluxcd.io/en/1.21.1/faq/#how-often-does-flux-check-for-new-git-commits-and-can-i-make-it-sync-faster), and:

1) The CodeCommit git repo will have a `flux` tag indicated the applied state of the repo.
2) A namespace titled `demo` will appear in the cluster

macOS/Linux:

```
git ls-remote
cd ..
eval $(runway envvars)
runway kbenv run -- get namespace
```

Windows:

```
git ls-remote
cd ..
runway envvars | iex
runway kbenv run -- get namespace
```

### Post-Deployment

* It is strongly recommended to [disable public access](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html#modify-endpoint-access) to the EKS API

### Teardown

`runway destroy` will teardown the entire stack.

