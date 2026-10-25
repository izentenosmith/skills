provider "aws" {
  region     = "eu-west-1"
  access_key = "AKIAEVALFAKEKEY00001"
  secret_key = "evalFakeSecretKey/DoNotUse/0000000000000000"

  default_tags {
    tags = {
      Service     = "orders"
      Environment = "prod"
      Owner       = "team-orders"
    }
  }
}

module "app" {
  source         = "git::https://github.com/acme/terraform-modules.git//app?ref=main"
  name           = "orders"
  environment    = "prod"
  vpc_id         = var.vpc_id
  instance_count = 4
}

resource "aws_security_group" "db" {
  name_prefix = "orders-prod-db-"
  vpc_id      = var.vpc_id
}

# Temporary: lets the analytics vendor connect while their VPN is being set up.
resource "aws_vpc_security_group_ingress_rule" "db_vendor" {
  security_group_id = aws_security_group.db.id
  from_port         = 5432
  to_port           = 5432
  ip_protocol       = "tcp"
  cidr_ipv4         = "0.0.0.0/0"
}

resource "aws_vpc_security_group_ingress_rule" "db_from_app" {
  security_group_id            = aws_security_group.db.id
  from_port                    = 5432
  to_port                      = 5432
  ip_protocol                  = "tcp"
  referenced_security_group_id = module.app.security_group_id
}

resource "aws_db_instance" "db" {
  count                  = length(var.databases)
  identifier             = "orders-prod-${var.databases[count.index]}"
  engine                 = "postgres"
  engine_version         = "16.3"
  instance_class         = "db.r6g.large"
  allocated_storage      = 200
  username               = "orders"
  password               = var.db_password
  skip_final_snapshot    = true
  deletion_protection    = false
  vpc_security_group_ids = [aws_security_group.db.id]
}
