import os
import json
import logging
from datetime import datetime, timedelta
from uuid import uuid4

from django.conf import settings
from django.utils import timezone

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

TOKEN_FILE = "token.json"
CLIENT_SECRET_FILE = "credentials.json"


# -----------------------------
# Helper (optional)
# -----------------------------
def _abs(path):
    if not path:
        return None
    if os.path.isabs(path):
        return path
    return os.path.join(settings.BASE_DIR, path)


# -----------------------------
# AUTH (NO pickle, production safe)
# -----------------------------
def get_calendar_service():
    token_path = _abs(os.environ.get("GOOGLE_OAUTH_TOKEN_FILE")) or os.path.join(settings.BASE_DIR, TOKEN_FILE)
    client_secret_path = _abs(os.environ.get("GOOGLE_CLIENT_SECRET_FILE")) or os.path.join(settings.BASE_DIR, CLIENT_SECRET_FILE)

    creds = None

    # 1. Load token.json
    if os.path.exists(token_path):
        try:
            with open(token_path, "r") as f:
                creds = Credentials.from_authorized_user_info(
                    json.load(f),
                    SCOPES
                )
        except Exception as e:
            logger.error("Token load failed: %s", e)

    # 2. Refresh token if expired
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())

            with open(token_path, "w") as f:
                f.write(creds.to_json())

        except Exception as e:
            logger.error("Token refresh failed: %s", e)
            return None

    # 3. First-time login
    if not creds:
        if not os.path.exists(client_secret_path):
            logger.error("Missing credentials.json file")
            return None

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                client_secret_path,
                SCOPES
            )

            creds = flow.run_local_server(
                port=0,
                access_type="offline",
                prompt="consent"
            )

            with open(token_path, "w") as f:
                f.write(creds.to_json())

        except Exception as e:
            logger.error("OAuth failed: %s", e)
            return None

    # 4. Build service
    try:
        return build("calendar", "v3", credentials=creds, cache_discovery=False)
    except Exception as e:
        logger.error("Calendar service error: %s", e)
        return None


# -----------------------------
# MAIN FUNCTION
# -----------------------------
def generate_google_meet_link(booking, client_email=None):
    service = get_calendar_service()

    if not service:
        return None

    calendar_id = getattr(settings, "GOOGLE_CALENDAR_ID", "primary")

    try:
        start = datetime.combine(booking.booking_date, booking.start_time)
        start_dt = timezone.make_aware(start, timezone.get_current_timezone())
        end_dt = start_dt + timedelta(minutes=30)

        attendees = []

        if client_email:
            attendees.append({"email": client_email})

        if getattr(booking, "consultant", None) and booking.consultant.email:
            attendees.append({"email": booking.consultant.email})

        event = {
            "summary": f"Meeting: {booking.client.name if booking.client else 'Client'}",
            "description": booking.project_brief or "Scheduled meeting",
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": timezone.get_current_timezone_name()
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": timezone.get_current_timezone_name()
            },
            "attendees": attendees,
            "conferenceData": {
                "createRequest": {
                    "requestId": str(uuid4()),
                    "conferenceSolutionKey": {
                        "type": "hangoutsMeet"
                    }
                }
            }
        }

        event = service.events().insert(
            calendarId=calendar_id,
            body=event,
            conferenceDataVersion=1
        ).execute()

        # Extract Meet link
        conference = event.get("conferenceData", {})
        for ep in conference.get("entryPoints", []):
            if ep.get("entryPointType") == "video":
                return ep.get("uri")

        return event.get("htmlLink")

    except HttpError as e:
        logger.error("Google API error: %s", e)
        return None

    except Exception as e:
        logger.error("Meet creation failed: %s", e)
        return None