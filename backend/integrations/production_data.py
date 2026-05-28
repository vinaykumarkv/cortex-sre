# production_data.py — Live data fetch + SQL-shaped queries for production mode
import logging

from integrations import github_client, sentry_client, slack_client

logger = logging.getLogger(__name__)

_cache: dict[str, list[dict]] = {}


def clear_cache() -> None:
    _cache.clear()


def _load_tables() -> dict[str, list[dict]]:
    if _cache:
        return _cache

    logger.info("Loading live Sentry, GitHub, and Slack data...")
    sentry = sentry_client.fetch_active_issues()
    github = github_client.fetch_all_recent()
    slack = slack_client.fetch_all_configured_history()

    _cache["sentry"] = sentry
    _cache["github"] = github
    _cache["slack"] = slack
    return _cache


def run_query(sql_query: str, runs_data: list[dict], healed_data: list[dict]) -> list[dict]:
    """Execute supported SQL patterns against live + local cortex_system tables."""
    query_upper = sql_query.upper()
    tables = _load_tables()
    sentry_data = tables["sentry"]
    github_data = tables["github"]
    slack_data = tables["slack"]

    if "JOIN" in query_upper:
        return _join(sentry_data, github_data, slack_data, query_upper)

    if "SENTRY_ISSUES" in query_upper or "SENTRY" in query_upper and "ISSUES" in query_upper:
        return sentry_data
    if "GITHUB_COMMITS" in query_upper or "GITHUB" in query_upper and "COMMITS" in query_upper:
        return github_data
    if "SLACK_HISTORY" in query_upper or "SLACK" in query_upper and "HISTORY" in query_upper:
        return slack_data
    if "RUNS" in query_upper and "CORTEX_SYSTEM" in query_upper:
        return runs_data
    if "HEALED" in query_upper:
        return healed_data

    return []


def _join(
    sentry_data: list[dict],
    github_data: list[dict],
    slack_data: list[dict],
    query_upper: str,
) -> list[dict]:
    active_only = "STATUS = 'ACTIVE'" in query_upper.replace(" ", "") or "IS:UNRESOLVED" in query_upper
    joined_results = []

    for issue in sentry_data:
        if active_only and issue.get("status") != "active":
            continue

        target_file = issue.get("file")
        if target_file and target_file != "unknown":
            matching_commits = [
                c for c in github_data
                if c.get("file") == target_file or target_file in (c.get("message") or "")
            ]
            if not matching_commits:
                matching_commits = github_client.fetch_commits(target_file)
        else:
            matching_commits = github_data[:1]

        slack_needle = "app.py" if "APP.PY" in query_upper else target_file
        matching_slack = [
            s for s in slack_data
            if slack_needle and slack_needle.lower() in (s.get("text") or "").lower()
        ]
        if not matching_slack and target_file:
            matching_slack = [
                s for s in slack_data
                if target_file in (s.get("text") or "")
            ]

        commit = matching_commits[0] if matching_commits else {}
        slack = matching_slack[0] if matching_slack else {}

        joined_results.append({
            "issue_id": issue.get("issue_id"),
            "error_type": issue.get("error_type"),
            "message": issue.get("message"),
            "file": target_file,
            "line": issue.get("line"),
            "status": issue.get("status"),
            "commit_sha": commit.get("commit_sha"),
            "author": commit.get("author"),
            "commit_msg": commit.get("message"),
            "username": slack.get("username"),
            "slack_msg": slack.get("text"),
            "slack_channel": slack.get("channel"),
            "slack_text": slack.get("text"),
        })

    return joined_results
