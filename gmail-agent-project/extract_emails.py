# extract_emails.py
import os
import csv
import base64
from datetime import datetime, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Scopes determine the level of access.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def load_heuristics(filename):
    """Loads keywords or domains from a file."""
    with open(filename, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def get_gmail_service():
    """Authenticates and returns a Gmail API service client."""
    creds = None
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def label_email(sender, subject, body, customer_domains, prospect_keywords):
    """Applies a label based on simple heuristics."""
    sender_domain = sender.split('@')[-1].replace('>', '')
    if sender_domain in customer_domains:
        return "Customer"
    
    text_content = (subject + ' ' + body).lower()
    if any(keyword in text_content for keyword in prospect_keywords):
        return "Prospect"
        
    return "Unknown" # We will filter these out later

def get_emails():
    """Fetches and processes emails from the last 3.5 years."""
    service = get_gmail_service()
    customer_domains = load_heuristics('customer_domains.txt')
    prospect_keywords = load_heuristics('prospect_keywords.txt')
    
    # Calculate date 3.5 years ago
    date_3_5_years_ago = (datetime.now() - timedelta(days=3.5 * 365.25)).strftime('%Y/%m/%d')
    query = f'after:{date_3_5_years_ago}'
    
    results = []
    page_token = None
    
    with open('emails.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['text_content', 'label']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        while True:
            try:
                logging.info(f"Fetching page with token: {page_token}")
                response = service.users().messages().list(userId='me', q=query, pageToken=page_token).execute()
                messages = response.get('messages', [])
                
                if not messages:
                    logging.info("No more messages found.")
                    break

                for msg in messages:
                    msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                    payload = msg_data['payload']
                    headers = payload['headers']
                    
                    subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
                    sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
                    
                    body = ""
                    if 'parts' in payload:
                        for part in payload['parts']:
                            if part['mimeType'] == 'text/plain':
                                body_data = part['body'].get('data')
                                if body_data:
                                    body = base64.urlsafe_b64decode(body_data.encode('ASCII')).decode('utf-8')
                                    break
                    elif 'body' in payload and 'data' in payload['body']:
                         body_data = payload['body'].get('data')
                         if body_data:
                            body = base64.urlsafe_b64decode(body_data.encode('ASCII')).decode('utf-8')
                    
                    label = label_email(sender, subject, body, customer_domains, prospect_keywords)
                    
                    if label != "Unknown" and body:
                        # Combine subject and body for training text
                        text_content = subject + " " + body.replace('\r\n', ' ').replace('\n', ' ')
                        writer.writerow({'text_content': text_content, 'label': label})

                page_token = response.get('nextPageToken')
                if not page_token:
                    break

            except HttpError as error:
                logging.error(f'An error occurred: {error}')
                break
                
    logging.info("Email extraction complete. Data saved to emails.csv")


if __name__ == '__main__':
    # You need to create a credentials.json file from the Google Cloud Console
    # Go to APIs & Services -> Credentials -> Create Credentials -> OAuth client ID
    # Select 'Desktop app' and download the JSON file, renaming it to 'credentials.json'
    print("Please make sure you have a 'credentials.json' file in this directory.")
    print("If you don't have one, go to the Google Cloud Console -> APIs & Services -> Credentials.")
    get_emails()