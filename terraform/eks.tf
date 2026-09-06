# Small, cost-conscious EKS cluster:
# Control plane + one managed node group
# across the private subnets.
# No Fargate, no multiple node groups.

# ---------------------------------------------------------
# EKS Cluster IAM Role
# ---------------------------------------------------------

resource "aws_iam_role" "eks_cluster" {
  name = "${var.project_name}-eks-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Principal = {
          Service = "eks.amazonaws.com"
        }

        Action = "sts:AssumeRole"
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  role       = aws_iam_role.eks_cluster.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
}


# ---------------------------------------------------------
# EKS Cluster
# ---------------------------------------------------------

resource "aws_eks_cluster" "this" {
  name     = local.cluster_name
  version  = var.cluster_version
  role_arn = aws_iam_role.eks_cluster.arn

  # Enable EKS Access Entries.
  # API_AND_CONFIG_MAP keeps compatibility with the
  # traditional aws-auth ConfigMap as well.
  access_config {
    authentication_mode = "API_AND_CONFIG_MAP"
      bootstrap_cluster_creator_admin_permissions = true

  }

  vpc_config {
    subnet_ids = concat(
      values(aws_subnet.public)[*].id,
      values(aws_subnet.private)[*].id
    )

    endpoint_public_access  = true
    endpoint_private_access = true
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_cluster_policy
  ]

  tags = local.common_tags
}


# ---------------------------------------------------------
# OIDC Provider for IRSA
# Used by Kubernetes workloads that need AWS IAM access.
# ---------------------------------------------------------

data "tls_certificate" "eks" {
  url = aws_eks_cluster.this.identity[0].oidc[0].issuer
}

resource "aws_iam_openid_connect_provider" "eks" {
  url = aws_eks_cluster.this.identity[0].oidc[0].issuer

  client_id_list = [
    "sts.amazonaws.com"
  ]

  thumbprint_list = [
    data.tls_certificate.eks.certificates[0].sha1_fingerprint
  ]
}


# ---------------------------------------------------------
# EKS Node IAM Role
# ---------------------------------------------------------

resource "aws_iam_role" "eks_nodes" {
  name = "${var.project_name}-eks-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"

    Statement = [
      {
        Effect = "Allow"

        Principal = {
          Service = "ec2.amazonaws.com"
        }

        Action = "sts:AssumeRole"
      }
    ]
  })
}


# ---------------------------------------------------------
# Node IAM Policies
# ---------------------------------------------------------

resource "aws_iam_role_policy_attachment" "eks_nodes_worker" {
  role       = aws_iam_role.eks_nodes.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
}

resource "aws_iam_role_policy_attachment" "eks_nodes_cni" {
  role       = aws_iam_role.eks_nodes.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
}

resource "aws_iam_role_policy_attachment" "eks_nodes_ecr" {
  role       = aws_iam_role.eks_nodes.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}


# ---------------------------------------------------------
# EKS Managed Node Group
# ---------------------------------------------------------

resource "aws_eks_node_group" "default" {
  cluster_name    = aws_eks_cluster.this.name
  node_group_name = "${var.project_name}-default-ng"
  node_role_arn   = aws_iam_role.eks_nodes.arn

  subnet_ids = values(aws_subnet.private)[*].id

  # EKS-optimized Amazon Linux 2023 AMI
  ami_type = "AL2023_x86_64_STANDARD"

  instance_types = [
    var.node_instance_type
  ]

  capacity_type = "ON_DEMAND"

  scaling_config {
    min_size     = var.node_min_size
    max_size     = var.node_max_size
    desired_size = var.node_desired_size
  }

  update_config {
    max_unavailable = 1
  }

  depends_on = [
    aws_iam_role_policy_attachment.eks_nodes_worker,
    aws_iam_role_policy_attachment.eks_nodes_cni,
    aws_iam_role_policy_attachment.eks_nodes_ecr
  ]

  tags = local.common_tags
}