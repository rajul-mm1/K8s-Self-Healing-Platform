output "cluster_name" {
  value = local.cluster_name
}

output "cluster_endpoint" {
  value = aws_eks_cluster.this.endpoint
}

output "ecr_backend_repo_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_repo_url" {
  value = aws_ecr_repository.frontend.repository_url
}

output "ecr_remediation_repo_url" {
  value = aws_ecr_repository.remediation.repository_url
}

output "github_actions_role_arn" {
  description = "Put this in the GitHub Actions workflow's AWS role-to-assume"
  value       = aws_iam_role.github_actions.arn
}

output "configure_kubectl" {
  value = "aws eks update-kubeconfig --region ${var.aws_region} --name ${local.cluster_name}"
}
