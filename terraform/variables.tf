variable "aws_region" {
  description = "AWS region for all resources"
  type        = string
  default     = "us-west-2"
}

variable "project_name" {
  description = "Prefix used for naming all resources"
  type        = string
  default     = "self-healing-k8s"
}

variable "cluster_version" {
  description = "EKS Kubernetes version"
  type        = string
  default     = "1.31"
}

variable "vpc_cidr" {
  description = "CIDR block for the VPC"
  type        = string
  default     = "10.20.0.0/16"
}

# Two AZs, one public + one private subnet each = 4 subnets total.
# Kept intentionally small: enough for a real EKS cluster with private
# worker nodes, without the cost/complexity of a 3-AZ production layout.
variable "availability_zones" {
  description = "AZs to spread subnets across"
  type        = list(string)
  default     = ["us-west-2a", "us-west-2b"]
}

variable "node_instance_type" {
  description = "EC2 instance type for EKS worker nodes"
  type        = string
  default     = "t3.micro"
}

# Small, cost-conscious node group: min 1 keeps costs low when idle,
# max 3 gives headroom to demo HPA / node pressure scenarios.
variable "node_min_size" {
  type    = number
  default = 1
}
variable "node_max_size" {
  type    = number
  default = 3
}
variable "node_desired_size" {
  type    = number
  default = 2
}

variable "github_org" {
  description = "GitHub org/user that owns the repo (for OIDC trust policy)"
  type        = string
}

variable "github_repo" {
  description = "GitHub repo name (for OIDC trust policy)"
  type        = string
}
