# Backend setup
terraform {
  backend "s3" {
    key = "eks-job-s3-echo.tfstate"
  }
}

# Variable definitions
variable "region" {}

# Provider and access setup
provider "aws" {
  version = "~> 2.43"
  region = "${var.region}"
}

# Data and resources
data "aws_region" "current" {}

locals {
  cluster_name = "k8s-${terraform.workspace}"
  job_name = "s3-echo"
  sa_name = "${local.job_name}-serviceaccount"
}

data "aws_eks_cluster" "cluster" {
  name = "${local.cluster_name}"
}

data "aws_eks_cluster_auth" "cluster_auth" {
  name = "${data.aws_eks_cluster.cluster.id}"
}

provider "kubernetes" {
  host = "${data.aws_eks_cluster.cluster.endpoint}"
  cluster_ca_certificate = "${base64decode(data.aws_eks_cluster.cluster.certificate_authority.0.data)}"
  token = "${data.aws_eks_cluster_auth.cluster_auth.token}"
  load_config_file = false
  # Pinned back from 1.11 pending resolution of:
  # https://github.com/terraform-providers/terraform-provider-kubernetes/issues/759
  version = "~> 1.10.0"
}

data "aws_ssm_parameter" "oidc_iam_provider_cluster_url" {
  name = "/${local.cluster_name}/oidc-iam-provider-cluster-url"
}
data "aws_ssm_parameter" "oidc_iam_provider_cluster_arn" {
  name = "/${local.cluster_name}/oidc-iam-provider-cluster-arn"
}

resource "aws_s3_bucket" "bucket" {
  bucket_prefix = "eks-${local.job_name}-"
  acl = "private"
  force_destroy = "true"
}

data "aws_iam_policy_document" "service_account_assume_role_policy" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect = "Allow"

    condition {
      test = "StringEquals"
      variable = "${replace(data.aws_ssm_parameter.oidc_iam_provider_cluster_url.value, "https://", "")}:sub"
      values = ["system:serviceaccount:default:${local.sa_name}"]
    }

    principals {
      identifiers = ["${data.aws_ssm_parameter.oidc_iam_provider_cluster_arn.value}"]
      type = "Federated"
    }
  }
}
resource "aws_iam_role" "service_account" {
  name_prefix = "eks-${local.sa_name}-"
  assume_role_policy = "${data.aws_iam_policy_document.service_account_assume_role_policy.json}"
}
data "aws_iam_policy_document" "service_account" {

  statement {
    actions = [
      "s3:ListBucket",
      "s3:ListBucketVersions"
    ]
    resources = ["${aws_s3_bucket.bucket.arn}"]
  }

  statement {
    actions = [
      "s3:GetObject",
      "s3:PutObject*"
    ]
    resources = ["${aws_s3_bucket.bucket.arn}/*"]
  }
}
resource "aws_iam_role_policy" "service_account" {
  role = "${aws_iam_role.service_account.id}"

  policy = "${data.aws_iam_policy_document.service_account.json}"
}

resource "kubernetes_service_account" "service_account" {
  metadata {
    name = "${local.sa_name}"
    annotations = "${
      map(
       "eks.amazonaws.com/role-arn", "${aws_iam_role.service_account.arn}"
      )
    }"
  }
  depends_on = [
    "aws_iam_role_policy.service_account",
  ]
  # Sleep on initial creation here to avoid api errors on initial job creation.
  provisioner "local-exec" {
    command = "runway run-python sleep.py"
  }
}

resource "kubernetes_job" "job" {
  metadata {
    name = "${local.job_name}"
  }
  spec {
    template {
      metadata {}
      spec {
        service_account_name = "${kubernetes_service_account.service_account.metadata.0.name}"
        container {
          name    = "main"
          image   = "amazonlinux:2018.03"
          command = [
            "sh",
            "-c",
            "curl -sL -o /s3-echoer https://github.com/mhausenblas/s3-echoer/releases/latest/download/s3-echoer-linux && chmod +x /s3-echoer && echo This is an in-cluster test | /s3-echoer $BUCKET_NAME"
          ]
          env {
            name  = "AWS_DEFAULT_REGION"
            value = "${var.region}"
          }
          env {
            name  = "BUCKET_NAME"
            value = "${aws_s3_bucket.bucket.id}"
          }
          env {
            name  = "ENABLE_IRP"
            value = "true"
          }
          volume_mount {
            mount_path = "/var/run/secrets/kubernetes.io/serviceaccount"
            name = "${kubernetes_service_account.service_account.default_secret_name}"
            read_only = true
          }
        }
        volume {
          name = "${kubernetes_service_account.service_account.default_secret_name}"
          secret {
            secret_name = "${kubernetes_service_account.service_account.default_secret_name}"
          }
        }
        restart_policy = "Never"
      }
    }
  }
}
