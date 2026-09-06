terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.60"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
    }
  }

  # Uncomment and configure for team use / remote state locking.
  # backend "s3" {
  #   bucket = "your-terraform-state-bucket"
  #   key    = "self-healing-k8s/terraform.tfstate"
  #   region = "ap-south-1"
  # }
}

provider "aws" {
  region = var.aws_region
}
