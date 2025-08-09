# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository builds a Gmail AI Agent that automatically classifies incoming emails using Google Cloud Platform. The system extracts historical Gmail data, trains an ML model, and deploys a real-time classification agent.

**Current Classification Labels:**
- **Customer**: Emails from known customers
- **Internal**: Company internal communications (@getuplevel.ai, @upleveldigitalservices.com)
- **Prospect**: Potential customers with inquiry keywords
- **Other**: Everything else

## Current Project Status (as of Aug 8, 2025)

### ✅ Completed
1. GCP project setup (project ID: `account-strategy-464106`)
2. All required APIs enabled
3. OAuth2 authentication configured
4. BigQuery dataset and table created (`gmail_agent_dataset.emails_raw`)
5. Three extraction scripts developed:
   - `extract_emails.py`: Original 2-label version
   - `extract_emails_v2.py`: 4-label version with heuristics
   - `extract_emails_to_bigquery.py`: Direct to BigQuery with metadata flags
6. GitHub repository created: https://github.com/brandon-uplevel/gmail-ai-agent

### 🔄 In Progress
- Email extraction to BigQuery running (37K+ emails processed, continuing in background)
- Process ID can be found with: `ps aux | grep extract_emails_to_bigquery`

### ⏳ Next Steps
1. Complete email extraction (wait for all 3.5 years of data)
2. Develop SQL queries to label emails correctly
3. Filter out automated notifications using metadata flags
4. Train Vertex AI AutoML model
5. Deploy Cloud Function for real-time classification
6. Set up Gmail push notifications

## Critical Context

### Email Filtering Requirements
The user discovered thousands of automated lead notifications sent FROM their email that should NOT be used for training. These must be filtered out:

**Exclude from training data:**
- Emails from `no_reply@getuplevel.ai`
- Emails sent by user with ` | ` (pipe separator) in subject
- Emails sent by user with "new lead" in subject
- Any automated/templated emails that aren't real conversations

**Include in training data:**
- Back-and-forth customer conversations
- Prospect inquiries
- Internal team discussions
- Real human communications

### BigQuery Metadata Flags
The `emails_raw` table includes boolean flags for filtering:
- `is_sent_by_me`: Email was sent by brandon@getuplevel.ai
- `is_from_no_reply`: From no_reply@getuplevel.ai
- `has_pipe_separator`: Subject contains ` | `
- `has_new_lead`: Subject contains "new lead"

### Architecture Decision
We chose to extract ALL emails to BigQuery first, then apply labels via SQL queries. This allows iterative refinement of labeling logic without re-extracting emails.

## Key Files and Locations

### Project Structure
```
/home/brandon/gmail/
├── CLAUDE.md (this file)
├── PROJECT.md (original tutorial)
├── README.md (GitHub documentation)
├── .gitignore
├── gmail-agent-project/
│   ├── extract_emails.py
│   ├── extract_emails_v2.py
│   ├── extract_emails_to_bigquery.py (currently running)
│   ├── customer_domains.txt
│   ├── prospect_keywords.txt
│   ├── requirements.txt
│   └── venv/ (Python virtual environment)
└── [NOT IN GIT]:
    ├── credentials.json (OAuth2 credentials)
    ├── customers.txt (customer email list)
    ├── token.json (Gmail API token)
    └── *.csv (email data files)
```

### BigQuery Resources
- **Dataset**: `gmail_agent_dataset`
- **Table**: `emails_raw`
- **Project**: `account-strategy-464106`
- **Region**: `us-central1`

## Development Commands

### Check extraction progress
```bash
# Check if extraction is still running
ps aux | grep extract_emails_to_bigquery

# Check email count in BigQuery
bq query --use_legacy_sql=false "SELECT COUNT(*) FROM \`account-strategy-464106.gmail_agent_dataset.emails_raw\`"

# View extraction statistics
bq query --use_legacy_sql=false "
SELECT 
    COUNT(*) as total,
    COUNTIF(is_sent_by_me) as sent_by_me,
    COUNTIF(has_pipe_separator) as with_pipe,
    COUNTIF(has_new_lead) as with_new_lead
FROM \`account-strategy-464106.gmail_agent_dataset.emails_raw\`"
```

### Example labeling queries for next phase
```sql
-- Find automated notifications to exclude
SELECT * FROM `account-strategy-464106.gmail_agent_dataset.emails_raw`
WHERE is_sent_by_me = true 
AND (has_pipe_separator OR has_new_lead OR is_from_no_reply)

-- Find real customer conversations
SELECT * FROM `account-strategy-464106.gmail_agent_dataset.emails_raw`
WHERE sender_domain IN (SELECT DISTINCT domain FROM customer_domains)
AND NOT is_from_no_reply
AND NOT has_pipe_separator
```

## Important Reminders

1. **DO NOT** re-run extraction scripts without checking if one is already running
2. **DO NOT** commit sensitive files (credentials.json, customers.txt, token.json)
3. **WAIT** for extraction to complete before applying labels (check with ps aux)
4. **TEST** labeling queries thoroughly before applying to entire dataset
5. The user's email is `brandon@getuplevel.ai`
6. Company domains are `@getuplevel.ai` and `@upleveldigitalservices.com`

## Next Agent Tasks

1. Monitor extraction completion
2. Develop comprehensive SQL queries for labeling
3. Create labeled view/table for ML training
4. Export labeled data for Vertex AI
5. Continue with Phase 4-7 of the original PROJECT.md