import base64
import sys
import os.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from langchain_core.tools import tool 

# If modifying SCOPES, delete the token.json file.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/calendar']

def decode_base64url(data):
    try:
        return base64.urlsafe_b64decode(data + '=' * (-len(data) % 4)).decode('utf-8')
    except Exception as e:
        print(f"Failed to decode email body: {e}")
        return ''

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

@tool
def fetch_k_emails(k=5, query=None, after=None, before=None, unread_only=False):
    """
    Fetch and return the last k emails that contain any of the given query in the subject or body,
    optionally filtered by date/time and unread status.
    This tool is only to be called by the inbox_reader_agent agent.

    Args:
        k (int): Number of recent emails to fetch. If not specified, defaults to 5.
        query (str): query to filter emails by. If not provided, fetches the most recent emails.
        after (str): Only include emails after this date (YYYY/MM/DD or epoch seconds).
        before (str): Only include emails before this date (YYYY/MM/DD or epoch seconds).
        unread_only (bool): If True, only fetch unread emails.

    Returns:
        list[dict[str, str]]: The emails as a list of dictionaries, each containing subject, sender, body, date, and ID.
    """
    service = authenticate_gmail()

    results = service.users().messages().list(userId='me', maxResults=k, q=query).execute()
    messages = results.get('messages', [])

    email_list = []
    if not messages:
        print("No messages found.")
        print(f"Parameters used: k={k}, query={query}, after={after}, before={before}, unread_only={unread_only}")
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
                    body_data = part.get('body', {}).get('data', '')
                    body = decode_base64url(body_data)
                    break
        elif payload.get('mimeType') == 'text/plain':
            body_data = payload.get('body', {}).get('data', '')
            body = decode_base64url(body_data)
        date = next((h['value'] for h in headers if h['name'] == 'Date'), None)
        email_dict = {
            'subject': subject,
            'sender': sender,
            'body': body,
            'date': date,
            'id': msg['id']
        }
        email_list.append(email_dict)
        # print(f"\nEmail ID: {email_dict['id']}")
        # print(f"From: {email_dict['sender']}")
        # print(f"Subject: {email_dict['subject']}")
        # print(f"Date: {email_dict['date']}")
        # print(f"Body:\n{email_dict['body']}\n{'-'*40}")
    return {"emails": email_list}

# if __name__ == '__main__':
#     # service = authenticate_gmail()
#     query = ['meeting', 'zoom', 'schedule', 'calendar', 'invite', 'appointment', 'availability', 'time to meet', 'set up a meeting', 'meeting request', 'meeting inquiry']
#     fetch_k_emails(10, query[8], unread_only=False)
