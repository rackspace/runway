# Runway

[![CI/CD](https://github.com/onicagroup/runway/workflows/CI/CD/badge.svg?branch=master)](https://github.com/onicagroup/runway/actions?query=workflow%3ACI%2FCD)
[![codecov](https://codecov.io/gh/onicagroup/runway/branch/master/graph/badge.svg?token=Ku28I0RY80)](https://codecov.io/gh/onicagroup/runway)
[![PyPi](https://img.shields.io/pypi/v/runway?style=flat)](https://pypi.org/project/runway/)
[![npm](https://img.shields.io/npm/v/@onica/runway?style=flat)](https://www.npmjs.com/package/@onica/runway)
[![code style: black](https://img.shields.io/badge/code%20style-black-000000.svg?style=flat)](https://github.com/psf/black)

![runway-example.gif](https://raw.githubusercontent.com/onicagroup/runway/master/docs/source/images/runway-example.gif)

Runway is a lightweight integration app designed to ease management of infrastructure tools.

Its main goals are to encourage GitOps best-practices, avoid convoluted Makefiles/scripts (enabling identical deployments from a workstation or CI job), and enable developers/admins to use the best tool for any given job.


## Features

* Centralized environment-specific configuration
* Automatic environment identification from git branches
* Automatic linting/verification
* Support of IAM roles to assume for each deployment
* Terraform backend/workspace config management w/per-environment tfvars
* Automatic kubectl/terraform version management per-environment

### Supported Deployment Tools

* AWS CDK
* Kubectl
* Serverless Framework
* CFNgin (CloudFormation)
* Static websites (build & deploy to S3+CloudFront)
* Terraform


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

Runway is available via any of the following installation methods. Use whatever works best for your project/team (it's the same application no matter how you obtain it).

### HTTPS Download (e.g cURL)

Use one of the endpoints below to download a single-binary executable version of Runway based on your operating system.

| Operating System | Endpoint                               |
|------------------|----------------------------------------|
| Linux            | <https://oni.ca/runway/latest/linux>   |
| macOS            | <https://oni.ca/runway/latest/osx>     |
| Windows          | <https://oni.ca/runway/latest/windows> |

```shell
$ curl -L oni.ca/runway/latest/osx -o runway
$ chmod +x runway
$ ./runway new
```

**Suggested use:** CloudFormation or Terraform projects


### npm

```shell
$ npm i -D @onica/runway
$ npx runway new
```

**Suggested use:** Serverless or AWS CDK projects


### pip (or poetry, etc)

```shell
$ pip install runway
$ runway new
# OR
$ poetry add --dev runway
$ poetry run runway new
```

**Suggested use:** Python projects


## Documentation

See the [doc site](https://docs.onica.com/projects/runway) for full documentation.

Quickstart documentation, including CloudFormation templates and walkthrough can be found [here](https://docs.onica.com/projects/runway/page/quickstart/index.html)
