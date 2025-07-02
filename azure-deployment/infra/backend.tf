terraform {
  backend "azurerm" {
    resource_group_name  = "terraform-state-rg"
    storage_account_name = "terraformstate123"
    container_name       = "tfstate"
    key                  = "infra.tfstate"
  }
}
