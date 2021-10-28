# Kubernetes CloudFormation Sample

## Overview

This repo represents a sample infrastructure deployment of EKS, featuring:

- Consolidated configuration for each environment in runway.yml
  - Environments in this context correlate with separate k8s clusters (e.g. a dev & prod cluster)
- Per-environment kubectl version management
  - Because each k8s environment has a `.kubectl-version` file, kubectl does not need to be installed (Runway will handle downloading and executing the appropriate version for the environment)
- kustomize-templated k8s configurations
  - Runway uses the kustomize base/overlays directory structure to apply per-environment k8s configurations

## Prerequisites

- [awscli](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-install.html)
- [Runway](https://pypi.org/project/runway/)
- existing VPC & subnets created in an AWS account ([recommended AWS guide](https://docs.aws.amazon.com/eks/latest/userguide/create-public-private-vpc.html))

## Setup

### Deployment

1. Update the VPC-id & subnet ids in [runway.yml](./runway.yml) to reflect your VPC & private subnets.
2. Deploy to the **dev** environment (`runway deploy -e dev`). This will take some time to complete.

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
