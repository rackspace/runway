# Kubernetes CloudFormation Sample

## Overview

This repo represents a sample infrastructure deployment of EKS, featuring:

* Consolidated configuration for each environment in runway.yml
  * Environments in this context correlate with separate k8s clusters (e.g. a dev & prod cluster)
* Per-environment kubectl version management
  * Because each k8s environment has a `.kubectl-version` file, kubectl does not need to be installed (Runway will handle downloading and executing the appropriate version for the environment)
* kustomize-templated k8s configurations
  * Runway uses the kustomize base/overlays directory structure to apply per-environment k8s configurations

## Pre-reqs

* Runway
* awscli

## Setup

### Deployment

Update the VPC-id & subnet ids in runway.yml to reflect your VPC & private subnets.

Then deploy to the dev environment via:

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

### Post-Deployment

* It is strongly recommended to [disable public access](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html#modify-endpoint-access) to the EKS API

### Teardown

`runway destroy` will teardown the entire stack, though it will error during the cert-manager teardown (errors are fine to ignore; just proceed with deleting the rest of the modules)

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
