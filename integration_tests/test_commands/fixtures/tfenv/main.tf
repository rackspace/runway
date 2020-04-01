provider "aws" {
  version = "~> 2.0"
  region  = "us-east-1"
}

resource "random_uuid" "uuid" { }

locals {
  key = "/r4y/tfenv/integrationtest/${random_uuid.uuid.result}"
}

resource "aws_ssm_parameter" "foo" {
  name = "${local.key}"
  type  = "String"
  value = "bar"
}

output "key" {
  value = "${local.key}"
}
