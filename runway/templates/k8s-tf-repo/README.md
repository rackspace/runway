# Kubernetes Terraform Sample

## Overview

This repo represents a sample Terraform infrastructure deployment of EKS, featuring:

* Consolidated configuration for each environment in runway.yml
  * Environments in this context correlate with separate k8s clusters (e.g. a dev & prod cluster)
* Per-environment kubectl version management
  * Because each k8s environment has a `.kubectl-version` file, kubectl does not need to be installed (Runway will handle downloading and executing the appropriate version for the environment)
* IAM Role enabled Service Account (IRSA) usage
* kustomize-templated k8s configurations
  * Runway uses the kustomize base/overlays directory structure to apply per-environment k8s configurations

## Pre-reqs

* Runway
* awscli

## Setup

### Deployment

Update the kubectl-access-role-arn to specify the IAM role to which cluster admin access should be granted. E.g., if you assume an IAM role for operating in your account `aws sts get-caller-identity --query 'Arn' --output text` will show you the assumed role principal like:

```
arn:aws:sts::123456789012:assumed-role/myIamRole/guy.incognito
```

You can use that arn to determine the IAM role arn for runway.yml:

```
        kubectl-access-role-arn: arn:aws:iam::123456789012:role/myIamRole
```

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

(Terraform will prompt twice for confirmation; set the `CI` environment variable to `1` before deployment to prevent any prompting)

### Post-Deployment

* It is strongly recommended to [disable public access](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html#modify-endpoint-access) to the EKS API

### Teardown

`runway destroy` will teardown the entire stack.

## Hello-World App

After deployment, the sample hello-world app will be available at port 8666 on the address shown via:

macOS/Linux:

```
eval $(runway envvars)
RUNWAY_ENV=$(runway whichenv)
cd service-hello-world.k8s/overlays/$RUNWAY_ENV
echo "http://$(runway kbenv run -- get svc $RUNWAY_ENV-the-service -o jsonpath="{.status.loadBalancer.ingress[0].hostname}"):8666/"
```

Windows:

```
runway envvars | iex
$RUNWAY_ENV = $(runway whichenv)
cd service-hello-world.k8s/overlays/$RUNWAY_ENV
Write-Host "http://$(runway kbenv run -- get svc $RUNWAY_ENV-the-service -o jsonpath="{.status.loadBalancer.ingress[0].hostname}"):8666/"
```

Compare its dev & prod overlays for examples on per-environment app kustomization.

## IAM Role enabled Service Accounts (IRSA)

An IAM OIDC identity provider is configured (see `aws_iam_openid_connect_provider` in the eks-base.tf module) to allow containers access to AWS APIs (by way of annotated k8s service accounts).

The example `job-s3-echo.tf` module creates an IAM role, a k8s service account annotated with the role, and a job using the service account to place an object on S3 (see the bucket starting with `eks-s3-echo-` after deployment).
