# Tests to Fix

* ModuleTags test is currently broken; appears no tests are being run
    * This was developed during reworking of the integration tests. Should be updated to match the error number returns as shown in the commands test

# Tests to Write

## CloudFormation

### Module-defined Environment Variables

Ensure that modules with defined env_vars work and don't pollute each other:

```
---
deployments:
  - modules:
      - path: module1.cfn
        env_vars:
          "*":
            FOO: BAR
      - module2.cfn
    regions:
      - us-west-2
    environments:
      dev:
        namespace: dev
```

^ `FOO` should only be set in module1, and not module2

(this can almost certainly be incorporated in another test)


## Terraform

### Map values provided in runway.yml environments

Ensure that environment dicts are properly converted to strings

runway.yml
```
---
global_variables: &global_variables
  customer: msp-agasper

deployments:
  - name: Env Setup
    modules:
      - path: tfstate.cfn
    regions:
      - us-east-1
    environments:
      test:
        environment: test
  - name: Some S3 Bucket
    modules:
      - path: examples-s3
    regions:
      - us-east-1
    module_options:
      terraform_backend_config:
        region: us-east-1
      terraform_backend_cfn_outputs:
        bucket: test-tf-state::TerraformStateBucketName
        dynamodb_table: test-tf-state::TerraformStateTableName
    environments:
      test:
        <<: *global_variables
        region: us-east-1
        environment: test
        tags:
          Purpose: Example
          ResourceType: s3-bucket

```

terraform:
```
terraform {
    required_version = ">= 0.12.10"

    backend "s3" {
        key = "example-application/terraform.tfstate"
    }
}

variable "customer" {
    type = string
    description = "The name of the customer."
    default = "me"
}

variable "environment" {
    type = string
    description = "The name of the environment"
}

variable "region" {
    type = string
    description = "The region to deploy resources in."
}

variable "tags" {
    type = map(string)
    description = "A map of key value pairs for the bucket resource"
    default = {
        "key1": "value1",
        "key2": "value2"
    }
}

provider "aws" {
    region = "${var.region}"
}

resource "aws_s3_bucket" "example_bucket" {
    tags = "${var.tags}"
}
```

Without conversion, python will attempt to shell out with TF_VAR_tags=`<dictobject>` causing
a stacktrace
