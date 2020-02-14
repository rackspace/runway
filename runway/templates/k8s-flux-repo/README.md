## Overview

This repo represents a sample Terraform infrastructure deployment of EKS + Flux

## Pre-reqs

* Runway
* Docker
* awscli

## Getting started

- Update runway.yml
  Update the kubectl-access-role-arn to specify the IAM role to which cluster admin access should be granted. E.g., if you assume an IAM role for operating in your account `aws sts get-caller-identity --query 'Arn' --output text` will show you the assumed role principal like:

- Deploy the stack
`DEPLOY_ENVIRONMENT=dev runway deploy`

- clone the git repository called `flux-dev` from AWS codecommit and push the contents 
  located under the folder `flux-repository-sample`
  see https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-connect.html

- wait up to 5 minutes to see the a namespace called `demo` in the cluster
  `aws eks update-kubeconfig --region us-east-1 --name k8s-dev --kubeconfig .kubeconfig`
  `kubectl --kubeconfig=./.kubeconfig get namespace`

### Post-Deployment

* It is strongly recommended to [disable public access](https://docs.aws.amazon.com/eks/latest/userguide/cluster-endpoint.html#modify-endpoint-access) to the EKS API

### Teardown

`DEPLOY_ENVIRONMENT=dev runway deploy` will teardown the entire stack.

