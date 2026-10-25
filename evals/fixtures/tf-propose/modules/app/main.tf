resource "aws_security_group" "app" {
  name_prefix = "${var.name}-${var.environment}-app-"
  vpc_id      = var.vpc_id
  description = "Application tier for ${var.name}"

  lifecycle {
    create_before_destroy = true
  }
}

resource "aws_vpc_security_group_ingress_rule" "app_from_lb" {
  security_group_id = aws_security_group.app.id
  description       = "HTTP from the load balancer only"
  from_port         = 8080
  to_port           = 8080
  ip_protocol       = "tcp"
  cidr_ipv4         = "10.20.0.0/24"
}

resource "aws_vpc_security_group_egress_rule" "app_https" {
  security_group_id = aws_security_group.app.id
  description       = "HTTPS egress for package mirrors and AWS APIs"
  from_port         = 443
  to_port           = 443
  ip_protocol       = "tcp"
  cidr_ipv4         = "0.0.0.0/0"
}
