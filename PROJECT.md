Build a Gmail AI Agent on Google Cloud: A Step-by-Step GuideThis guide provides all the necessary steps, commands, and code to build an AI agent that classifies incoming emails as "Prospect" or "Customer" and automatically applies the corresponding label in your Gmail account.Table of ContentsProject OverviewPrerequisitesPhase 1: Google Cloud Project SetupPhase 2: Data Extraction & LabelingPhase 3: Data Storage & PreparationPhase 4: Build and Run the Training PipelinePhase 5: Deploy the ModelPhase 6: Build and Deploy the Agent (Cloud Function)Phase 7: Activate the AgentConclusion & Next StepsProject OverviewWe will build a complete, end-to-end machine learning system on Google Cloud.Data Source: Your Gmail account (last 3.5 years of emails).Core Task: Classify emails into two categories: Prospect and Customer.Platform: Google Cloud (Vertex AI, Cloud Storage, BigQuery, Cloud Functions).End Result: An automated agent that applies a Prospect or Customer label to new, incoming emails.PrerequisitesGoogle Cloud Account: You need a Google Cloud account with billing enabled.Google Cloud SDK: Install and initialize the gcloud CLI on your local machine. Installation Guide.Python 3.8+: Ensure you have Python installed locally.Gmail Account: The Workspace account you want to manage.Phase 1: Google Cloud Project SetupFirst, set up your Google Cloud environment.1.1. Create and Configure ProjectRun these commands in your local terminal.# 1. Create a new project (or use an existing one)
gcloud projects create gmail-ai-agent --name="Gmail AI Agent"

# 2. Set your new project as the default
export PROJECT_ID="gmail-ai-agent" # Replace with your project ID
gcloud config set project $PROJECT_ID

# 3. Link your billing account
export BILLING_ACCOUNT=$(gcloud beta billing accounts list --format='value(ACCOUNT_ID)')
gcloud beta billing projects link $PROJECT_ID --billing-account=$BILLING_ACCOUNT

# 4. Set a default region
export REGION="us-central1"
gcloud config set compute/region $REGION
1.2. Enable Required APIsThis grants your project permission to use the necessary services.gcloud services enable \
  iam.googleapis.com \
  cloudresourcemanager.googleapis.com \
  storage.googleapis.com \
  bigquery.googleapis.com \
  aiplatform.googleapis.com \
  cloudfunctions.googleapis.com \
  cloudbuild.googleapis.com \
  pubsub.googleapis.com \
  gmail.googleapis.com
1.3. Local AuthenticationAuthenticate your local environment to access Google Cloud and Gmail APIs.# Authenticate for Google Cloud Application Default Credentials
gcloud auth application-default login

# Authenticate for the Gmail API specifically
gcloud auth login --scopes=https://www.googleapis.com/auth/gmail.readonly,https://www.googleapis.com/auth/gmail.labels,https://www.googleapis.com/auth/gmail.modify
This will open a browser window asking you to grant permission. Make sure to log in with the Gmail account you want the agent to manage.Phase 2: Data Extraction & LabelingNow, we'll write a script to pull emails from Gmail and perform initial labeling.2.1. Create Project StructureOn your local machine, create a new folder for this project.mkdir gmail-agent-project
cd gmail-agent-project
2.2. Create Labeling HeuristicsCreate two files to help our script label the data.customer_domains.txt:# Add one domain per line. Emails from these domains will be labeled 'Customer'.
your-company.com
bigcustomer.com
another-client.net
```prospect_keywords.txt`:
Add one keyword per line. Emails containing these will be labeled 'Prospect'.demo requestpricinginquiryquestion aboutinterested intrialsign up
### 2.3. Create the Extraction Script

Create a file named `extract_emails.py`. This script will:
* Connect to the Gmail API.
* Search for emails from the last 3.5 years.
* Apply a `Customer` or `Prospect` label based on your heuristic files.
* Save the output as a `emails.csv` file.

