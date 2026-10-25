terraform {
  backend "s3" {
    bucket = "acme-orders-tfstate"
    key    = "orders/terraform.tfstate"
    region = "eu-west-1"
  }
}
