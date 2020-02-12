# Backend setup
terraform {
  backend "s3" {
    key = "eks-base.tfstate"
  }
}

# Variable definitions
variable "region" {}
variable "kubectl-access-role-arn" {}
variable "vpc-cidr" { default = "10.0.64.0/18" }
variable "az-count" { default = 3 }

# Provider and access setup
provider "aws" {
  version = "~> 2.43"
  region = "${var.region}"
}
provider "external" {
  version = "~> 1.2"
}

# Data and resources
data "aws_region" "current" {}
data "aws_availability_zones" "available" {}

locals {
  # This cluster name is also used in the next runway module to create the local
  # kubeconfig; if updated here make sure to update that module as well
  cluster_name = "k8s-${terraform.workspace}"
}

module "vpc" {
  source = "terraform-aws-modules/vpc/aws"
  version = "~> 2.15.0"

  name = "${local.cluster_name}"
  cidr = "${var.vpc-cidr}"

  azs = [
    for num in range(var.az-count):
    "${data.aws_availability_zones.available.names[num]}"
  ]
  private_subnets = [
    for num in range(0, var.az-count):
    cidrsubnet(var.vpc-cidr, 6, num)
  ]
  public_subnets = [
    for num in range(var.az-count, var.az-count * 2):
    cidrsubnet(var.vpc-cidr, 6, num)
  ]

  enable_nat_gateway = true

  tags = "${
    map(
     "kubernetes.io/cluster/${local.cluster_name}", "shared",
     "Environment", "${terraform.workspace}",
     "Terraform", "true"
    )
  }"
}

data "aws_iam_policy_document" "cluster-assume-role-policy" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["eks.amazonaws.com"]
    }
  }
}
resource "aws_iam_role" "cluster" {
  name_prefix = "eks-cluster-"

  assume_role_policy = "${data.aws_iam_policy_document.cluster-assume-role-policy.json}"
}
resource "aws_iam_role_policy_attachment" "cluster-AmazonEKSClusterPolicy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = "${aws_iam_role.cluster.name}"
}
resource "aws_iam_role_policy_attachment" "cluster-AmazonEKSServicePolicy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSServicePolicy"
  role       = "${aws_iam_role.cluster.name}"
}

resource "aws_security_group" "cluster" {
  name_prefix = "eks-cluster-"
  description = "Cluster communication with worker nodes"
  vpc_id = "${module.vpc.vpc_id}"

  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

data "aws_iam_policy_document" "node-assume-role-policy" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["ec2.amazonaws.com"]
    }
  }
}
resource "aws_iam_role" "node" {
  name_prefix = "eks-node-"

  assume_role_policy = "${data.aws_iam_policy_document.node-assume-role-policy.json}"
}
resource "aws_iam_role_policy_attachment" "node-AmazonEKSWorkerNodePolicy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role = "${aws_iam_role.node.name}"
}
resource "aws_iam_role_policy_attachment" "node-AmazonEKS_CNI_Policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role = "${aws_iam_role.node.name}"
}
resource "aws_iam_role_policy_attachment" "node-AmazonEC2ContainerRegistryReadOnly" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role = "${aws_iam_role.node.name}"
}
# SSM agent not shipped ootb
# resource "aws_iam_role_policy_attachment" "node-AmazonSSMManagedInstanceCore" {
#   policy_arn = "arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore"
#   role = "${aws_iam_role.node.name}"
# }
resource "aws_iam_instance_profile" "node" {
  role = "${aws_iam_role.node.name}"
}

resource "aws_security_group" "node" {
  name_prefix = "eks-node-"
  description = "Security group for all nodes in the cluster"
  vpc_id = "${module.vpc.vpc_id}"

  egress {
    from_port = 0
    to_port = 0
    protocol = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = "${
    map(
     "kubernetes.io/cluster/${local.cluster_name}", "owned",
    )
  }"
}
resource "aws_security_group_rule" "node-ingress-self" {
  description = "Allow node to communicate with each other"
  from_port = 0
  protocol = "-1"
  security_group_id = "${aws_security_group.node.id}"
  source_security_group_id = "${aws_security_group.node.id}"
  to_port = 65535
  type = "ingress"
}

resource "aws_security_group_rule" "node-ingress-cluster" {
  description = "Allow worker Kubelets and pods to receive communication from the cluster control plane"
  from_port = 1025
  protocol = "tcp"
  security_group_id = "${aws_security_group.node.id}"
  source_security_group_id = "${aws_security_group.cluster.id}"
  to_port = 65535
  type = "ingress"
}
resource "aws_security_group_rule" "cluster-ingress-node-https" {
  description = "Allow pods to communicate with the cluster API Server"
  from_port = 443
  protocol = "tcp"
  security_group_id = "${aws_security_group.cluster.id}"
  source_security_group_id = "${aws_security_group.node.id}"
  to_port = 443
  type = "ingress"
}

