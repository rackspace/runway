# Runway

[![Build Status](https://travis-ci.org/onicagroup/r4y.svg?branch=master)](https://travis-ci.org/onicagroup/r4y)
[![PyPi](https://img.shields.io/pypi/v/r4y?style=flat)](https://pypi.org/project/r4y/)
[![npm](https://img.shields.io/npm/v/@onica/r4y?style=flat)](https://www.npmjs.com/package/@onica/r4y)

![r4y-example.gif](https://raw.githubusercontent.com/onicagroup/r4y/master/docs/r4y-example.gif)

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
* Stacker (CloudFormation)
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
    environments:  # Environment settings
        dev:
            foo: dev-bar
        prod:
            foo: prod-bar
```

The example above contains enough information for Runway to deploy all resources, lambda functions and a static website backed by S3 and Cloudfront in either dev or prod environments


## Install

Runway is available via any of the following installation methods. Use whatever works best for your project/team (it's the same application no matter how you obtain it).

### HTTPS Download (e.g cURL)

Use one of the endpoints below to download a single-binary executable version of Runway based on your operating system.

| Operating System | Endpoint                               |
|------------------|----------------------------------------|
| Linux            | <https://oni.ca/r4y/latest/linux>   |
| macOS            | <https://oni.ca/r4y/latest/osx>     |
| Windows          | <https://oni.ca/r4y/latest/windows> |

```shell
$ curl -L oni.ca/r4y/latest/osx -o r4y
$ chmod +x r4y
$ ./r4y init
```

**Suggested use:** CloudFormation or Terraform projects


### npm

```shell
$ npm i -D @onica/r4y
$ npx r4y init
```

**Suggested use:** Serverless or AWS CDK projects


### pip (or pipenv,poetry,etc)

```shell
$ pip install r4y
$ r4y init
# OR
$ pipenv install r4y
$ pipenv run r4y init
```

**Suggested use:** Python projects


## Documentation

See the [doc site](https://docs.onica.com/projects/r4y) for full documentation.

Quickstart documentation, including CloudFormation templates and walkthrough can be found [here](https://docs.onica.com/projects/r4y/en/latest/quickstart.html)

## Community Chat

Drop into the [#r4y channel](https://kiwiirc.com/client/irc.freenode.net/?nick=RunwayHelp?#r4y) for discussion/questions.
