output "security_group_id" {
  description = "ID of the application security group, for rules that admit app traffic."
  value       = aws_security_group.app.id
}
