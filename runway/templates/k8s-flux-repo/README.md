# Overview

This repo represents a sample Terraform infrastructure deployment of EKS & Flux.Terraform is used to manage the base infrastructure components, including a CodeCommit git repo configured for continuos deployment via Flux.

## Prerequisites

- [awscli](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)
- [Docker](https://docs.docker.com/get-docker/)
- [Runway](https://pypi.org/project/runway/)

## Setup

### Deployment

#### Part 1: Deploying Flux

1. Update the `kubectl-access-role-arn` parameter in [runway.yml](./runway.yml) to specify the IAM role to which cluster admin access should be granted.
   E.g., if you assume an IAM role for operating in your account `aws sts get-caller-identity --query 'Arn' --output text` will show you the assumed role principal like:

    ```text
    arn:aws:sts::123456789012:assumed-role/myIamRole/guy.incognito
    ```

    You can use that arn to determine the IAM role arn for runway.yml:

    ```yaml
    deployments:
      ...
      - modules:
        ...
        parameters:
          ...
          kubectl-access-role-arn: arn:aws:iam::123456789012:role/myIamRole
    ```

    (to use IAM users instead, see `mapUsers` in `eks-base.tf/main.tf`)

2. After updating the role ARN, deploy to the dev environment (`runway deploy -e dev`).
   This will take some time to complete.
  (Terraform will prompt for confirmation; pass the `--ci` flag to prevent any prompting)

#### Part 2: Pushing to the Flux repo

1. Setup and push an initial commit to the AWS CodeCommit git repository called `flux-dev`.

    macOS/Linux:

    ```sh
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

2. [Wait 5 minutes](https://fluxcd.io/legacy/flux/faq/#how-often-does-flux-check-for-new-images)...

3. The CodeCommit git repo will have a `flux` tag indicated the applied state of the repo and a namespace titled `demo` will appear in the cluster.

    macOS/Linux:

    ```sh
    git ls-remote
    cd ..
    eval $(runway envvars -e dev)
    runway kbenv run -- get namespace
    ```

    Windows:

    ```powershell
    git ls-remote
    cd ..
    runway envvars -e dev | iex
    runway kbenv run -- get namespace
    ```

### Post-Deployment

It is **strongly recommended** to [disable public access](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html#modify-endpoint-access) to the EKS API if this infrastructure will be left running for any period of time.

### Teardown

`runway destroy -e dev` will teardown all infrastructure deployed as part of this sample project.