```python
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
2.4. Run the ScriptGet Credentials: Go to your Google Cloud Console, navigate to APIs & Services > Credentials. Click + CREATE CREDENTIALS > OAuth client ID. Select Desktop app, give it a name, and download the JSON file. Rename this file to credentials.json and place it in your gmail-agent-project directory.Install Libraries: pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlibRun: python extract_emails.pyThis will create a token.json file for future runs and an emails.csv file with your training data.Phase 3: Data Storage & PreparationNow, we upload the extracted data to Google Cloud for our pipeline to use.3.1. Create GCS Bucket and BigQuery Dataset# 1. Create a Google Cloud Storage bucket
export BUCKET_NAME="gs://${PROJECT_ID}-email-data"
gcloud storage buckets create $BUCKET_NAME --location=$REGION

# 2. Upload your CSV to the bucket
gcloud storage cp emails.csv ${BUCKET_NAME}/data/

# 3. Create a BigQuery dataset
export DATASET_NAME="email_agent_dataset"
bq --location=$REGION mk --dataset $PROJECT_ID:$DATASET_NAME
3.2. Create BigQuery TableWe will create a table in BigQuery directly from the CSV file in our GCS bucket.# Create the table from the CSV in GCS
bq load \
    --source_format=CSV \
    --autodetect \
    ${DATASET_NAME}.labeled_emails \
    ${BUCKET_NAME}/data/emails.csv
Phase 4: Build and Run the Training PipelineWe'll use Vertex AI Pipelines with the AutoML component to train our classifier.4.1. Go to Vertex AI WorkbenchNavigate to Vertex AI -> Workbench in the Google Cloud Console. Create a new Jupyter Notebook instance. Use the default settings, but ensure it's a TensorFlow-based image.4.2. Create the Pipeline CodeOnce the notebook is running, open it and create a new Python 3 notebook file. Paste and run the following code in the notebook cells.Cell 1: Install Libraries!pip install --upgrade google-cloud-aiplatform kfp google-cloud-pipeline-components --user
# You will need to restart the kernel after this installation.
Cell 2: Setup and Importsimport kfp
from kfp import dsl
from google.cloud import aiplatform
from google_cloud_pipeline_components.v1.automl.training_job import AutoMLTextTrainingJobRunOp

# Set your project variables
PROJECT_ID = "gmail-ai-agent"  # <-- Make sure this is your project ID
REGION = "us-central1"
BUCKET_NAME = f"gs://{PROJECT_ID}-email-data"
PIPELINE_ROOT = f"{BUCKET_NAME}/pipeline-root"
DATASET_NAME = "email_agent_dataset"
TABLE_NAME = "labeled_emails"
MODEL_DISPLAY_NAME = "gmail_classifier_model"
Cell 3: Define the Pipeline@dsl.pipeline(
    name="automl-text-classification-pipeline",
    pipeline_root=PIPELINE_ROOT
)
def pipeline(
    project: str,
    model_display_name: str,
    dataset_bq_source: str
):
    # This component creates a Vertex AI Dataset from our BigQuery table
    dataset_create_op = dsl.importer(
        artifact_uri=dataset_bq_source,
        artifact_class=dsl.Dataset,
        reimport=False,
    )

    # This component trains the AutoML model
    training_job_run_op = AutoMLTextTrainingJobRunOp(
        project=project,
        display_name=model_display_name,
        prediction_type="classification",
        multi_label=False,
        dataset=dataset_create_op.outputs["artifact"],
        target_column="label"
    )

Cell 4: Compile and Run the Pipelinefrom kfp.v2 import compiler

# Define the BQ source for our data
bq_source = f"bq://{PROJECT_ID}.{DATASET_NAME}.{TABLE_NAME}"

# Compile the pipeline
compiler.Compiler().compile(
    pipeline_func=pipeline,
    package_path="text_classification_pipeline.json"
)

# Initialize the Vertex AI client
aiplatform.init(project=PROJECT_ID, location=REGION)

# Create the pipeline job
job = aiplatform.PipelineJob(
    display_name="gmail-classifier-training",
    template_path="text_classification_pipeline.json",
    pipeline_root=PIPELINE_ROOT,
    parameter_values={
        "project": PROJECT_ID,
        "model_display_name": MODEL_DISPLAY_NAME,
        "dataset_bq_source": bq_source
    }
)

# Run the job
job.run()
Running these cells will kick off a new pipeline run in Vertex AI -> Pipelines. This process can take over an hour as AutoML trains and evaluates the model.Phase 5: Deploy the ModelOnce the pipeline successfully completes, a new model will appear in your Vertex AI Model Registry.5.1. Find and Deploy the ModelNavigate to Vertex AI -> Models.Find your model, named gmail_classifier_model.Click on the model name, then click the DEPLOY TO ENDPOINT button.Choose Create new endpoint, give it a name (e.g., gmail-classifier-endpoint), and use the default settings.Click DEPLOY. Deployment can take 15-20 minutes.5.2. Get Endpoint IDOnce deployed, go to the Endpoints page in Vertex AI, click on your endpoint, and find the ENDPOINT ID. You will need this for the next step. It's a long number.Phase 6: Build and Deploy the Agent (Cloud Function)This function will be the active agent. It will trigger on new emails, call our model for a prediction, and apply a label.6.1. Create Gmail LabelsFirst, manually create the two labels in your Gmail account:AI-ProspectAI-Customer6.2. Create the Cloud Function CodeIn your local gmail-agent-project directory, create a new folder email_agent_function. Inside it, create two files: main.py and requirements.txt.requirements.txt:google-cloud-aiplatform
google-api-python-client
```main.py`:
```python
import base64
import json
from google.cloud import aiplatform
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# --- CONFIGURATION ---
PROJECT_ID = "gmail-ai-agent" # Your Project ID
REGION = "us-central1" # Your region
ENDPOINT_ID = "YOUR_ENDPOINT_ID" # <--- PASTE YOUR ENDPOINT ID HERE
GMAIL_USER_ID = "me" # Use 'me' for the authenticated user

