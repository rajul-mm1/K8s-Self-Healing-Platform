locals {
  cluster_name = "${var.project_name}-eks"
  common_tags = {
    Project   = var.project_name
    ManagedBy = "terraform"
  }
}
