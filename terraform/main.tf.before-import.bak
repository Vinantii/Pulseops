terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

provider "aws" {
  region = "us-east-1"
}

variable "instance_id" {
  description = "Existing PulseOps EC2 instance ID"
  type        = string
  default     = "i-0c0f836a10abb36ce"
}

# Read the existing instance without changing it.
data "aws_instance" "pulseops" {
  instance_id = var.instance_id
}

output "instance_id" {
  value = data.aws_instance.pulseops.id
}

output "instance_type" {
  value = data.aws_instance.pulseops.instance_type
}

output "instance_state" {
  value = data.aws_instance.pulseops.instance_state
}

output "availability_zone" {
  value = data.aws_instance.pulseops.availability_zone
}

data "aws_subnet" "pulseops" {
  id = data.aws_instance.pulseops.subnet_id
}

output "subnet_id" {
  value = data.aws_instance.pulseops.subnet_id
}

output "private_ip" {
  value = data.aws_instance.pulseops.private_ip
}

output "public_ip" {
  value = data.aws_instance.pulseops.public_ip
}

output "security_group_ids" {
  value = data.aws_instance.pulseops.vpc_security_group_ids
}