def get_prediction(text_content):
    """Calls the Vertex AI endpoint for a prediction."""
    aiplatform.init(project=PROJECT_ID, location=REGION)
    endpoint = aiplatform.Endpoint(ENDPOINT_ID)
    
    # The AutoML Text model expects a list of instances.
    instances = [{"content": text_content}]
    
    prediction_response = endpoint.predict(instances=instances)
    
    # Extract the prediction display name
    prediction = prediction_response.predictions[0]
    predicted_label = prediction['displayNames'][0]
    
    return predicted_label

def get_gmail_service():
    """Returns a Gmail service object using default credentials."""
    # Cloud Functions run with a service account. You must grant it Gmail access.
    # We will do this via the gcloud command line later.
    credentials = Credentials.from_authorized_user_info(info=None, scopes=['https://www.googleapis.com/auth/gmail.modify'])
    service = build('gmail', 'v1', credentials=credentials, cache_discovery=False)
    return service

def get_label_id(service, label_name):
    """Gets the ID of a label by its name."""
    results = service.users().labels().list(userId=GMAIL_USER_ID).execute()
    labels = results.get('labels', [])
    for label in labels:
        if label['name'] == label_name:
            return label['id']
    return None

def apply_label(service, msg_id, label_id):
    """Applies a label to a specific email message."""
    label_body = {'addLabelIds': [label_id]}
    service.users().messages().modify(userId=GMAIL_USER_ID, id=msg_id, body=label_body).execute()
    print(f"Applied label ID {label_id} to message {msg_id}")

