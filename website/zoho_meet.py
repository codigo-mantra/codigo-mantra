import time
import logging
import requests
from datetime import datetime, timedelta
from decouple import config
from django.utils import timezone

logger = logging.getLogger(__name__)

ZOHO_ACCESS_TOKEN_CACHE = None
ZOHO_TOKEN_EXPIRY = 0


def get_zoho_access_token():
    global ZOHO_ACCESS_TOKEN_CACHE, ZOHO_TOKEN_EXPIRY

    if ZOHO_ACCESS_TOKEN_CACHE and time.time() < ZOHO_TOKEN_EXPIRY:
        return ZOHO_ACCESS_TOKEN_CACHE

    try:
        res = requests.post(
            config("ZOHO_TOKEN_URI", default="https://accounts.zoho.in/oauth/v2/token"),
            data={
                "refresh_token": config("ZOHO_REFRESH_TOKEN"),
                "client_id": config("ZOHO_CLIENT_ID"),
                "client_secret": config("ZOHO_CLIENT_SECRET"),
                "grant_type": "refresh_token",
            },
            timeout=20,
        )

        data = res.json()

        if res.status_code != 200 or "access_token" not in data:
            logger.error("Zoho token error: %s", data)
            return None

        ZOHO_ACCESS_TOKEN_CACHE = data["access_token"]
        ZOHO_TOKEN_EXPIRY = time.time() + int(data.get("expires_in", 3600)) - 60

        return ZOHO_ACCESS_TOKEN_CACHE

    except Exception as e:
        logger.error("Zoho token exception: %s", e)
        return None


def generate_zoho_meeting_link(booking, client_email=None):
    access_token = get_zoho_access_token()
    if not access_token:
        return None

    try:
        zsoid = config("ZOHO_ZSOID")
        presenter_id = config("ZOHO_PRESENTER_ID")
        meeting_api = config("ZOHO_MEETING_API", default="https://meeting.zoho.in/api/v2")

        url = f"{meeting_api}/{zsoid}/sessions.json"

        start = datetime.combine(booking.booking_date, booking.start_time)
        start_dt = timezone.make_aware(start, timezone.get_current_timezone())

        payload = {
            "session": {
                "topic": f"Call Scheduled With Codigo Mantra: {booking.client.name if booking.client else 'Client'}",
                "agenda": booking.project_brief or "Scheduled Call",
                "presenter": presenter_id,
                "startTime": start_dt.strftime("%b %d, %Y %I:%M %p"),
                "duration": 1800000,
                "timezone": "Asia/Calcutta",
                "participants": [
                    {"email": client_email}
                ] if client_email else []
            }
        }

        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}",
            "Content-Type": "application/json;charset=UTF-8",
        }

        res = requests.post(url, json=payload, headers=headers, timeout=20)

        print("ZOHO STATUS:", res.status_code)
        print("ZOHO RESPONSE:", res.text)

        data = res.json()

        if res.status_code not in [200, 201]:
            logger.error("Zoho meeting error: %s", data)
            return None

        session = data.get("session", {})

        return (
            session.get("joinLink")
            or session.get("joinUrl")
            or session.get("participantUrl")
            or session.get("meetingLink")
            or session.get("startLink")
        )

    except Exception as e:
        logger.error("Zoho meeting exception: %s", e)
        return None