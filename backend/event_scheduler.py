import datetime
import os.path
from langchain_core.tools import tool 
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/calendar']

def get_user_credentials():
    """Authenticate the user and return Google API credentials."""
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds

def get_gcal_service():
    """Return an authenticated Google Calendar service using user credentials."""
    creds = get_user_credentials()
    return build('calendar', 'v3', credentials=creds)

@tool
def schedule_google_calendar_event(
    summary: str,
    description: str,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    attendees: list[str] = [],
):
    """
    Tool: Schedule a Google Calendar event for the user.

    This tool is only to be called by the event_scheduler_agent.
    The agent must provide the event summary (title), description, start and end times (as datetime objects).
    If available the agent can provide a list of attendee email addresses.

    The tool will return the created event details as a dictionary if successful.
    If there is an authentication or API error, the tool will raise an exception.

    Args:
        summary (str): Title of the event (e.g., "Team Meeting").
        description (str): Description of the event (e.g., "Discuss project updates").
        start_time (datetime): Event start time (UTC, as a datetime object).
        end_time (datetime): Event end time (UTC, as a datetime object).
        attendees (list[str]): List of attendee email addresses (e.g., ["alice@example.com", ...]).

    Returns:
        dict: The created event resource from the Google Calendar API.
    """
    service = get_gcal_service()
    event = {
        'summary': summary,
        'description': description,
        'start': {
            'dateTime': start_time.isoformat(),
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': end_time.isoformat(),
            'timeZone': 'UTC',
        },
        'attendees': [{'email': email} for email in attendees],
    }
    created_event = service.events().insert(calendarId="primary", body=event).execute()
    return created_event

@tool
def check_google_calendar_availability(
    start_time: datetime.datetime,
    end_time: datetime.datetime,
) -> bool:
    """
    Tool: Check if the specified time slot is available in the user's Google Calendar.

    Args:
        start_time (datetime): Start time of the slot (UTC, as a datetime object).
        end_time (datetime): End time of the slot (UTC, as a datetime object).
        calendar_id (str, optional): Google Calendar ID. Defaults to "primary".

    Returns:
        bool: True if the time slot is free, False if there is a conflict.
    """
    service = get_gcal_service()
    body = {
        "timeMin": start_time.isoformat() + "Z",
        "timeMax": end_time.isoformat() + "Z",
        "items": [{"id": "primary"}],
    }
    events_result = service.freebusy().query(body=body).execute()
    busy_times = events_result["calendars"]["primary"].get("busy", [])
    return len(busy_times) == 0

# Sample usage:
# def main():
#     summary = "Team Meeting"
#     description = "Discuss project updates and next steps."
#     start_time = datetime.datetime.utcnow() + datetime.timedelta(days=1, hours=2)
#     end_time = start_time + datetime.timedelta(hours=1)
#     attendees = ["alice@example.com", "bob@example.com"]
#     event = schedule_google_calendar_event(
#         summary, description, start_time, end_time, attendees
#     )
#     print("Event created:")
#     print(event)

# if __name__ == "__main__":
#     main()
