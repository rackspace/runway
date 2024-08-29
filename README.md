# Runway

[![CI/CD](https://github.com/rackspace/runway/workflows/CI/CD/badge.svg?branch=master)](https://github.com/rackspace/runway/actions?query=workflow%3ACI%2FCD)
[![codecov](https://codecov.io/gh/rackspace/runway/branch/master/graph/badge.svg?token=Ku28I0RY80)](https://codecov.io/gh/rackspace/runway)
[![PyPi](https://img.shields.io/pypi/v/runway?style=flat)](https://pypi.org/project/runway/)
[![code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat)](https://github.com/psf/black)

![runway-example.gif](https://raw.githubusercontent.com/rackspace/runway/master/docs/source/images/runway-example.gif)

Runway is a lightweight integration app designed to ease management of infrastructure tools.

Its main goals are to encourage GitOps best-practices, avoid convoluted Makefiles/scripts (enabling identical deployments from a workstation or CI job), and enable developers/admins to use the best tool for any given job.

## Features

- Centralized environment-specific configuration
- Automatic environment identification from git branches
- Automatic linting/verification
- Support of IAM roles to assume for each deployment
- Terraform backend/workspace config management w/per-environment tfvars
- Automatic kubectl/terraform version management per-environment

### Supported Deployment Tools

- AWS CDK
- Kubectl
- Serverless Framework
- CFNgin (CloudFormation)
- Static websites (build & deploy to S3+CloudFront)
- Terraform

## Example

A typical Runway configuration is unobtrusive -- it just lists the deployment order and locations (regions).

```yml
deployments:
  - modules:
      - resources.tf  # terraform resources
      - backend.sls  # serverless lambda functions
      - frontend  # static web site
    environments:  # Environments
      dev: "123456789012"  # AWS development Account ID
      prod: "234567890123"  # AWS production Account ID
    regions:
      - us-east-1
```

The example above contains enough information for Runway to deploy all resources, lambda functions and a static website backed by S3 and Cloudfront in either dev or prod environments

## Install

```shell
$ pip install runway
$ runway new
# OR
$ poetry add --dev runway
$ poetry run runway new
```

## Documentation

See the [doc site](https://runway.readthedocs.io) for full documentation.

Quickstart documentation, including CloudFormation templates and walkthrough can be found [here](https://runway.readthedocs.io/page/quickstart/index.html)
