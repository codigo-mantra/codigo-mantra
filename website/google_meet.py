# """
# Google Meet via Google Calendar API.

# Service account (recommended for servers):
#   GOOGLE_SERVICE_ACCOUNT_FILE=/absolute/path/to/sa-key.json
#   OR GOOGLE_SERVICE_ACCOUNT_JSON=<single-line service account JSON>
#   GOOGLE_CALENDAR_ID=<calendar id>  # calendar shared with the SA email as Editor

# OAuth (local dev only — needs browser + token.pickle):
#   GOOGLE_CLIENT_SECRET_FILE=/path/to/client_secret....json
#   GOOGLE_OAUTH_TOKEN_FILE=... (optional)

# Do NOT put OAuth "installed" / "web" client JSON in GOOGLE_SERVICE_ACCOUNT_JSON — use a
# service account key from IAM → Service accounts → Keys, or use GOOGLE_CLIENT_SECRET_FILE + OAuth.
# """

# import json
# import logging
# import os
# import pickle
# from datetime import datetime, timedelta
# from uuid import uuid4

# from django.conf import settings
# from django.utils import timezone
# from google.auth.transport.requests import Request
# from google.oauth2 import service_account
# from google_auth_oauthlib.flow import InstalledAppFlow
# from googleapiclient.discovery import build
# from googleapiclient.errors import HttpError

# logger = logging.getLogger(__name__)

# SCOPES = ["https://www.googleapis.com/auth/calendar"]

# _DEFAULT_OAUTH_CLIENT = (
#     "client_secret_775236158556-f0rhmdo8kilm64srtv7q15vjrbpouc7v.apps.googleusercontent.com.json"
# )


# def _service_account_credentials():
#     """Load service account credentials from env/settings. Returns None if misconfigured."""
#     json_raw = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
#     path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE") or getattr(
#         settings, "GOOGLE_SERVICE_ACCOUNT_FILE", None
#     )

#     if json_raw:
#         try:
#             info = json.loads(json_raw)
#         except json.JSONDecodeError as e:
#             logger.error("GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON: %s", e)
#             return None

#         if info.get("type") != "service_account":
#             if "installed" in info or "web" in info:
#                 logger.error(
#                     "GOOGLE_SERVICE_ACCOUNT_JSON contains OAuth client credentials (installed/web), "
#                     "not a service account key. Create a key in Google Cloud → IAM → Service accounts → Keys, "
#                     "or remove GOOGLE_SERVICE_ACCOUNT_JSON and set GOOGLE_CLIENT_SECRET_FILE to your "
#                     "client_secret JSON path and complete OAuth locally (token.pickle)."
#                 )
#             else:
#                 logger.error(
#                     "GOOGLE_SERVICE_ACCOUNT_JSON must be a service account key (type: service_account)."
#                 )
#             return None

#         try:
#             return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
#         except Exception as e:
#             logger.error("Invalid service account JSON: %s", e)
#             return None

#     if path:
#         if not os.path.isfile(path):
#             logger.error("GOOGLE_SERVICE_ACCOUNT_FILE does not exist: %s", path)
#             return None
#         try:
#             return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
#         except Exception as e:
#             logger.error("Could not load service account file %s: %s", path, e)
#             return None

#     return None


# def get_google_calendar_service():
#     """
#     1) Service account — use for production; share calendar with SA email.
#     2) OAuth + token.pickle — local only.
#     """
#     sa_creds = _service_account_credentials()
#     if sa_creds:
#         try:
#             return build("calendar", "v3", credentials=sa_creds, cache_discovery=False)
#         except Exception as e:
#             logger.error("Failed to build Google Calendar service (service account): %s", e)
#             return None

#     token_path = os.environ.get("GOOGLE_OAUTH_TOKEN_FILE") or os.path.join(
#         settings.BASE_DIR, "token.pickle"
#     )
#     client_secret_path = os.environ.get("GOOGLE_CLIENT_SECRET_FILE") or os.path.join(
#         settings.BASE_DIR, _DEFAULT_OAUTH_CLIENT
#     )

