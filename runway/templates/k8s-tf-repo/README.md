# Kubernetes Terraform Sample

## Overview

This repo represents a sample Terraform infrastructure deployment of EKS, featuring:

- Consolidated configuration for each environment in runway.yml
  - Environments in this context correlate with separate k8s clusters (e.g. a dev & prod cluster)
- Per-environment kubectl version management
  - Because each k8s environment has a `.kubectl-version` file, kubectl does not need to be installed (Runway will handle downloading and executing the appropriate version for the environment)
- IAM Role enabled Service Account (IRSA) usage
- kustomize-templated k8s configurations
  - Runway uses the kustomize base/overlays directory structure to apply per-environment k8s configurations

## Prerequisites

- [awscli](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)
- [Runway](https://pypi.org/project/runway/)
- AWS IAM Role or IAM User (should be the User or assumed Role being used to access the AWS account)

## Setup

### Deployment

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
  (Terraform will prompt twice for confirmation; pass the `--ci` flag to prevent any prompting)

### Post-Deployment

It is **strongly recommended** to [disable public access](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html#modify-endpoint-access) to the EKS API if this infrastructure will be left running for any period of time.

### Teardown

`runway destroy -e dev` will teardown all infrastructure deployed as part of this sample project.

## Hello-World App

After deployment, the sample hello-world app will be available at port 8666 on the address shown via:

macOS/Linux:

```sh
RUNWAY_ENV="dev"
eval $(runway envvars -e $RUNWAY_ENV)
cd service-hello-world.k8s/overlays/$RUNWAY_ENV
echo "http://$(runway kbenv run -- get svc $RUNWAY_ENV-the-service -o jsonpath="{.status.loadBalancer.ingress[0].hostname}"):8666/"
```

Windows:

```powershell
$RUNWAY_ENV = "dev"
runway envvars -e $RUNWAY_ENV | iex
cd service-hello-world.k8s/overlays/$RUNWAY_ENV
Write-Host "http://$(runway kbenv run -- get svc $RUNWAY_ENV-the-service -o jsonpath="{.status.loadBalancer.ingress[0].hostname}"):8666/"
```

Compare its dev & prod overlays for examples on per-environment app kustomization.

## IAM Role enabled Service Accounts (IRSA)

An IAM OIDC identity provider is configured (see `aws_iam_openid_connect_provider` in the [eks-base.tf](./eks-base.tf/main.tf) module) to allow containers access to AWS APIs (by way of annotated k8s service accounts).

The example [job-s3-echo.tf](./job-s3-echo.tf/main.tf) module creates an IAM role, a k8s service account annotated with the role, and a job using the service account to place an object on S3 (see the bucket starting with `eks-s3-echo-` after deployment).
