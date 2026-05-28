# sentry_client.py — Sentry Issues API
import logging
import os
import re

import httpx

logger = logging.getLogger(__name__)

SENTRY_API = "https://sentry.io/api/0"


def _headers() -> dict:
    token = os.environ.get("SENTRY_AUTH_TOKEN", "")
    return {"Authorization": f"Bearer {token}"}


def _org_project() -> tuple[str, str]:
    return os.environ["SENTRY_ORG"], os.environ["SENTRY_PROJECT"]


def fetch_active_issues() -> list[dict]:
    """Returns issues normalized to mock_obs.sentry_issues schema."""
    org, project = _org_project()
    url = f"{SENTRY_API}/projects/{org}/{project}/issues/"
    issues = []
    with httpx.Client(timeout=30) as client:
        resp = client.get(
            url,
            headers=_headers(),
            params={"query": "is:unresolved", "limit": 25},
        )
        resp.raise_for_status()
        for item in resp.json():
            issues.append(_normalize_issue(client, item))
    return issues


def _normalize_issue(client: httpx.Client, item: dict) -> dict:
    issue_id = str(item.get("id", ""))
    title = item.get("title") or item.get("culprit") or "Unknown error"
    metadata = item.get("metadata") or {}
    error_type = metadata.get("type") or _guess_error_type(title)
    message = metadata.get("value") or title

    file_path, line_no = _extract_location(item, issue_id, client)

    status_raw = (item.get("status") or "unresolved").lower()
    status = "active" if status_raw in ("unresolved", "active") else "resolved"

    return {
        "issue_id": issue_id,
        "error_type": error_type,
        "message": message,
        "file": file_path or "unknown",
        "line": line_no or 0,
        "status": status,
        "timestamp": item.get("lastSeen") or item.get("firstSeen") or "",
    }


def _guess_error_type(title: str) -> str:
    match = re.match(r"^([A-Za-z][A-Za-z0-9_]*(?:Error|Exception))", title)
    return match.group(1) if match else "Error"


def _extract_location(item: dict, issue_id: str, client: httpx.Client) -> tuple[str | None, int | None]:
    """Best-effort file:line from issue metadata or latest event."""
    culprit = item.get("culprit") or ""
    if culprit and ":" in culprit:
        parts = culprit.rsplit(":", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return os.path.basename(parts[0]), int(parts[1])

    try:
        return _fetch_event_location(client, issue_id)
    except Exception as e:
        logger.debug("Could not fetch Sentry event for %s: %s", issue_id, e)
    return None, None


def _fetch_event_location(client: httpx.Client, issue_id: str) -> tuple[str | None, int | None]:
    url = f"{SENTRY_API}/issues/{issue_id}/events/latest/"
    resp = client.get(url, headers=_headers())
    if resp.status_code != 200:
        return None, None
    event = resp.json()
    for entry in event.get("entries", []):
        if entry.get("type") != "exception":
            continue
        for exc in entry.get("data", {}).get("values", []):
            frames = exc.get("stacktrace", {}).get("frames") or []
            if not frames:
                continue
            frame = frames[-1]
            filename = frame.get("filename") or frame.get("absPath")
            if filename:
                return os.path.basename(filename), frame.get("lineNo") or frame.get("line")
    return None, None


def resolve_issue(issue_id: str) -> None:
    """Mark a Sentry issue resolved via API."""
    url = f"{SENTRY_API}/issues/{issue_id}/"
    with httpx.Client(timeout=30) as client:
        resp = client.put(url, headers=_headers(), json={"status": "resolved"})
        resp.raise_for_status()
    logger.info("Resolved Sentry issue %s", issue_id)
