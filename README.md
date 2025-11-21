# Azure Terraform Template - Chat AI Infrastructure

This repository contains Terraform infrastructure-as-code for deploying a chat AI system on Azure.

## Infrastructure Components
- **10 Azure Functions**: ChatAssistantHandler, ChatRetrieveFunction, ChatSessionRetreival, ChatTransactionHandler, DeleteChatHandler, FeedbackHandler, ReadUploadDoc, SharepointPlugin, Sharpoint_Scrape_Sites, UpdateChatlogsDB
- **Cosmos DB**: construction-cluster database for persistent storage
- **Azure Cognitive Search**: construction-bot search service for document indexing
- **Application Insights**: Monitoring and telemetry for function apps
- **Storage Accounts**: Blob storage for function apps and data persistence
- **Service Plans**: Linux-based S1 tier App Service Plans for hosting functions

## Quick Start
Run `terraform init`, `terraform plan`, and `terraform apply` from the `azure-deployment/infra` directory to deploy all resources.
