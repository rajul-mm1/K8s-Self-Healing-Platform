resource "aws_ecr_repository" "frontend" {
  name                 = "todo-frontend"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  tags = local.common_tags
}

resource "aws_ecr_repository" "backend" {
  name                 = "todo-backend"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  tags = local.common_tags
}

resource "aws_ecr_repository" "remediation" {
  name                 = "remediation-engine"
  image_tag_mutability = "MUTABLE"
  image_scanning_configuration { scan_on_push = true }
  tags = local.common_tags
}

# Keep only the last 10 images per repo to control storage cost.
resource "aws_ecr_lifecycle_policy" "cleanup" {
  for_each = {
    frontend    = aws_ecr_repository.frontend.name
    backend     = aws_ecr_repository.backend.name
    remediation = aws_ecr_repository.remediation.name
  }
  repository = each.value
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = { type = "expire" }
    }]
  })
}
