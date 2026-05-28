# coral_sync.py — Snapshot live APIs into JSONL for Coral SQL
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def live_cache_dir(project_root: str) -> Path:
    path = Path(project_root) / "demo_data" / "live_cache"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def sync_live_cache(project_root: str) -> Path:
    """
    Pull latest Sentry/GitHub/Slack via production clients and write JSONL
    files that Coral live_obs specs read.
    """
    from integrations import github_client, sentry_client, slack_client

    cache = live_cache_dir(project_root)
    logger.info("Syncing live observability data to Coral cache: %s", cache)

    sentry = sentry_client.fetch_active_issues()
    github = github_client.fetch_all_recent(per_page=30)
    slack = slack_client.fetch_all_configured_history()

    _write_jsonl(cache / "sentry_issues.jsonl", sentry)
    _write_jsonl(cache / "github_commits.jsonl", github)
    _write_jsonl(cache / "slack_history.jsonl", slack)

    logger.info(
        "Coral live_cache synced: sentry=%d github=%d slack=%d",
        len(sentry),
        len(github),
        len(slack),
    )
    return cache
