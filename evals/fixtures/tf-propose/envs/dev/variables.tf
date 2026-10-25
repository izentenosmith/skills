variable "vpc_id" {
  type        = string
  description = "VPC for the orders service."
}

variable "databases" {
  type        = list(string)
  description = "Logical databases, one RDS instance each."
}

variable "db_password" {
  type        = string
  description = "Master password for the RDS instances."
}
