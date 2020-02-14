
terraform {
  backend "s3" {
    key = "eks-flux.tfstate"
  }
}

locals {
  cluster_name = "k8s-${terraform.workspace}"
  flux_repository = "flux-${terraform.workspace}"
  flux_namespace = "flux"
  flux_service_account = "flux"
  flux_version = "1.15.0"
}

data "aws_eks_cluster" "cluster" {
  name = "${local.cluster_name}"
}

data "aws_eks_cluster_auth" "cluster_auth" {
  name = "${data.aws_eks_cluster.cluster.id}"
}

data "aws_ssm_parameter" "oidc_iam_provider_cluster_url" {
  name = "/${local.cluster_name}/oidc-iam-provider-cluster-url"
}
data "aws_ssm_parameter" "oidc_iam_provider_cluster_arn" {
  name = "/${local.cluster_name}/oidc-iam-provider-cluster-arn"
}

provider "kubernetes" {
  host = "${data.aws_eks_cluster.cluster.endpoint}"
  cluster_ca_certificate = "${base64decode(data.aws_eks_cluster.cluster.certificate_authority.0.data)}"
  token = "${data.aws_eks_cluster_auth.cluster_auth.token}"
  load_config_file = false
  version = "1.9"
}

provider "aws" {
  version = "~> 2.0"
  region  = "us-east-1"
}

resource "kubernetes_namespace" "flux" {
  metadata {
    name = "${local.flux_namespace}"
  }
}
resource "aws_codecommit_repository" "flux_repository" {
  repository_name = "${local.flux_repository}"
}

data "aws_iam_policy_document" "flux_policy" {

  statement {
    effect = "Allow"
    actions = [
      "codecommit:*"
    ]
    resources = [
      "${aws_codecommit_repository.flux_repository.arn}"
    ]
  }

}

data "aws_iam_policy_document" "flux_service_account_assume_role_policy" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    effect  = "Allow"

    condition {
      test     = "StringEquals"
      variable = "${replace(data.aws_ssm_parameter.oidc_iam_provider_cluster_url.value, "https://", "")}:sub"
      values   = ["system:serviceaccount:${local.flux_namespace}:${local.flux_service_account}"]
    }

    principals {
      identifiers = ["${data.aws_ssm_parameter.oidc_iam_provider_cluster_arn.value}"]
      type        = "Federated"
    }
  }
}

resource "aws_iam_role" "flux_service_account" {
  name               = "${local.flux_service_account}"
  assume_role_policy = "${data.aws_iam_policy_document.flux_service_account_assume_role_policy.json}"
}

resource "aws_iam_role_policy" "flux_service_account" {
  role   = "${aws_iam_role.flux_service_account.id}"
  policy = "${data.aws_iam_policy_document.flux_policy.json}"
}

resource "aws_ecr_repository" "flux_with_awscli" {
  name                 = "${local.flux_repository}"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "null_resource" "flux_image" {

  depends_on = [
    "aws_ecr_repository.flux_with_awscli",
  ]

  provisioner "local-exec" {
    command = "${path.module}/build_image.sh ${aws_ecr_repository.flux_with_awscli.repository_url}"
  }  

}


resource "kubernetes_service_account" "flux_service_account" {
  automount_service_account_token = true
  metadata {
    name      = "${local.flux_service_account}"
    namespace = "${local.flux_namespace}"
    labels = {
      app  = "${local.flux_namespace}"
      name = "${local.flux_namespace}"
    }
    annotations = "${
      map(
       "eks.amazonaws.com/role-arn", "${aws_iam_role.flux_service_account.arn}"
      )
    }"
  }
  depends_on = [
    "aws_iam_role_policy.flux_service_account",
  ]
  provisioner "local-exec" {
    command = "runway run-python sleep.py"
  }  
}

resource "kubernetes_config_map" "flux_git_config" {
  metadata {
    name      = "${local.flux_namespace}-git-config"
    namespace = "${local.flux_namespace}"
    labels = {
      app  = "${local.flux_namespace}"
      name = "${local.flux_namespace}-git-config"
    }
  }
  data = {
    giturl    = "${aws_codecommit_repository.flux_repository.clone_url_http}"
    gitconfig = <<EOF
     [credential "${aws_codecommit_repository.flux_repository.clone_url_http}"]
       helper = !AWS_WEB_IDENTITY_TOKEN_FILE=/var/run/secrets/eks.amazonaws.com/serviceaccount/token AWS_ROLE_ARN=${aws_iam_role.flux_service_account.arn} aws codecommit credential-helper $@
       UseHttpPath = true
    EOF
  }
}

resource "kubernetes_cluster_role_binding" "flux" {
  metadata {
    name = "flux"

    labels = {
      name = "flux"
    }
  }

  subject {
    kind      = "ServiceAccount"
    name      = "${local.flux_service_account}"
    namespace = "${local.flux_namespace}"
  }

  role_ref {
    api_group = "rbac.authorization.k8s.io"
    kind      = "ClusterRole"
    name      = "flux"
  }
}

