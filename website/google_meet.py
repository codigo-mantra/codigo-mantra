import os
import logging
from datetime import datetime, timedelta
from uuid import uuid4
from decouple import config

from django.conf import settings
from django.utils import timezone

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from django.conf import settings



logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]

# -----------------------------
# AUTH (Using .env variables)
# -----------------------------
def get_calendar_service():
    # Fetching individual keys from .env (reconstructing token.json logic)

    # info = {
    #     "token": os.getenv("G_TOKEN"),
    #     "refresh_token": os.getenv("G_REFRESH_TOKEN"),
    #     "client_id": os.getenv("G_CLIENT_ID"),
    #     "client_secret": os.getenv("G_CLIENT_SECRET"),
    #     "token_uri": os.getenv("G_TOKEN_URI", "https://googleapis.com"),
    # }
    info = {
        "token": config("G_TOKEN"),
        "refresh_token": config("G_REFRESH_TOKEN"),
        "client_id": config("G_CLIENT_ID"),
        "client_secret": config("G_CLIENT_SECRET"),
        "token_uri": config("G_TOKEN_URI", default="https://oauth2.googleapis.com/token"),
    }

    # info = settings.GOOGLE_AUTH_INFO

    # Validation to ensure .env is set correctly
    # if not info["refresh_token"] or not info["client_id"]:
    #     logger.error("Missing Google Auth variables in .env")
    #     return None

    # Condition to check if info is a dictionary
    # and contains required keys
    if not info or not isinstance(info, dict):
        logger.error("GOOGLE_AUTH_INFO missing or invalid in settings.")
        return None

    required_keys = ["refresh_token", "client_id", "client_secret"]
    for key in required_keys:
        if not info.get(key):
            logger.error(f"Missing required Google Auth key: {key}")
            return None

    if not info.get("token_uri"):
        info["token_uri"] = "https://oauth2.googleapis.com/token"

    try:
        # Load credentials from the info dictionary
        creds = Credentials.from_authorized_user_info(info, SCOPES)

        # Handle Refreshing automatically if expired
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            # NOTE: In a pure .env approach, the new access token 
            # is used in memory but cannot be written back to the .env file.
            # This is fine as long as G_REFRESH_TOKEN is valid.

        return build("calendar", "v3", credentials=creds, cache_discovery=False)

    except Exception as e:
        logger.error("Google Auth/Service error: %s", e)
        return None

# -----------------------------
# MAIN FUNCTION
# -----------------------------
def generate_google_meet_link(booking, client_email=None):
    service = get_calendar_service()

    if not service:
        logger.error("Could not initialize Google Calendar service.")
        return None

    calendar_id = getattr(settings, "GOOGLE_CALENDAR_ID", "primary")

    try:
        # Timezone handling
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
                    "conferenceSolutionKey": {"type": "hangoutsMeet"}
                }
            }
        }

        event_result = service.events().insert(
            calendarId=calendar_id,
            body=event,
            conferenceDataVersion=1
        ).execute()

        # Extract Meet link (URI)
        conference = event_result.get("conferenceData", {})
        for ep in conference.get("entryPoints", []):
            if ep.get("entryPointType") == "video":
                return ep.get("uri")

        return event_result.get("htmlLink")

    except HttpError as e:
        logger.error("Google API HttpError: %s", e)
        return None
    except Exception as e:
        logger.error("Meet creation failed: %s", e)
        return None
