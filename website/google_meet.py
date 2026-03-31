"""
Google Meet via Google Calendar API (service account creates event + conferenceData).

Enable in views: uncomment `from .google_meet import generate_google_meet_link` and the
fallback block in `_booking_followup_zoom_and_emails`.

Setup:
1. Google Cloud project → enable Calendar API.
2. Create a service account, download JSON key.
3. Share the target Google Calendar with the service account email (Editor), or use a
   calendar owned by a workspace where the SA has domain-wide delegation (advanced).

Environment:
- GOOGLE_CALENDAR_ID: calendar id (default: primary — only works if SA has its own calendar)
- GOOGLE_SERVICE_ACCOUNT_JSON: full JSON string OR
- GOOGLE_SERVICE_ACCOUNT_FILE: absolute path to the JSON file

Optional in Django settings (see codigo/settings.py): GOOGLE_SERVICE_ACCOUNT_FILE, GOOGLE_CALENDAR_ID
"""

import json
import logging
import os
import pickle
from datetime import datetime, timedelta
from uuid import uuid4

from django.conf import settings
from django.utils import timezone
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

# If modifying scopes, delete token.pickle
SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_google_calendar_service():
    """
    Get authenticated Google Calendar service using token.pickle or client_secret.
    """
    creds = None
    token_path = os.path.join(settings.BASE_DIR, 'token.pickle')
    client_secret_path = os.path.join(settings.BASE_DIR, 'client_secret_775236158556-f0rhmdo8kilm64srtv7q15vjrbpouc7v.apps.googleusercontent.com.json')

    # Load saved token
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            try:
                creds = pickle.load(token)
            except Exception as e:
                logger.error("Failed to load token.pickle: %s", e)

    # If no valid creds, login (Note: run_local_server requires interactive session)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logger.error("Failed to refresh Google token: %s", e)
                return None
        else:
            if not os.path.exists(client_secret_path):
                logger.error("Google client secret file not found at %s", client_secret_path)
                return None
            
            try:
                flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
                # This will fail in a non-interactive server environment if not already authenticated
                creds = flow.run_local_server(port=0)
            except Exception as e:
                logger.error("Failed to run Google auth flow: %s", e)
                return None

        # Save token for reuse
        with open(token_path, 'wb') as token:
            pickle.dump(creds, token)

    try:
        service = build('calendar', 'v3', credentials=creds, cache_discovery=False)
        return service
    except Exception as e:
        logger.error("Failed to build Google Calendar service: %s", e)
        return None

def generate_google_meet_link(booking, client_email=None):
    """
    Create a Calendar event with Google Meet and return the video join URI.
    """
    service = get_google_calendar_service()
    if not service:
        return None

    calendar_id = os.environ.get("GOOGLE_CALENDAR_ID") or getattr(
        settings, "GOOGLE_CALENDAR_ID", "primary"
    )

    try:
        start_naive = datetime.combine(booking.booking_date, booking.start_time)
        if timezone.is_naive(start_naive):
            start_dt = timezone.make_aware(start_naive, timezone.get_current_timezone())
        else:
            start_dt = start_naive
        end_dt = start_dt + timedelta(minutes=15)
        tz_name = timezone.get_current_timezone_name()

        attendees = []
        if client_email:
            attendees.append({'email': client_email})
        if booking.consultant and booking.consultant.email:
            attendees.append({'email': booking.consultant.email})

        event_body = {
            "summary": f"Discovery Call: {booking.client.name if hasattr(booking, 'client') and booking.client else 'Client'}",
            "description": booking.project_brief or "Scheduled from website booking form.",
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": tz_name,
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": tz_name,
            },
            "attendees": attendees,
            "conferenceData": {
                "createRequest": {
                    "requestId": str(uuid4()),
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
        }

        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event_body,
            conferenceDataVersion=1
        ).execute()

        # Extract Meet link
        conf = created_event.get("conferenceData", {})
        entry_points = conf.get("entryPoints", [])
        for ep in entry_points:
            if ep.get("entryPointType") == "video":
                return ep.get("uri")

        return created_event.get("htmlLink")

    except Exception as e:
        logger.error("Google Meet creation failed: %s", e)
        return None
