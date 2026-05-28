# github_client.py — GitHub Commits API
import logging
import os

import httpx

logger = logging.getLogger(__name__)


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def fetch_commits(file_path: str | None = None, per_page: int = 10) -> list[dict]:
    owner = os.environ["GITHUB_OWNER"]
    repo = os.environ["GITHUB_REPO"]
    url = f"https://api.github.com/repos/{owner}/{repo}/commits"
    params: dict = {"per_page": per_page}
    if file_path and file_path != "unknown":
        params["path"] = file_path

    with httpx.Client(timeout=30) as client:
        resp = client.get(url, headers=_headers(), params=params)
        if resp.status_code in (404, 409):
            # 404 = repo not found; 409 = empty repo with no commits yet
            logger.warning("GitHub commits unavailable (%s): %s", resp.status_code, resp.text[:200])
            return []
        resp.raise_for_status()
        commits = resp.json()

    normalized = []
    for c in commits:
        commit = c.get("commit", {})
        author = (c.get("author") or {}).get("login") or commit.get("author", {}).get("name", "unknown")
        sha = c.get("sha", "")[:7]
        message = (commit.get("message") or "").split("\n")[0]
        normalized.append({
            "commit_sha": sha,
            "author": author,
            "message": message,
            "file": file_path or "unknown",
            "timestamp": commit.get("author", {}).get("date", ""),
        })
    return normalized


def fetch_all_recent(per_page: int = 20) -> list[dict]:
    """Recent commits without path filter (for status dashboard)."""
    return fetch_commits(file_path=None, per_page=per_page)
