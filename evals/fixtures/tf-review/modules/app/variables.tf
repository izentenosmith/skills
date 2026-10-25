variable "name" {
  type        = string
  description = "Service name, used as the prefix for every resource this module creates."
}

variable "environment" {
  type        = string
  description = "Environment the service runs in (dev, prod)."

  validation {
    condition     = contains(["dev", "prod"], var.environment)
    error_message = "environment must be dev or prod."
  }
}

variable "vpc_id" {
  type        = string
  description = "VPC the service's security groups are created in."
}

variable "instance_count" {
  type        = number
  description = "Number of application instances behind the load balancer."
  default     = 2
}
