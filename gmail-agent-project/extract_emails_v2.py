# extract_emails_v2.py
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
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Scopes determine the level of access.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Company domains to exclude internal emails
COMPANY_DOMAINS = ['getuplevel.ai', 'upleveldigitalservices.com']

def load_customer_emails(filename):
    """Loads customer emails from the CSV file."""
    customer_emails = set()
    customer_domains = set()
    
    try:
        with open(filename, 'r') as f:
            reader = csv.reader(f, delimiter='\t')
            next(reader)  # Skip header
            for row in reader:
                for cell in row:
                    if cell:
                        emails = cell.split(',')
                        for email in emails:
                            email = email.strip()
                            if '@' in email:
                                customer_emails.add(email.lower())
                                domain = email.split('@')[1].lower()
                                # Don't add company domains to customer domains
                                if domain not in COMPANY_DOMAINS:
                                    customer_domains.add(domain)
    except Exception as e:
        logging.error(f"Error loading customer emails: {e}")
    
    return customer_emails, customer_domains

def load_prospect_keywords(filename):
    """Loads keywords from a file."""
    with open(filename, 'r') as f:
        return [line.strip().lower() for line in f if line.strip()]

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

def extract_all_emails_from_headers(headers):
    """Extract all email addresses from the email headers."""
    all_emails = set()
    
    # Fields to check for email addresses
    email_fields = ['from', 'to', 'cc', 'bcc']
    
    for header in headers:
        if header['name'].lower() in email_fields:
            value = header['value']
            # Extract email addresses using regex
            emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', value)
            for email in emails:
                all_emails.add(email.lower())
    
    return all_emails

def label_email(sender, subject, body, headers, customer_emails, customer_domains, prospect_keywords):
    """Applies a label based on the new logic."""
    
    # Extract all email addresses from the email
    all_emails = extract_all_emails_from_headers(headers)
    
    # Check if this is an internal email (only company emails)
    non_company_emails = [email for email in all_emails 
                          if not any(email.endswith('@' + domain) for domain in COMPANY_DOMAINS)]
    
    if not non_company_emails:
        return "Internal"
    
    # Check if sender is a customer
    sender_email = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', sender.lower())
    if sender_email:
        sender_email = sender_email[0]
        sender_domain = sender_email.split('@')[1]
        
        if sender_email in customer_emails or sender_domain in customer_domains:
            return "Customer"
    
    # Check if any participant is a customer
    for email in all_emails:
        if email in customer_emails:
            return "Customer"
        domain = email.split('@')[1] if '@' in email else ''
        if domain in customer_domains:
            return "Customer"
    
    # Check for prospect keywords in content
    text_content = (subject + ' ' + body).lower()
    
    # Enhanced prospect keywords for lead generation
    lead_indicators = [
        'new lead', 'form submission', 'interested in', 'pricing',
        'demo request', 'trial', 'sign up', 'inquiry', 'question about',
        'quote request', 'estimate', 'consultation', 'appointment',
        'homeowner', 'looking to', 'need help with', 'project:'
    ]
    
    if any(keyword in text_content for keyword in prospect_keywords + lead_indicators):
        return "Prospect"
    
    # Check for specific lead generation patterns
    if any(pattern in text_content for pattern in 
           ['lead aggregator', 'homebuddy', 'angi', 'thumbtack', 'homeadvisor']):
        return "Prospect"
        
    return "Other"

def get_emails():
    """Fetches and processes emails from the last 3.5 years."""
    service = get_gmail_service()
    customer_emails, customer_domains = load_customer_emails('customers.txt')
    prospect_keywords = load_prospect_keywords('prospect_keywords.txt')
    
    logging.info(f"Loaded {len(customer_emails)} customer emails and {len(customer_domains)} customer domains")
    
    # Calculate date 3.5 years ago
    date_3_5_years_ago = (datetime.now() - timedelta(days=3.5 * 365.25)).strftime('%Y/%m/%d')
    query = f'after:{date_3_5_years_ago}'
    
    results = []
    page_token = None
    email_count = 0
    
    with open('emails_labeled.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['text_content', 'label', 'sender', 'date']
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
                    try:
                        msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                        payload = msg_data['payload']
                        headers = payload['headers']
                        
                        subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), '')
                        sender = next((h['value'] for h in headers if h['name'].lower() == 'from'), '')
                        date = next((h['value'] for h in headers if h['name'].lower() == 'date'), '')
                        
                        body = ""
                        if 'parts' in payload:
                            for part in payload['parts']:
                                if part['mimeType'] == 'text/plain':
                                    body_data = part['body'].get('data')
                                    if body_data:
                                        body = base64.urlsafe_b64decode(body_data.encode('ASCII')).decode('utf-8', errors='ignore')
                                        break
                        elif 'body' in payload and 'data' in payload['body']:
                            body_data = payload['body'].get('data')
                            if body_data:
                                body = base64.urlsafe_b64decode(body_data.encode('ASCII')).decode('utf-8', errors='ignore')
                        
                        label = label_email(sender, subject, body, headers, customer_emails, customer_domains, prospect_keywords)
                        
                        # Combine subject and body for training text
                        text_content = subject + " " + body.replace('\r\n', ' ').replace('\n', ' ')[:1000]  # Limit length
                        writer.writerow({
                            'text_content': text_content,
                            'label': label,
                            'sender': sender,
                            'date': date
                        })
                        
                        email_count += 1
                        if email_count % 100 == 0:
                            logging.info(f"Processed {email_count} emails")
                    
                    except Exception as e:
                        logging.error(f"Error processing message: {e}")
                        continue

                page_token = response.get('nextPageToken')
                if not page_token:
                    break

            except HttpError as error:
                logging.error(f'An error occurred: {error}')
                break
                
    logging.info(f"Email extraction complete. Processed {email_count} emails. Data saved to emails_labeled.csv")
    
    # Print label distribution
    print("\nLabel distribution:")
    with open('emails_labeled.csv', 'r') as f:
        reader = csv.DictReader(f)
        labels = {}
        for row in reader:
            label = row['label']
            labels[label] = labels.get(label, 0) + 1
        
        for label, count in sorted(labels.items()):
            print(f"{label}: {count}")


if __name__ == '__main__':
    print("Starting email extraction with new labeling logic...")
    print("Labels: Customer, Internal, Prospect, Other")
    get_emails()