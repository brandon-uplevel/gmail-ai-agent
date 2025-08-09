# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains a comprehensive guide for building a Gmail AI Agent on Google Cloud Platform. The project demonstrates a complete end-to-end machine learning system that:

- Extracts emails from Gmail using the Gmail API
- Classifies emails as "Prospect" or "Customer" using AutoML
- Automatically applies labels to incoming emails via Cloud Functions

## Architecture

The system consists of several key phases:

1. **Google Cloud Project Setup**: Environment configuration and API enablement
2. **Data Extraction & Labeling**: Gmail API integration with heuristic-based labeling
3. **Data Storage**: BigQuery for structured data and Cloud Storage for artifacts
4. **ML Pipeline**: Vertex AI AutoML for text classification training
5. **Model Deployment**: Vertex AI endpoints for real-time predictions
6. **Agent Deployment**: Cloud Functions triggered by Pub/Sub for email processing
7. **Gmail Integration**: Watch API for real-time email notifications

## Key Components

### Authentication & APIs
- Gmail API with OAuth2 flow for email access
- Google Cloud Application Default Credentials
- Service account domain-wide delegation for production

### Data Pipeline
- `extract_emails.py`: Gmail data extraction with heuristic labeling
- BigQuery tables for training data storage
- Cloud Storage for pipeline artifacts and model storage

### Machine Learning
- Vertex AI AutoML Text Classification
- Vertex AI Pipelines for automated training workflows
- Model deployment to managed endpoints

### Production Agent
- Cloud Functions for real-time email processing
- Pub/Sub for Gmail push notifications
- Automated label application based on ML predictions

## Required External Setup

### Google Cloud Console
1. Enable required APIs (Gmail, Vertex AI, Cloud Functions, etc.)
2. Create OAuth2 credentials for desktop application
3. Configure service account with domain-wide delegation

### Gmail Configuration
1. Create labels: "AI-Prospect" and "AI-Customer"
2. Grant Gmail API access to service accounts
3. Configure Gmail push notifications

### Google Workspace Admin
1. Domain-wide delegation for service accounts
2. OAuth scope authorization for Gmail modification

## Development Workflow

This is a tutorial-based project with sequential phases that must be completed in order:

1. **Setup Phase**: Configure GCP project and authentication
2. **Data Collection**: Extract historical Gmail data
3. **Training Phase**: Build and run ML pipeline in Vertex AI Workbench
4. **Deployment Phase**: Deploy model and Cloud Function
5. **Activation Phase**: Enable Gmail watch notifications

## Important Notes

- No traditional package managers (no package.json, requirements.txt in root)
- Code examples are embedded within the PROJECT.md documentation
- Each phase requires manual configuration in Google Cloud Console
- Authentication involves multiple OAuth flows and service account setup
- Production deployment requires Google Workspace admin privileges

## Security Considerations

- OAuth2 credentials and tokens are stored locally during development
- Service accounts require carefully scoped Gmail API permissions
- Domain-wide delegation requires Google Workspace admin access
- All email data processing occurs within Google Cloud infrastructure