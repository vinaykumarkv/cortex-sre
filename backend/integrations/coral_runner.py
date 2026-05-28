# coral_runner.py — Execute queries through Coral CLI
import json
import logging
import os
import subprocess

from config import is_production, use_coral_cli

logger = logging.getLogger(__name__)


def coral_available() -> bool:
    try:
        result = subprocess.run(
            ["coral", "--version"],
            capture_output=True,
            text=True,
            shell=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def _rewrite_sql_for_production(sql_query: str) -> str:
    """Point mock_obs namespace at live_cache-backed live_obs tables."""
    return sql_query.replace("mock_obs.", "live_obs.")


def run_coral_sql(sql_query: str, project_root: str) -> list[dict]:
    """
    Run `coral sql --format json` after optional live cache sync.
    Raises on failure so caller can fall back to REST/JSONL.
    """
    if not use_coral_cli():
        raise RuntimeError("Coral CLI disabled via CORAL_USE_CLI=false")

    if is_production():
        from integrations.coral_sync import sync_live_cache
        sync_live_cache(project_root)
        sql_query = _rewrite_sql_for_production(sql_query)

    logger.info("Coral SQL: %s", sql_query[:120])
    result = subprocess.run(
        ["coral", "sql", "--format", "json", sql_query],
        capture_output=True,
        text=True,
        shell=True,
        cwd=project_root,
        timeout=90,
        check=True,
    )
    stdout = result.stdout.strip()
    if not stdout:
        return []
    return json.loads(stdout)
