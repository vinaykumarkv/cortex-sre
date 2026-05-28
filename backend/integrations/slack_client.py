# slack_client.py — Slack Conversations API
import logging
import os

import httpx

logger = logging.getLogger(__name__)

SLACK_API = "https://slack.com/api"


def _headers() -> dict:
    return {"Authorization": f"Bearer {os.environ['SLACK_BOT_TOKEN']}"}


def _clean_channel(value: str) -> str:
    return value.strip().strip("'\"")


def resolve_channel_id(channel: str) -> str:
    """Resolve #name or channel ID to a Slack channel ID."""
    channel = _clean_channel(channel)
    if channel.startswith("C") and len(channel) > 8:
        return channel

    name = channel.lstrip("#").lower()
    with httpx.Client(timeout=30) as client:
        cursor = None
        while True:
            params = {"types": "public_channel,private_channel", "limit": 200}
            if cursor:
                params["cursor"] = cursor
            resp = client.get(
                f"{SLACK_API}/conversations.list",
                headers=_headers(),
                params=params,
            )
            data = resp.json()
            if not data.get("ok"):
                raise RuntimeError(data.get("error", "conversations.list failed"))

            for ch in data.get("channels", []):
                if ch.get("name", "").lower() == name:
                    return ch["id"]

            cursor = (data.get("response_metadata") or {}).get("next_cursor")
            if not cursor:
                break

    raise ValueError(f"Slack channel not found: {channel}")


def fetch_channel_history(channel: str, limit: int = 50) -> list[dict]:
    channel_id = resolve_channel_id(channel)
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            f"{SLACK_API}/conversations.history",
            headers=_headers(),
            params={"channel": channel_id, "limit": limit},
        )
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("error", "conversations.history failed"))
        messages = data.get("messages", [])

    return [_normalize_message(channel, m) for m in messages]


def fetch_all_configured_history() -> list[dict]:
    """Merge history from incident + dev channels."""
    channels = []
    for key in ("SLACK_INCIDENT_CHANNEL", "SLACK_DEV_CHANNEL"):
        val = os.environ.get(key, "").strip()
        if val:
            channels.append(val)

    seen = set()
    combined: list[dict] = []
    for ch in channels:
        try:
            for msg in fetch_channel_history(ch):
                uid = (msg.get("channel"), msg.get("timestamp"), msg.get("text"))
                if uid not in seen:
                    seen.add(uid)
                    combined.append(msg)
        except Exception as e:
            logger.warning("Slack history for %s failed: %s", ch, e)
    return combined


def post_message(channel: str, text: str) -> None:
    channel_id = resolve_channel_id(channel)
    with httpx.Client(timeout=30) as client:
        resp = client.post(
            f"{SLACK_API}/chat.postMessage",
            headers={**_headers(), "Content-Type": "application/json"},
            json={"channel": channel_id, "text": text},
        )
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("error", "chat.postMessage failed"))
    logger.info("Posted Slack message to %s", channel)


def _normalize_message(channel: str, msg: dict) -> dict:
    return {
        "channel": _clean_channel(channel),
        "username": msg.get("username") or msg.get("user") or "unknown",
        "text": msg.get("text", ""),
        "timestamp": msg.get("ts", ""),
    }