resource "aws_eks_cluster" "cluster" {
  name = "${local.cluster_name}"
  role_arn = "${aws_iam_role.cluster.arn}"

  vpc_config {
    security_group_ids = ["${aws_security_group.cluster.id}"]
    subnet_ids = "${module.vpc.private_subnets[*]}"
  }

  # version doesn't need to be specified until it's time to upgrade
  # version = ""

  depends_on = [
    "aws_iam_role_policy_attachment.cluster-AmazonEKSClusterPolicy",
    "aws_iam_role_policy_attachment.cluster-AmazonEKSServicePolicy",
    "module.vpc.natgw_ids",  # would be better to just depend on the entire module, if it were possible
  ]

  # API will timeout on initial connection attempts (i.e. when using the config_map 
  # resource below). Wait here for 2 minutes to ensure it is available.
  provisioner "local-exec" {
    command = "runway run-python sleep.py"
  }
}

data "aws_eks_cluster_auth" "cluster_auth" {
  name = "${aws_eks_cluster.cluster.id}"
}

provider "kubernetes" {
  host = "${aws_eks_cluster.cluster.endpoint}"
  cluster_ca_certificate = "${base64decode(aws_eks_cluster.cluster.certificate_authority.0.data)}"
  token = "${data.aws_eks_cluster_auth.cluster_auth.token}"
  load_config_file = false
  # Pinned back from 1.11 pending resolution of:
  # https://github.com/terraform-providers/terraform-provider-kubernetes/issues/759
  version = "~> 1.10.0"
}

resource "kubernetes_config_map" "aws_auth_configmap" {
  metadata {
    name      = "aws-auth"
    namespace = "kube-system"
  }
  data = {
    mapRoles = <<YAML
- rolearn: ${aws_iam_role.node.arn}
  username: system:node:{{EC2PrivateDNSName}}
  groups:
    - system:bootstrappers
    - system:nodes
- rolearn: ${var.kubectl-access-role-arn}
  username: kubectl-access-user
  groups:
    - system:masters
YAML
  }
}

resource "aws_eks_node_group" "node" {
  cluster_name = aws_eks_cluster.cluster.name
  node_group_name = "base"
  node_role_arn = aws_iam_role.node.arn
  subnet_ids = module.vpc.private_subnets[*]

  scaling_config {
    desired_size = 1
    max_size = 1
    min_size = 1
  }

  # Ensure that IAM Role permissions are created before and deleted after EKS Node Group handling.
  # Otherwise, EKS will not be able to properly delete EC2 Instances and Elastic Network Interfaces.
  depends_on = [
    aws_iam_role_policy_attachment.node-AmazonEKSWorkerNodePolicy,
    aws_iam_role_policy_attachment.node-AmazonEKS_CNI_Policy,
    aws_iam_role_policy_attachment.node-AmazonEC2ContainerRegistryReadOnly,
    kubernetes_config_map.aws_auth_configmap,
  ]
}

# Need an external script for this for now
# https://github.com/terraform-providers/terraform-provider-aws/issues/10104
# https://github.com/terraform-providers/terraform-provider-tls/issues/52
data "external" "cluster-cert-thumbprint" {
  program = ["runway", "run-python", "get_idp_root_cert_thumbprint.py"]

  query = {
    url = "${aws_eks_cluster.cluster.identity.0.oidc.0.issuer}"
  }
}
resource "aws_iam_openid_connect_provider" "cluster" {
  client_id_list = ["sts.amazonaws.com"]
  thumbprint_list = ["${data.external.cluster-cert-thumbprint.result.thumbprint}"]
  url = "${aws_eks_cluster.cluster.identity.0.oidc.0.issuer}"
}

resource "aws_ssm_parameter" "oidc_iam_provider_cluster_url" {
  name = "/${local.cluster_name}/oidc-iam-provider-cluster-url"
  type = "String"
  value = "${aws_iam_openid_connect_provider.cluster.url}"
}
resource "aws_ssm_parameter" "oidc_iam_provider_cluster_arn" {
  name = "/${local.cluster_name}/oidc-iam-provider-cluster-arn"
  type = "String"
  value = "${aws_iam_openid_connect_provider.cluster.arn}"
}
