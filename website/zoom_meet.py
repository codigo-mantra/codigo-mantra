import base64
import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

from django.utils import timezone

logger = logging.getLogger(__name__)

ZOOM_TOKEN_URL = "https://zoom.us/oauth/token"


def _zoom_access_token():
    account_id = os.environ.get("ZOOM_ACCOUNT_ID")
    client_id = os.environ.get("ZOOM_CLIENT_ID")
    client_secret = os.environ.get("ZOOM_CLIENT_SECRET")
    if not all([account_id, client_id, client_secret]):
        logger.warning("Zoom: set ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, and ZOOM_CLIENT_SECRET in the environment.")
        return None
    auth = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    body = urllib.parse.urlencode(
        {"grant_type": "account_credentials", "account_id": account_id}
    ).encode()
    req = urllib.request.Request(
        ZOOM_TOKEN_URL,
        data=body,
        method="POST",
        headers={
            "Authorization": f"Basic {auth}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        return data.get("access_token")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode(errors="replace")
        logger.warning("Zoom OAuth token request failed (%s): %s", e.code, err_body)
        return None
    except (urllib.error.URLError, ValueError, json.JSONDecodeError) as e:
        logger.warning("Zoom OAuth token request failed: %s", e)
        return None


def generate_zoom_meet_link(booking, client_email=None):
    """
    Create a Zoom meeting and return the join URL (Server-to-Server OAuth).

    Environment:
    - ZOOM_ACCOUNT_ID, ZOOM_CLIENT_ID, ZOOM_CLIENT_SECRET (Marketplace S2S app)
    - ZOOM_HOST_USER_ID: required — host's Zoom login email or user id (do not use "me" for S2S)

    Returns join URL string, or None if credentials are missing or the API fails.
    """
    host_user = (os.environ.get("ZOOM_HOST_USER_ID") or "").strip()
    if not host_user:
        logger.warning(
            "Zoom: ZOOM_HOST_USER_ID is not set. "
            "Use the host user's Zoom email or user id (Server-to-Server OAuth cannot use 'me')."
        )
        return None

    token = _zoom_access_token()
    if not token:
        return None

    url = f"https://api.zoom.us/v2/users/{urllib.parse.quote(host_user, safe='')}/meetings"

    start_naive = datetime.combine(booking.booking_date, booking.start_time)
    if timezone.is_naive(start_naive):
        start_dt = timezone.make_aware(start_naive, timezone.get_current_timezone())
    else:
        start_dt = start_naive
    end_dt = start_dt + timedelta(minutes=15)
    tz_name = timezone.get_current_timezone_name()
    start_str = start_dt.strftime("%Y-%m-%dT%H:%M:%S")

    payload = {
        "topic": "Codigo Mantra Discovery Call",
        "type": 2,
        "start_time": start_str,
        "duration": max(1, int((end_dt - start_dt).total_seconds() // 60)),
        "timezone": tz_name,
        "agenda": (booking.project_brief or "Scheduled from website booking form.")[:2000],
        "settings": {
            "waiting_room": True,
            "join_before_host": False,
        },
    }

    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            out = json.loads(resp.read().decode())
        return out.get("join_url")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode(errors="replace")
        logger.warning("Zoom create meeting failed (%s): %s", e.code, err_body)
        return None
    except (urllib.error.URLError, ValueError, json.JSONDecodeError) as e:
        logger.warning("Zoom create meeting failed: %s", e)
        return None
