"""
Google Calendar API → Google Meet links.

Meet creation: use OAuth (token.pickle + client secret) first. Service accounts
often get 400 "Invalid conference type value" for hangoutsMeet; a real Google
account calendar does not.

SA JSON default in project root: lustrous-setup-492718-q6-74c0162708c2.json
Override with GOOGLE_SERVICE_ACCOUNT_JSON or GOOGLE_SERVICE_ACCOUNT_FILE.
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
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/calendar"]
DEFAULT_SERVICE_ACCOUNT_FILE = "lustrous-setup-492718-q6-74c0162708c2.json"
DEFAULT_OAUTH_CLIENT_FILE = (
    "client_secret_955503077655-3lnnkjujaai3giaaq9q5tvvl2fljcj9i.apps.googleusercontent.com.json"
)
DEFAULT_OAUTH_TOKEN_FILE = "token.pickle"


def _abs_from_base(path_value, default_name):
    value = (path_value or "").strip()
    if not value:
        return os.path.join(settings.BASE_DIR, default_name)
    if os.path.isabs(value):
        return value
    return os.path.join(settings.BASE_DIR, value)


def _service_account_credentials():
    """
    Priority:
    1) GOOGLE_SERVICE_ACCOUNT_JSON (single-line JSON in .env)
    2) GOOGLE_SERVICE_ACCOUNT_FILE or settings.GOOGLE_SERVICE_ACCOUNT_FILE
    3) DEFAULT_SERVICE_ACCOUNT_FILE in project root
    """
    json_raw = (os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON") or "").strip()
    if json_raw:
        try:
            info = json.loads(json_raw)
            if info.get("type") != "service_account":
                logger.error("GOOGLE_SERVICE_ACCOUNT_JSON must be service-account JSON.")
                return None
            return service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
        except Exception as exc:
            logger.error("Invalid GOOGLE_SERVICE_ACCOUNT_JSON: %s", exc)
            return None

    cfg_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE") or getattr(
        settings, "GOOGLE_SERVICE_ACCOUNT_FILE", None
    )
    path = _abs_from_base(cfg_path, DEFAULT_SERVICE_ACCOUNT_FILE)
    if os.path.isfile(path):
        try:
            return service_account.Credentials.from_service_account_file(path, scopes=SCOPES)
        except Exception as exc:
            logger.error("Could not load service account file %s: %s", path, exc)
            return None

    logger.warning(
        "Service account key not found at %s. Set GOOGLE_SERVICE_ACCOUNT_FILE/JSON or add %s.",
        path,
        DEFAULT_SERVICE_ACCOUNT_FILE,
    )
    return None


def _calendar_service_from_oauth():
    """User OAuth — required for reliable Google Meet links on Calendar API."""
    token_path = _abs_from_base(os.environ.get("GOOGLE_OAUTH_TOKEN_FILE"), DEFAULT_OAUTH_TOKEN_FILE)
    client_secret_path = _abs_from_base(
        os.environ.get("GOOGLE_CLIENT_SECRET_FILE"), DEFAULT_OAUTH_CLIENT_FILE
    )

    creds = None
    if os.path.exists(token_path):
        try:
            with open(token_path, "rb") as token:
                creds = pickle.load(token)
        except Exception as exc:
            logger.error("Failed to load OAuth token file: %s", exc)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as exc:
                logger.error("Failed to refresh OAuth token: %s", exc)
                return None
        else:
            if not os.path.exists(client_secret_path):
                logger.warning(
                    "Google OAuth: no valid token and client secret missing at %s",
                    client_secret_path,
                )
                return None
            try:
                from google_auth_oauthlib.flow import InstalledAppFlow

                flow = InstalledAppFlow.from_client_secrets_file(client_secret_path, SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as exc:
                logger.error("Failed to run OAuth flow: %s", exc)
                return None

        try:
            with open(token_path, "wb") as token:
                pickle.dump(creds, token)
        except Exception as exc:
            logger.warning("Failed to save OAuth token: %s", exc)

    try:
        return build("calendar", "v3", credentials=creds, cache_discovery=False)
    except Exception as exc:
        logger.error("Failed to build Google Calendar service (OAuth): %s", exc)
        return None


def _calendar_service_from_service_account():
    sa_creds = _service_account_credentials()
    if not sa_creds:
        return None
    try:
        return build("calendar", "v3", credentials=sa_creds, cache_discovery=False)
    except Exception as exc:
        logger.error("Failed to build Calendar service (service account): %s", exc)
        return None


def get_google_calendar_service():
    """
    Calendar API client for Meet: OAuth user first (Meet works), then service account.
    """
    oauth_svc = _calendar_service_from_oauth()
    if oauth_svc:
        return oauth_svc
    return _calendar_service_from_service_account()


def _http_error_detail(exc: HttpError) -> str:
    try:
        return exc.content.decode(errors="replace") if exc.content else str(exc)
    except Exception:
        return str(exc)


def generate_google_meet_link(booking, client_email=None):
    """Create Calendar event + Google Meet conference and return join URL."""
    service = get_google_calendar_service()
    if not service:
        return None

    calendar_id = (
        os.environ.get("GOOGLE_CALENDAR_ID")
        or getattr(settings, "GOOGLE_CALENDAR_ID", None)
        or "primary"
    )

    try:
        start_naive = datetime.combine(booking.booking_date, booking.start_time)
        start_dt = timezone.make_aware(start_naive, timezone.get_current_timezone())
        end_dt = start_dt + timedelta(minutes=30)
        tz_name = timezone.get_current_timezone_name()

        attendees = []
        if client_email:
            attendees.append({"email": client_email})
        if getattr(booking, "consultant", None) and booking.consultant.email:
            attendees.append({"email": booking.consultant.email})

        event_body = {
            "summary": (
                f"Call Scheduled With Codigo Mantra: "
                f"{booking.client.name if getattr(booking, 'client', None) else 'Client'}"
            ),
            "description": booking.project_brief or "Call scheduled-our team will connect with you soon.",
            "start": {"dateTime": start_dt.isoformat(), "timeZone": tz_name},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": tz_name},
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
            conferenceDataVersion=1,
        ).execute()

        conf = created_event.get("conferenceData", {})
        for ep in conf.get("entryPoints", []):
            if ep.get("entryPointType") == "video":
                return ep.get("uri")
        return created_event.get("htmlLink")
    except HttpError as exc:
        logger.error(
            "Google Calendar API HttpError %s: %s",
            exc.resp.status if exc.resp else "?",
            _http_error_detail(exc),
        )
        return None
    except Exception as exc:
        logger.error("Google Meet creation failed: %s", exc)
        return None
