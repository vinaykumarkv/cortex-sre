# connector.py - Production & Demo API Connector
import os
import json
import logging

from config import is_production, use_coral_cli

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


class DataConnector:
    """
    DataConnector acts as the data retrieval layer for CortexSRE.
    Query order: Coral CLI (SQL joins) -> REST APIs (production) -> JSONL fallback (demo).
    """
    def __init__(self, mode=None):
        if mode is None:
            from config import get_mode
            self.mode = get_mode()
        else:
            self.mode = mode.lower()
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.demo_data_dir = os.path.join(self.project_root, "demo_data")
        logger.info(f"DataConnector initialized in '{self.mode}' mode.")

    def run_coral_query(self, sql_query):
        """Execute SQL via Coral CLI, production REST, or demo JSONL fallback."""
        if use_coral_cli():
            try:
                from integrations.coral_runner import run_coral_sql
                return run_coral_sql(sql_query, self.project_root)
            except Exception as e:
                logger.warning("Coral CLI query failed, using fallback: %s", e)

        if self.mode == "production":
            return self._production_query(sql_query)

        return self._fallback_jsonl_query(sql_query)

    def _production_query(self, sql_query):
        """Live Sentry/GitHub/Slack via REST; cortex_system from local JSONL."""
        query_upper = sql_query.upper()
        runs_data = self._read_jsonl("cortex_runs.jsonl")
        healed_data = self._read_jsonl("cortex_healed.jsonl")

        if "CORTEX_SYSTEM" in query_upper:
            if "HEALED" in query_upper:
                return healed_data
            if "RUNS" in query_upper:
                return runs_data

        try:
            from integrations import production_data
            return production_data.run_query(sql_query, runs_data, healed_data)
        except Exception as e:
            logger.error("Production data fetch failed: %s", e)
            raise RuntimeError(f"Production query failed: {e}") from e

    def _fallback_jsonl_query(self, sql_query):
        """Parse local JSONL files (demo mode reliability net)."""
        query_upper = sql_query.upper()

        try:
            sentry_data = self._read_jsonl("sentry_issues.jsonl")
            github_data = self._read_jsonl("github_commits.jsonl")
            slack_data = self._read_jsonl("slack_history.jsonl")
            runs_data = self._read_jsonl("cortex_runs.jsonl")
            healed_data = self._read_jsonl("cortex_healed.jsonl")
        except Exception as file_err:
            logger.error(f"Failed to read fallback database files: {file_err}")
            return []

        if "JOIN" in query_upper:
            active_only = "STATUS = 'ACTIVE'" in query_upper.replace(" ", "")
            joined_results = []
            for issue in sentry_data:
                if active_only and issue.get("status") != "active":
                    continue

                target_file = issue.get("file")
                matching_commits = [c for c in github_data if c.get("file") == target_file]
                slack_needle = "app.py" if "APP.PY" in query_upper else target_file
                matching_slack = [
                    s for s in slack_data
                    if slack_needle and slack_needle.lower() in s.get("text", "").lower()
                ]
                if not matching_slack:
                    matching_slack = [
                        s for s in slack_data
                        if target_file and target_file in s.get("text", "")
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

        if "SENTRY_ISSUES" in query_upper:
            return sentry_data
        if "GITHUB_COMMITS" in query_upper:
            return github_data
        if "SLACK_HISTORY" in query_upper:
            return slack_data
        if "RUNS" in query_upper:
            return runs_data
        if "HEALED_FILES" in query_upper or "HEALED" in query_upper:
            return healed_data

        return []

    def _read_jsonl(self, filename):
        filepath = os.path.join(self.demo_data_dir, filename)
        if not os.path.exists(filepath):
            return []
        data = []
        with open(filepath, "r") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line.strip()))
        return data

    def write_jsonl(self, filename, record, append=True):
        filepath = os.path.join(self.demo_data_dir, filename)
        mode = "a" if append else "w"
        with open(filepath, mode) as f:
            f.write(json.dumps(record) + "\n")
        logger.info(f"Successfully recorded data log to {filename}")

    def post_slack_alert(self, text: str) -> bool:
        if is_production():
            from integrations import slack_client
            channel = os.environ.get("SLACK_INCIDENT_CHANNEL", "incident-alerts")
            try:
                slack_client.post_message(channel, text)
                return True
            except Exception as e:
                logger.warning("Slack post failed: %s", e)
                return False
        self.write_jsonl("slack_history.jsonl", {
            "channel": "#incident-alerts",
            "username": "cortex-sre-autopilot",
            "text": text,
            "timestamp": __import__("datetime").datetime.now().isoformat(),
        })
        return True

    def resolve_sentry(self, issue_id: str) -> bool:
        if is_production():
            from integrations import sentry_client
            from integrations import production_data
            ok = sentry_client.resolve_issue(issue_id)
            if ok:
                production_data.clear_cache()
            return ok
        self._resolve_sentry_jsonl(issue_id)
        return True

    def _resolve_sentry_jsonl(self, issue_id: str) -> None:
        sentry_file = os.path.join(self.demo_data_dir, "sentry_issues.jsonl")
        if not os.path.exists(sentry_file):
            return
        records = []
        with open(sentry_file, "r") as f:
            for line in f:
                if line.strip():
                    rec = json.loads(line.strip())
                    if rec.get("issue_id") == issue_id:
                        rec["status"] = "resolved"
                    records.append(rec)
        with open(sentry_file, "w") as f:
            for rec in records:
                f.write(json.dumps(rec) + "\n")
