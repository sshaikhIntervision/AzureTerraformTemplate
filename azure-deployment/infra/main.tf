provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

resource "azurerm_resource_group" "ai" {
  name     = "ai"
  location = var.location
}

resource "azurerm_resource_group" "feedbackhandler_group" {
  name     = "feedbackhandler_group"
  location = var.location
}

resource "azurerm_resource_group" "readuploaddoc_group" {
  name     = "readuploaddoc_group"
  location = var.location
}

resource "azurerm_service_plan" "ASP_AI" {
  for_each = toset([
    "89bf", "9a62", "a71e", "a8b0", "ab8a", "b154", "bdc1"
  ])

  name                = "ASP-AI-${each.key}"
  resource_group_name = azurerm_resource_group.ai.name
  location            = var.location
  sku_name            = "S1"
  os_type             = "Linux"
}

resource "azurerm_service_plan" "ASP_FeedbackHandler" {
  name                = "ASP-FeedbackHandlergroup-b6e7"
  resource_group_name = azurerm_resource_group.feedbackhandler_group.name
  location            = var.location
  sku_name            = "S1"
  os_type             = "Linux"
}

resource "azurerm_service_plan" "ASP_ReadUploadDoc" {
  name                = "ASP-ReadUploadDocgroup-937e"
  resource_group_name = azurerm_resource_group.readuploaddoc_group.name
  location            = var.location
  sku_name            = "S1"
  os_type             = "Linux"
}

resource "azurerm_storage_account" "storage" {
  for_each = {
    "brinkmannbotui"         = azurerm_resource_group.ai,
    "brinkmannstorage"       = azurerm_resource_group.ai,
    "feedbackhandlergroub5d1" = azurerm_resource_group.feedbackhandler_group,
    "readuploaddocgroupb1c2" = azurerm_resource_group.readuploaddoc_group
  }

  name                     = each.key
  resource_group_name      = each.value.name
  location                 = var.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_linux_function_app" "function" {
  for_each = {
    "ChatAssistantHandler"       = azurerm_service_plan.ASP_AI["89bf"],
    "ChatRetrieveFunction"       = azurerm_service_plan.ASP_AI["9a62"],
    "ChatSessionRetreival"       = azurerm_service_plan.ASP_AI["a71e"],
    "ChatTransactionHandler"     = azurerm_service_plan.ASP_AI["a8b0"],
    "DeleteChatHandler"          = azurerm_service_plan.ASP_AI["ab8a"],
    "FeedbackHandler"            = azurerm_service_plan.ASP_FeedbackHandler,
    "ReadUploadDoc"              = azurerm_service_plan.ASP_ReadUploadDoc,
    "SharepointPlugin"           = azurerm_service_plan.ASP_AI["b154"],
    "Sharpoint_Scrape_Sites"     = azurerm_service_plan.ASP_AI["bdc1"],
    "UpdateChatlogsDB"           = azurerm_service_plan.ASP_AI["bdc1"]
  }

  name                       = each.key
  resource_group_name        = azurerm_resource_group.ai.name
  location                   = var.location
  app_service_plan_id        = each.value.id
  storage_account_name       = azurerm_storage_account.storage[each.key].name
  storage_account_access_key = azurerm_storage_account.storage[each.key].primary_access_key
}

resource "azurerm_application_insights" "app_insights" {
  for_each = {
    "ChatRetrieveFunction"       = azurerm_resource_group.ai,
    "ChatSessionRetreival"       = azurerm_resource_group.ai,
    "ChatTransactionHandler"     = azurerm_resource_group.ai,
    "DeleteChatHandler"          = azurerm_resource_group.ai,
    "FeedbackHandler"            = azurerm_resource_group.feedbackhandler_group,
    "ReadUploadDoc"              = azurerm_resource_group.readuploaddoc_group,
    "SharepointPlugin"           = azurerm_resource_group.ai,
    "Sharpoint_Scrape_Sites"     = azurerm_resource_group.ai,
    "UpdateChatlogsDB"           = azurerm_resource_group.ai
  }

  name                = each.key
  resource_group_name = each.value.name
  location            = var.location
  application_type    = "web"
}

resource "azurerm_cosmosdb_account" "construction_cluster" {
  name                = "construction-cluster"
  resource_group_name = azurerm_resource_group.ai.name
  location            = var.location
  offer_type          = "Standard"
  kind                = "GlobalDocumentDB"
  consistency_policy {
    consistency_level = "Session"
  }
  geo_location {
    location          = var.location
    failover_priority = 0
  }
}

resource "azurerm_search_service" "construction_bot" {
  name                = "construction-bot"
  resource_group_name = azurerm_resource_group.ai.name
  location            = var.location
  sku                 = "standard"
}