#     creds = None
#     if os.path.exists(token_path):
#         with open(token_path, "rb") as token:
#             try:
#                 creds = pickle.load(token)
#             except Exception as e:
#                 logger.error("Failed to load OAuth token file: %s", e)

#     if not creds or not creds.valid:
#         if creds and creds.expired and creds.refresh_token:
#             try:
#                 creds.refresh(Request())
#             except Exception as e:
#                 logger.error("Failed to refresh Google token: %s", e)
#                 return None
#         else:
#             if not os.path.exists(client_secret_path):
#                 logger.warning(
#                     "No service account configured and OAuth client secret not found at %s. "
#                     "Set GOOGLE_SERVICE_ACCOUNT_FILE or GOOGLE_SERVICE_ACCOUNT_JSON (service account key).",
#                     client_secret_path,
#                 )
#                 return None
#             try:
#                 flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
#                 creds = flow.run_local_server(port=0)
#             except Exception as e:
#                 logger.error("OAuth flow failed (needs interactive browser): %s", e)
#                 return None

#         with open(token_path, "wb") as token:
#             pickle.dump(creds, token)

#     try:
#         return build("calendar", "v3", credentials=creds, cache_discovery=False)
#     except Exception as e:
#         logger.error("Failed to build Google Calendar service: %s", e)
#         return None


# def generate_google_meet_link(booking, client_email=None):
#     service = get_google_calendar_service()
#     if not service:
#         return None

#     calendar_id = os.environ.get("GOOGLE_CALENDAR_ID") or getattr(
#         settings, "GOOGLE_CALENDAR_ID", "primary"
#     )

#     try:
#         start_naive = datetime.combine(booking.booking_date, booking.start_time)
#         if timezone.is_naive(start_naive):
#             start_dt = timezone.make_aware(start_naive, timezone.get_current_timezone())
#         else:
#             start_dt = start_naive
#         end_dt = start_dt + timedelta(minutes=15)
#         tz_name = timezone.get_current_timezone_name()

#         attendees = []
#         if client_email:
#             attendees.append({"email": client_email})
#         if booking.consultant and booking.consultant.email:
#             attendees.append({"email": booking.consultant.email})

#         event_body = {
#             "summary": f"Call Scheduled With Codigo Mantra: {booking.client.name if hasattr(booking, 'client') and booking.client else 'Client'}",
#             "description": booking.project_brief or "Call scheduled—our team will connect with you soon.",
#             "start": {
#                 "dateTime": start_dt.isoformat(),
#                 "timeZone": tz_name,
#             },
#             "end": {
#                 "dateTime": end_dt.isoformat(),
#                 "timeZone": tz_name,
#             },
#             "attendees": attendees,
#             "conferenceData": {
#                 "createRequest": {
#                     "requestId": str(uuid4()),
#                     "conferenceSolutionKey": {"type": "hangoutsMeet"},
#                 }
#             },
#         }

#         created_event = service.events().insert(
#             calendarId=calendar_id,
#             body=event_body,
#             conferenceDataVersion=1,
#         ).execute()

#         conf = created_event.get("conferenceData", {})
#         entry_points = conf.get("entryPoints", [])
#         for ep in entry_points:
#             if ep.get("entryPointType") == "video":
#                 return ep.get("uri")

#         return created_event.get("htmlLink")

#     except HttpError as e:
#         logger.error(
#             "Google Calendar API error (check Calendar API enabled, calendar shared with SA, GOOGLE_CALENDAR_ID): %s",
#             e,
#         )
#         return None
#     except Exception as e:
#         logger.error("Google Meet creation failed: %s", e)
#         return None




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
            "summary": f"Call Scheduled With Codigo Mantra: {booking.client.name if hasattr(booking, 'client') and booking.client else 'Client'}",
            "description": booking.project_brief or "Call scheduled—our team will connect with you soon.",
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