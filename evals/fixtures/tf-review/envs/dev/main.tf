provider "aws" {
  region = "eu-west-1"

  default_tags {
    tags = {
      Service     = "orders"
      Environment = "dev"
      Owner       = "team-orders"
    }
  }
}

module "app" {
  source      = "git::https://github.com/acme/terraform-modules.git//app?ref=main"
  name        = "orders"
  environment = "dev"
  vpc_id      = var.vpc_id
}

resource "aws_security_group" "db" {
  name_prefix = "orders-dev-db-"
  vpc_id      = var.vpc_id
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
  identifier             = "orders-dev-${var.databases[count.index]}"
  engine                 = "postgres"
  engine_version         = "16.3"
  instance_class         = "db.t4g.small"
  allocated_storage      = 20
  username               = "orders"
  password               = var.db_password
  storage_encrypted      = true
  skip_final_snapshot    = true
  vpc_security_group_ids = [aws_security_group.db.id]
}