resource "kubernetes_config_map" "flux_ssh_config" {
  metadata {
    name      = "flux-ssh-config"
    namespace = "${local.flux_namespace}"
  }

  data = {
    known_hosts = "git-codecommit.us-east-1.amazonaws.com,52.94.226.180 ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQCdut7aOM5Zh16OJ+GOP75O7x5oyHKAiA1ieuySetj/hAq4VrAuZV5R2TypZJcKBaripOtTc/Sr0FOU4YvxUla40PPH8N1lbDp6Pnc4BexKsrt2kz++TqIKx5FHmUQV3mit16kxRwHey3dv030+qXBDo3WPQjm2+JLoq0XcadpnCAMCd3ChaBnDRM+51GZbuEFilpZsxUchUzl0gseC+shYOBd7TqxTlIhj/56d/YF1kq7RMZYrwBnyYdVhpLeUJCeYjyx/O6FPSezNTLiinz5jjioWZATgn+G8feL/hIsk8g+7JoIcb2muUlymdxs+8l2lS+8MXqT0q9ohT+Knhb2j\n"
  }
}

resource "kubernetes_secret" "flux_git_deploy" {
  metadata {
    name      = "flux-git-deploy"
    namespace = "${local.flux_namespace}"
  }
  type = "Opaque"
}

resource "kubernetes_cluster_role" "flux" {
  metadata {
    name = "flux"

    labels = {
      name = "flux"
    }
  }

  rule {
    verbs      = ["*"]
    api_groups = ["*"]
    resources  = ["*"]
  }

  rule {
    verbs             = ["*"]
    non_resource_urls = ["*"]
  }
}

resource "kubernetes_deployment" "memcached" {
  metadata {
    name      = "memcached"
    namespace = "${local.flux_namespace}"
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        name = "memcached"
      }
    }

    template {
      metadata {
        labels = {
          name = "memcached"
        }
      }

      spec {
        automount_service_account_token = true
        container {
          name  = "memcached"
          image = "memcached:1.5.15"
          args  = ["-m 512", "-I 5m", "-p 11211"]

          port {
            name           = "clients"
            container_port = 11211
          }

          image_pull_policy = "IfNotPresent"

          security_context {
            run_as_user  = 11211
            run_as_group = 11211
          }
        }
      }
    }
  }
}

resource "kubernetes_service" "memcached" {
  metadata {
    name      = "memcached"
    namespace = "${local.flux_namespace}"
  }

  spec {
    port {
      name = "memcached"
      port = 11211
    }

    selector = {
      name = "memcached"
    }
  }
}

resource "kubernetes_deployment" "flux" {

  depends_on = [
    "null_resource.flux_image",
    "kubernetes_config_map.flux_git_config",
    "kubernetes_config_map.flux_ssh_config",
    "kubernetes_service_account.flux_service_account"
  ]

  metadata {
    name      = "flux"
    namespace = "${local.flux_namespace}"
  }

  spec {
    replicas = 1

    selector {
      match_labels = {
        name = "flux"
      }
    }

    template {

      metadata {
        labels = {
          name = "flux"
        }

        annotations = {
          "prometheus.io/port" = "3031"
        }
      }

      spec {
        volume {
          name = "git-key"

          secret {
            secret_name  = "flux-git-deploy"
            default_mode = "0400"
          }
        }

        volume {
          name = "git-keygen"

          empty_dir {
            medium = "Memory"
          }
        }

        volume {
          name = "ssh-config"

          config_map {
            name         = "flux-ssh-config"
            default_mode = "0644"
          }
        }

        volume {
          name = "git-config"

          config_map {
            name         = "flux-git-config"
            default_mode = "0644"
          }
        }

        automount_service_account_token = true

        container {
          name  = "flux"
          image = "${aws_ecr_repository.flux_with_awscli.repository_url}:${local.flux_version}"
          args  = [
            "--memcached-service=", 
            "--ssh-keygen-dir=/var/fluxd/keygen", 
            "--git-url=$(GIT_URL)", 
            "--git-branch=master", 
            "--git-path=namespaces,workloads", 
            "--git-label=flux", 
            "--git-user=Flux", 
            "--git-email=Flux", 
            "--listen-metrics=:3031",
            "--sync-garbage-collection"]

          port {
            container_port = 3030
            protocol       = "TCP"
          }

          env {
            name = "GIT_URL"

            value_from {
              config_map_key_ref {
                name = "flux-git-config"
                key  = "giturl"
              }
            }
          }

          resources {
            requests {
              cpu    = "50m"
              memory = "64Mi"
            }
          }

          volume_mount {
            name       = "git-key"
            read_only  = true
            mount_path = "/etc/fluxd/ssh"
          }

          volume_mount {
            name       = "git-keygen"
            mount_path = "/var/fluxd/keygen"
          }

          volume_mount {
            name       = "ssh-config"
            mount_path = "/root/.ssh"
          }

          volume_mount {
            name       = "git-config"
            mount_path = "/root/.gitconfig"
            sub_path   = "gitconfig"
          }

          liveness_probe {
            http_get {
              path   = "/api/flux/v6/identity.pub"
              port   = "3030"
              scheme = "HTTP"
            }

            initial_delay_seconds = 5
            timeout_seconds       = 5
            period_seconds        = 10
            success_threshold     = 1
            failure_threshold     = 3
          }

          readiness_probe {
            http_get {
              path   = "/api/flux/v6/identity.pub"
              port   = "3030"
              scheme = "HTTP"
            }

            initial_delay_seconds = 5
            timeout_seconds       = 5
            period_seconds        = 10
            success_threshold     = 1
            failure_threshold     = 3
          }

          termination_message_path = "/dev/termination-log"
          image_pull_policy        = "IfNotPresent"
        }

        restart_policy                   = "Always"
        termination_grace_period_seconds = 30
        dns_policy                       = "ClusterFirst"
        service_account_name             = "${local.flux_service_account}"
      }
    }

    strategy {
      type = "Recreate"
    }

    revision_history_limit    = 10
    progress_deadline_seconds = 600
  }
}