def process_email(event, context):
    """Cloud Function entry point."""
    # Decode the Pub/Sub message
    pubsub_message = base64.b64decode(event['data']).decode('utf-8')
    message_json = json.loads(pubsub_message)
    email_address = message_json['emailAddress']
    history_id = message_json['historyId']
    
    print(f"New email for {email_address} with historyId {history_id}")
    
    service = get_gmail_service()
    
    # Get the latest message from the history
    history = service.users().history().list(userId=GMAIL_USER_ID, startHistoryId=history_id).execute()
    # The first change is usually the new message arrival
    msg_id = history['history'][0]['messages'][0]['id']
    
    # Get the message content
    msg = service.users().messages().get(userId=GMAIL_USER_ID, id=msg_id).execute()
    payload = msg['payload']
    headers = payload['headers']
    subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
    
    # Extract body text (simplified version)
    body = ""
    if 'data' in payload['body']:
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    
    text_content = subject + " " + body
    
    # Get prediction from our AI model
    predicted_label = get_prediction(text_content)
    print(f"Model predicted: {predicted_label}")
    
    # Map prediction to Gmail label name
    label_to_apply = None
    if predicted_label == 'Customer':
        label_to_apply = 'AI-Customer'
    elif predicted_label == 'Prospect':
        label_to_apply = 'AI-Prospect'
        
    if label_to_apply:
        label_id = get_label_id(service, label_to_apply)
        if label_id:
            apply_label(service, msg_id, label_id)
        else:
            print(f"Error: Label '{label_to_apply}' not found in Gmail.")
6.3. Deploy the Cloud FunctionCreate Pub/Sub Topic: This topic will receive notifications from Gmail.gcloud pubsub topics create gmail-push-notifications
Deploy the Function: Run this command from inside the email_agent_function directory.gcloud functions deploy gmail-agent-function \
  --runtime python39 \
  --trigger-topic gmail-push-notifications \
  --entry-point process_email \
  --region $REGION \
  --service-account=${PROJECT_ID}@${PROJECT_ID}.iam.gserviceaccount.com
Note: This command might fail initially asking you to grant permissions to the service account. Follow the instructions provided by the gcloud error output to grant the necessary roles. You will likely need to grant the Service Account Token Creator role.Grant Gmail Access to the Function's Service Account: This is the most critical permission step. We need to authorize the service account to access your Gmail data.Find your function's service account email: ${PROJECT_ID}@${PROJECT_ID}.iam.gserviceaccount.com.Go to your Google Workspace Admin Console.Navigate to Security -> Access and data control -> API controls.Under Domain-wide Delegation, click MANAGE DOMAIN WIDE DELEGATION.Click Add new and enter the service account's Client ID. (To get the Client ID, go to IAM & Admin -> Service Accounts in Cloud Console, find your service account, and copy its "Unique ID").In the "OAuth scopes" field, add: https://www.googleapis.com/auth/gmail.modifyClick Authorize.Phase 7: Activate the AgentThe final step is to tell Gmail to send notifications for new emails to our Pub/Sub topic.7.1. Create an Activation ScriptIn your main gmail-agent-project directory, create a script activate_watch.py.# activate_watch.py
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
import os

PROJECT_ID = "gmail-ai-agent" # Your Project ID
TOPIC_NAME = "gmail-push-notifications"
SCOPES = ['https://www.googleapis.com/auth/gmail.modify'] # Use modify to be safe

def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        raise Exception("Token not found or invalid. Please re-run extract_emails.py to authenticate.")
    return build('gmail', 'v1', credentials=creds)

def start_watch():
    service = get_gmail_service()
    request = {
        'labelIds': ['INBOX'],
        'topicName': f'projects/{PROJECT_ID}/topics/{TOPIC_NAME}'
    }
    response = service.users().watch(userId='me', body=request).execute()
    print("Watch request successful. Agent is now active.")
    print(response)

if __name__ == '__main__':
    start_watch()

7.2. Run the Activation Scriptpython activate_watch.py
If successful, your agent is now live! Send yourself a test email with a prospect keyword like "interested in your pricing" to see the AI-Prospect label get applied automatically.Conclusion & Next StepsCongratulations! You have built a complete, end-to-end AI email agent on Google Cloud. It extracts historical data, trains a model using an automated pipeline, and uses that model in a live agent to manage your inbox.Next Steps:Improve Labeling: Your model is only as good as your data. Improve the labeling heuristics in extract_emails.py or manually label a subset of your data for higher quality.Re-train on a Schedule: Set up a Cloud Scheduler job to trigger your Vertex AI Pipeline periodically to keep your model fresh.Expand Agent Actions: Modify the Cloud Function to perform other actions, like forwarding emails, sending automated replies, or creating tasks in a CRM.