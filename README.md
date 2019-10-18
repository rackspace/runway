# Runway

[![Build Status](https://travis-ci.org/onicagroup/runway.svg?branch=master)](https://travis-ci.org/onicagroup/runway)


## What?

Runway is the perfect companion for full stack development.
It's a lightweight integration library to ease management of multiple infrastructure deployment tools


## Why?

Runway's main goal is to avoid convoluted Makefiles/CI.

Runway simplifies the deployment by integrating multiple tools into single build process with centralized environment-specific settings, e.g. dev, test, prod.


## Example

A typical runway configuration is unobtrusive, it just contains references to the paths of the inner deployments.

```yml
deployments:
  - modules:
    - path: ./resources.tf # terraform resources
    - path: ./backend.sls # serverless lambda functions
    - path: ./frontend # static web site
      class_path: runway.module.staticsite.StaticSite
    environments: # Environment settings
        dev:
            foo: dev-bar
        prod:
            foo: prod-bar
```
The example above contains enough information for Runway to deploy all resources, lambda functions and a static website backed by S3 and Cloudfront in either dev or prod environments


## Supported deployment tools

* AWS Cloudformation
* AWS CDK
* Terraform
* Stacker
* Serverless


## Features

* Centralized environment-specific configuration
* Automatic environment identification from GIT branches
* Automatic linting/verification
* Support of IAM roles to assume for each deployment
* Wrangle Terraform backend/workspace configs w/per-environment tfvars


## How?

See the [doc site](https://docs.onica.com/projects/runway).

Complete quickstart documentation, including Docker images, CloudFormation templates, and walkthrough can be found [here](https://docs.onica.com/projects/runway/en/latest/quickstart.html)
