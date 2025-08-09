# Gmail AI Agent Project

This project builds an AI-powered email classification system that automatically labels incoming Gmail emails as Customer, Prospect, Internal, or Other using Google Cloud Platform services.

## Architecture

- **Gmail API**: Extract historical emails and receive real-time notifications
- **BigQuery**: Store and analyze email data 
- **Vertex AI AutoML**: Train text classification model
- **Cloud Functions**: Process new emails in real-time
- **Pub/Sub**: Handle Gmail push notifications

## Project Structure

```
gmail-agent-project/
├── extract_emails.py              # Original email extraction script
├── extract_emails_v2.py           # Enhanced extraction with 4 labels  
├── extract_emails_to_bigquery.py  # Direct extraction to BigQuery
├── customer_domains.txt           # Customer domain heuristics
├── prospect_keywords.txt          # Prospect keyword patterns
├── customers.txt                  # Customer email list (not in git)
└── venv/                          # Python virtual environment
```

## Setup Instructions

### Prerequisites

1. Google Cloud Project with billing enabled
2. Gmail account to analyze
3. Python 3.8+

### Phase 1: Google Cloud Setup

```bash
# Set environment variables
export PROJECT_ID="your-project-id"
export REGION="us-central1"

# Enable required APIs
gcloud services enable iam.googleapis.com cloudresourcemanager.googleapis.com storage.googleapis.com bigquery.googleapis.com aiplatform.googleapis.com cloudfunctions.googleapis.com cloudbuild.googleapis.com pubsub.googleapis.com gmail.googleapis.com

# Authenticate
gcloud auth application-default login
```

### Phase 2: Data Extraction

1. Create OAuth2 credentials in Google Cloud Console
2. Download credentials.json to project directory
3. Install dependencies:

```bash
cd gmail-agent-project
python -m venv venv
source venv/bin/activate
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib google-cloud-bigquery
```

4. Run extraction to BigQuery:

```bash
python extract_emails_to_bigquery.py
```

### Phase 3: Data Labeling in BigQuery

The extraction creates a table with metadata flags that can be used for labeling:

- `is_sent_by_me`: Email was sent by you
- `is_from_no_reply`: Email from no-reply addresses  
- `has_pipe_separator`: Subject contains " | " (lead notifications)
- `has_new_lead`: Subject contains "new lead"

### Phase 4: Model Training

Train AutoML model using Vertex AI with labeled data from BigQuery.

### Phase 5: Deploy Agent

Deploy Cloud Function that processes new emails and applies labels automatically.

## Security Notes

- OAuth credentials and email data are excluded from git
- All processing occurs within Google Cloud infrastructure
- Service accounts require careful Gmail API permission scoping

## Development Status

- ✅ Gmail API integration and authentication
- ✅ Email extraction with metadata flags
- ✅ BigQuery data storage and analysis
- 🔄 SQL-based email labeling (in progress)
- ⏳ Vertex AI model training
- ⏳ Cloud Function deployment
- ⏳ Gmail watch notifications

## Important Files Not in Git

These files contain sensitive data and must be created locally:

- `credentials.json` - OAuth2 credentials from Google Cloud Console
- `customers.txt` - Customer email addresses and domains
- `token.json` - Gmail API access tokens (auto-generated)
- `*.csv` - Email data files

## Next Steps

1. Complete email labeling using BigQuery SQL queries
2. Export labeled dataset for ML training
3. Create Vertex AI AutoML pipeline
4. Deploy production Cloud Function
5. Activate Gmail push notifications