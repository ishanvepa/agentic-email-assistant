import sys
import os.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from email_types import Email

# If modifying SCOPES, delete the token.json file.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def authenticate_gmail():
    """Authenticate and return a Gmail API service."""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    return service

def fetch_k_emails(k=5):
    """Fetch and return the last k emails as a list of Email objects."""
    service = authenticate_gmail()
    results = service.users().messages().list(userId='me', maxResults=k).execute()
    messages = results.get('messages', [])

    email_list = []
    if not messages:
        print("No messages found.")
        return email_list
    for msg in messages:
        msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
        headers = msg_data.get('payload', {}).get('headers', [])

        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        body = ''
        # Try to extract the body (plain text)
        payload = msg_data.get('payload', {})
        if 'parts' in payload:
            for part in payload['parts']:
                if part.get('mimeType') == 'text/plain':
                    body = part.get('body', {}).get('data', '')
                    break
        elif payload.get('mimeType') == 'text/plain':
            body = payload.get('body', {}).get('data', '')
        date = next((h['value'] for h in headers if h['name'] == 'Date'), None)
        email_obj = Email(subject=subject, sender=sender, body=body, date=date, id=msg['id'])
        email_list.append(email_obj)
    print(email_list)
    return email_list

if __name__ == '__main__':
    # service = authenticate_gmail()
    fetch_k_emails(10)
