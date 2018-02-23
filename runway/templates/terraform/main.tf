terraform {
  backend "s3" {
    key = "sampleapp"
  }
}

variable "region" {}

# Specify the provider and access details
provider "aws" {
  version = "~> 0.1"
  region = "${var.region}"
}

# Continue with data and resources here
