# extract_emails_to_bigquery.py
import os
import csv
import base64
import json
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.cloud import bigquery
from google.oauth2 import service_account
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Scopes
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# BigQuery settings
PROJECT_ID = "account-strategy-464106"
DATASET_ID = "gmail_agent_dataset"
TABLE_ID = "emails_raw"

# Your email address (to identify sent emails)
MY_EMAIL = "brandon@getuplevel.ai"  # Update this with your actual email

def get_gmail_service():
    """Authenticates and returns a Gmail API service client."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def get_bigquery_client():
    """Returns a BigQuery client."""
    return bigquery.Client(project=PROJECT_ID)

def extract_email_address(email_string):
    """Extract clean email address from a string like 'Name <email@domain.com>'"""
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', email_string)
    return match.group(0).lower() if match else ""

def extract_domain(email):
    """Extract domain from email address."""
    if '@' in email:
        return email.split('@')[1].lower()
    return ""

def parse_email_headers(headers):
    """Parse email headers into a dictionary."""
    header_dict = {}
    for header in headers:
        header_dict[header['name'].lower()] = header['value']
    return header_dict

def extract_emails_to_bigquery():
    """Fetches emails and loads them directly to BigQuery."""
    service = get_gmail_service()
    bq_client = get_bigquery_client()
    table_ref = bq_client.dataset(DATASET_ID).table(TABLE_ID)
    table = bq_client.get_table(table_ref)
    
    # Calculate date 3.5 years ago
    date_3_5_years_ago = (datetime.now() - timedelta(days=3.5 * 365.25)).strftime('%Y/%m/%d')
    query = f'after:{date_3_5_years_ago}'
    
    page_token = None
    total_processed = 0
    batch_size = 500
    rows_to_insert = []
    
    extraction_timestamp = datetime.utcnow().isoformat() + 'Z'
    
    while True:
        try:
            logging.info(f"Fetching page with token: {page_token}")
            response = service.users().messages().list(userId='me', q=query, pageToken=page_token).execute()
            messages = response.get('messages', [])
            
            if not messages:
                logging.info("No more messages found.")
                break

            for msg in messages:
                try:
                    msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                    
                    # Parse message data
                    payload = msg_data['payload']
                    headers = parse_email_headers(payload['headers'])
                    
                    # Extract basic fields
                    message_id = msg_data['id']
                    thread_id = msg_data['threadId']
                    
                    sender = headers.get('from', '')
                    sender_email = extract_email_address(sender)
                    sender_domain = extract_domain(sender_email)
                    
                    recipients_to = headers.get('to', '')
                    recipients_cc = headers.get('cc', '')
                    recipients_bcc = headers.get('bcc', '')
                    
                    subject = headers.get('subject', '')
                    date_str = headers.get('date', '')
                    
                    # Parse date
                    try:
                        # Convert email date to timestamp
                        from email.utils import parsedate_to_datetime
                        email_date = parsedate_to_datetime(date_str).isoformat() if date_str else None
                    except:
                        email_date = None
                    
                    # Extract body
                    body = ""
                    if 'parts' in payload:
                        for part in payload['parts']:
                            if part['mimeType'] == 'text/plain':
                                body_data = part['body'].get('data')
                                if body_data:
                                    body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                                    break
                    elif 'body' in payload and 'data' in payload['body']:
                        body_data = payload['body'].get('data')
                        if body_data:
                            body = base64.urlsafe_b64decode(body_data).decode('utf-8', errors='ignore')
                    
                    # Truncate body if too long (BigQuery has limits)
                    if len(body) > 10000:
                        body = body[:10000] + "... [truncated]"
                    
                    # Extract labels
                    label_ids = msg_data.get('labelIds', [])
                    labels = ','.join(label_ids)
                    
                    # Compute boolean flags
                    is_sent_by_me = sender_email == MY_EMAIL
                    has_pipe_separator = ' | ' in subject
                    has_new_lead = 'new lead' in subject.lower()
                    is_from_no_reply = sender_email == 'no_reply@getuplevel.ai'
                    
                    # Create row for BigQuery
                    row = {
                        'message_id': message_id,
                        'sender': sender[:500],  # Truncate if needed
                        'sender_email': sender_email,
                        'sender_domain': sender_domain,
                        'recipients_to': recipients_to[:500],
                        'recipients_cc': recipients_cc[:500],
                        'recipients_bcc': recipients_bcc[:500],
                        'subject': subject[:500],
                        'body': body,
                        'email_date': email_date,
                        'is_sent_by_me': is_sent_by_me,
                        'has_pipe_separator': has_pipe_separator,
                        'has_new_lead': has_new_lead,
                        'is_from_no_reply': is_from_no_reply,
                        'thread_id': thread_id,
                        'labels': labels[:500],
                        'extraction_date': extraction_timestamp
                    }
                    
                    rows_to_insert.append(row)
                    total_processed += 1
                    
                    # Insert batch into BigQuery
                    if len(rows_to_insert) >= batch_size:
                        errors = bq_client.insert_rows_json(table, rows_to_insert)
                        if errors:
                            logging.error(f"Failed to insert rows: {errors}")
                        else:
                            logging.info(f"Inserted {len(rows_to_insert)} rows. Total processed: {total_processed}")
                        rows_to_insert = []
                    
                except Exception as e:
                    logging.error(f"Error processing message {msg.get('id')}: {e}")
                    continue

            page_token = response.get('nextPageToken')
            if not page_token:
                break

        except HttpError as error:
            logging.error(f'An error occurred: {error}')
            break
    
    # Insert any remaining rows
    if rows_to_insert:
        errors = bq_client.insert_rows_json(table, rows_to_insert)
        if errors:
            logging.error(f"Failed to insert final rows: {errors}")
        else:
            logging.info(f"Inserted final {len(rows_to_insert)} rows")
    
    logging.info(f"Email extraction complete. Total emails processed: {total_processed}")
    
    # Run a quick analysis query
    query = f"""
    SELECT 
        COUNT(*) as total_emails,
        COUNTIF(is_sent_by_me) as sent_by_me,
        COUNTIF(is_from_no_reply) as from_no_reply,
        COUNTIF(has_pipe_separator) as with_pipe_separator,
        COUNTIF(has_new_lead) as with_new_lead
    FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    """
    
    results = bq_client.query(query).result()
    for row in results:
        print("\n=== Initial Statistics ===")
        print(f"Total emails: {row.total_emails:,}")
        print(f"Sent by you: {row.sent_by_me:,}")
        print(f"From no_reply: {row.from_no_reply:,}")
        print(f"With pipe separator: {row.with_pipe_separator:,}")
        print(f"With 'new lead': {row.with_new_lead:,}")


if __name__ == '__main__':
    print("Starting email extraction to BigQuery...")
    print(f"Project: {PROJECT_ID}")
    print(f"Dataset: {DATASET_ID}")
    print(f"Table: {TABLE_ID}")
    extract_emails_to_bigquery()