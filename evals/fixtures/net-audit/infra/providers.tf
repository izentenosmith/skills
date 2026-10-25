terraform {
  required_version = "~> 1.9"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.10"
    }
  }
  backend "azurerm" {
    resource_group_name  = "rg-tfstate"
    storage_account_name = "nwtfstate01"
    container_name       = "tfstate"
    key                  = "network.tfstate"
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "net" {
  name     = "rg-network-weu"
  location = "westeurope"
}
