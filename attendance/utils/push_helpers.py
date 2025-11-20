import json
import logging
from typing import Iterable, Optional, Tuple

import requests
from django.conf import settings
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2 import service_account

from attendance.models import IntegrationSetting

logger = logging.getLogger(__name__)

FCM_ENDPOINT = "https://fcm.googleapis.com/fcm/send"
FCM_V1_ENDPOINT = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]


def get_fcm_server_key() -> str:
    """Fetch the server key from settings or IntegrationSetting."""
    direct_key = getattr(settings, "FCM_SERVER_KEY", "")
    if direct_key:
        direct_key = direct_key.strip()
        if direct_key:
            return direct_key

    try:
        config = IntegrationSetting.get_solo()
        stored_key = (config.fcm_server_key or "").strip()
        if stored_key:
            return stored_key
    except Exception:
        logger.debug("Unable to load IntegrationSetting for FCM key.", exc_info=True)
    return ""


def get_service_account_credentials() -> Optional[Tuple[service_account.Credentials, str]]:
    """Return (credentials, project_id) for Firebase HTTP v1 if configured."""
    raw_json = getattr(settings, "FCM_SERVICE_ACCOUNT_JSON", "") or ""
    raw_json = raw_json.strip()
    if not raw_json:
        try:
            config = IntegrationSetting.get_solo()
            raw_json = (config.fcm_service_account_json or "").strip()
        except Exception:
            logger.debug("Unable to load IntegrationSetting for service account.", exc_info=True)
            raw_json = ""

    if not raw_json:
        return None

    try:
        info = json.loads(raw_json)
    except Exception:
        logger.exception("Invalid Firebase service account JSON.")
        return None

    project_id = info.get("project_id")
    if not project_id:
        logger.error("Firebase service account JSON missing project_id.")
        return None

    try:
        credentials = service_account.Credentials.from_service_account_info(info, scopes=SCOPES)
    except Exception:
        logger.exception("Unable to build credentials from service account JSON.")
        return None

    return credentials, project_id


def send_database_update_notification(
    tokens: Iterable[str],
) -> Tuple[bool, str]:
    """
    Notify all registered devices (via FCM) to refresh their local database.

    Returns:
        (success, message)
    """
    token_list = [token for token in tokens if token]
    if not token_list:
        return False, "No registered devices to notify."

    service_credentials = get_service_account_credentials()
    if service_credentials:
        return _send_v1_notifications(token_list, service_credentials)

    server_key = get_fcm_server_key()
    if server_key:
        return _send_legacy_notifications(token_list, server_key)

    return False, "Firebase credentials are missing. Provide a service account JSON (preferred) or legacy server key."


def _send_v1_notifications(
    tokens: Iterable[str],
    credential_bundle: Tuple[service_account.Credentials, str],
) -> Tuple[bool, str]:
    credentials, project_id = credential_bundle
    auth_request = GoogleAuthRequest()
    try:
        credentials.refresh(auth_request)
    except Exception:
        logger.exception("Unable to refresh Firebase service account credentials.")
        return False, "Failed to authenticate with Firebase. Check your service account JSON."

    access_token = credentials.token
    if not access_token:
        return False, "Failed to obtain Firebase access token."

    url = FCM_V1_ENDPOINT.format(project_id=project_id)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    success = 0
    failure = 0
    for device_token in tokens:
        payload = {
            "message": {
                "token": device_token,
                "data": {"type": "database_updated"},
            }
        }
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                success += 1
            else:
                logger.warning("FCM v1 error for token %s: %s", device_token, response.text)
                failure += 1
        except Exception:
            logger.exception("FCM v1 request failed for token %s", device_token)
            failure += 1

    message = f"Sync request sent via FCM v1 (success: {success}, failed: {failure})."
    return (success > 0), message


def _send_legacy_notifications(tokens: Iterable[str], server_key: str) -> Tuple[bool, str]:
    headers = {
        "Authorization": f"key={server_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "registration_ids": list(tokens),
        "data": {"type": "database_updated"},
        "priority": "high",
    }

    try:
        response = requests.post(FCM_ENDPOINT, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        body = response.json()
        success_count = body.get("success", 0)
        failure_count = body.get("failure", 0)
        return True, f"Legacy FCM request sent to {success_count} device(s); {failure_count} failed."
    except Exception:
        logger.exception("Unable to send legacy FCM sync request.")
        return False, "Failed to reach legacy FCM endpoint. Check server logs for details."
