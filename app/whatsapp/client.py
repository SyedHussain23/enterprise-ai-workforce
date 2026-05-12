"""
WhatsApp Business Cloud API client.

Meta Cloud API docs: https://developers.facebook.com/docs/whatsapp/cloud-api/messages
Handles sending text messages and read receipts.
"""
import httpx

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)

GRAPH_URL = "https://graph.facebook.com/v20.0"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }


def send_text(to: str, body: str) -> bool:
    """
    Send a plain text message to a WhatsApp number.

    Args:
        to:   Phone number in E.164 format (e.g. "971501234567" — no +)
        body: Message body. Max 4096 characters.

    Returns:
        True if message was accepted by Meta API, False otherwise.
    """
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        logger.warning("whatsapp.not_configured")
        return False

    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": body[:4096]},
    }

    try:
        url = f"{GRAPH_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        with httpx.Client(timeout=10) as client:
            resp = client.post(url, json=payload, headers=_headers())
        resp.raise_for_status()
        logger.info("whatsapp.sent", to=to, status=resp.status_code)
        return True
    except Exception as exc:
        logger.error("whatsapp.send_failed", to=to, error=str(exc))
        return False


def mark_read(message_id: str) -> None:
    """Mark an inbound message as read (shows double-tick to sender)."""
    if not settings.WHATSAPP_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
        return
    try:
        url = f"{GRAPH_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        with httpx.Client(timeout=5) as client:
            client.post(url, json=payload, headers=_headers())
    except Exception as exc:
        logger.warning("whatsapp.mark_read_failed", error=str(exc))
