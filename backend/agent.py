# agent.py - Autonomous SRE Agent Orchestrator
import json
import logging
import os
from datetime import datetime
from connector import DataConnector
from healer import CodeHealer

logger = logging.getLogger(__name__)

class CortexSREAgent:
    """
    CortexSREAgent orchestrates the autonomous SRE and Self-Healing workflow.
    It:
      1. Queries Coral for active Sentry alerts.
      2. Invokes CodeHealer to fix files, run tests, and self-heal.
      3. Publishes results (simulated PRs, Slack notifications, Coral run logs).
    """
    def __init__(self, mode=None):
        self.connector = DataConnector(mode=mode)
        self.healer = CodeHealer()
        # Initialize internal state logs
        self.active_incident = None
        self.thought_stream = []

    def log_thought(self, stage, message):
        """Appends to the streaming trace shown in the UI cockpit."""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "stage": stage, # e.g. "SENSING", "PLANNING", "HEALING", "VERIFYING", "ACTION"
            "message": message
        }
        self.thought_stream.append(log_entry)
        logger.info(f"[{stage}] {message}")

    def execute_autopilot(self):
        """
        Executes a complete self-healing autopilot cycle.
        Returns a detailed summary of steps and results for UI render.
        """
        self.thought_stream = []
        self.log_thought("SENSING", "CortexSRE Autopilot active. Querying Coral SQL for unresolved production alerts...")

        # Step 1: Use Coral to join Sentry + GitHub + Slack
        # This is the exact 'Navigator/IncidentMind' style unified diagnostic JOIN!
        sre_join_query = (
            "SELECT sentry.issue_id, sentry.error_type, sentry.message, sentry.file, sentry.line, "
            "github.commit_sha, github.author, github.message AS commit_msg, "
            "slack.username, slack.text AS slack_msg "
            "FROM mock_obs.sentry_issues AS sentry "
            "LEFT JOIN mock_obs.github_commits AS github ON github.file = sentry.file "
            "LEFT JOIN mock_obs.slack_history AS slack ON slack.text LIKE '%app.py%' "
            "WHERE sentry.status = 'active'"
        )
        
        # Execute query via Coral (or JSONL fallback)
        incidents = self.connector.run_coral_query(sre_join_query)
        
        if not incidents:
            self.log_thought("SENSING", "No active production alerts found. System is healthy.")
            return {
                "incident_found": False,
                "thoughts": self.thought_stream
            }

        incident = incidents[0]
        self.active_incident = incident
        self.log_thought("PLANNING", f"Found high-priority alert {incident['issue_id']}: '{incident['error_type']}' in file '{incident['file']}'.")
        self.log_thought("PLANNING", f"Joined Coral Context: Culprit commit is {incident['commit_sha']} by @{incident['author']} ('{incident['commit_msg']}').")
        self.log_thought("PLANNING", f"Slack discussion context correlated: @{incident['username']} said '{incident['slack_msg']}'.")
        self.log_thought("PLANNING", f"Drafting self-healing implementation plan to patch '{incident['file']}' around line {incident['line']}.")

        # Step 2: Commencing Healing Loop
        self.log_thought("HEALING", "Invoking unit test suite to isolate error...")
        
        start_time = datetime.now()
        healing_result = self.healer.self_heal_incident(incident)
        duration = int((datetime.now() - start_time).total_seconds())

        if not healing_result["success"]:
            self.log_thought("HEALING", f"Self-healing loop failed after {healing_result['attempts']} attempts. Notifying human engineers.")
            # Record failed run
            self._record_run(incident["issue_id"], "failed", duration)
            return {
                "incident_found": True,
                "success": False,
                "incident": incident,
                "healing_details": healing_result,
                "thoughts": self.thought_stream
            }

        # Step 3: Record Success & Launch Automated Actions
        self.log_thought("VERIFYING", f"Unit tests successfully passed on Attempt #{healing_result['attempts']}!")
        self.log_thought("ACTION", "Drafting automated fix summary and committing changes...")
        
        # Create a mock GitHub Pull Request
        pr_number = 104
        self.log_thought("ACTION", f"Successfully opened GitHub Pull Request #{pr_number}: 'fix: resolve ZeroDivisionError in rating average calculation'")
        
        # Send automated Slack alert
        slack_alert = (
            f"✅ [CortexSRE Autopilot] OUTAGE RESOLVED: Incident {incident['issue_id']} "
            f"(ZeroDivisionError) in app.py has been healed. Automated test suite passed successfully. "
            f"Opened Pull Request #{pr_number} with code patches. Live Dashboard: http://localhost:8000"
        )
        self.connector.post_slack_alert(slack_alert)
        self.log_thought("ACTION", "Sent resolution report to Slack incident channel.")

        # Update Sentry to resolved (API in production, JSONL in demo)
        self.connector.resolve_sentry(incident["issue_id"])
        self.log_thought("ACTION", f"Sentry Incident {incident['issue_id']} status updated to 'resolved'.")

        # Step 4: Record this run in the custom Coral cortex_system log!
        run_id = f"RUN-{(int(datetime.now().timestamp()) % 1000):03d}"
        healed_id = f"HEAL-{(int(datetime.now().timestamp()) % 1000):03d}"
        
        self.connector.write_jsonl("cortex_runs.jsonl", {
            "run_id": run_id,
            "incident_id": incident["issue_id"],
            "status": "completed",
            "duration_sec": duration,
            "timestamp": datetime.now().isoformat()
        })
        
        self.connector.write_jsonl("cortex_healed.jsonl", {
            "healed_id": healed_id,
            "file": incident["file"],
            "lines_changed": 4,
            "test_status": "passed",
            "timestamp": datetime.now().isoformat()
        })
        
        self.log_thought("ACTION", "Healing run and file metrics logged in Coral `cortex_system` tables. System RESTORED.")

        return {
            "incident_found": True,
            "success": True,
            "incident": incident,
            "healing_details": healing_result,
            "pr_number": pr_number,
            "duration_sec": duration,
            "thoughts": self.thought_stream
        }

    def _record_run(self, incident_id, status, duration):
        run_id = f"RUN-{(int(datetime.now().timestamp()) % 1000):03d}"
        self.connector.write_jsonl("cortex_runs.jsonl", {
            "run_id": run_id,
            "incident_id": incident_id,
            "status": status,
            "duration_sec": duration,
            "timestamp": datetime.now().isoformat()
        })

    def restore_system(self):
        """Helper to reset all mock databases back to buggy state for demo replay."""
        self.healer.restore_bug()
        
        # Reset sentry issues to active
        sentry_file = os.path.join(self.connector.demo_data_dir, "sentry_issues.jsonl")
        initial_sentry = {"issue_id": "SEN-404", "error_type": "ZeroDivisionError", "message": "division by zero", "file": "app.py", "line": 9, "status": "active", "timestamp": "2026-05-28T21:10:00Z"}
        with open(sentry_file, "w") as f:
            f.write(json.dumps(initial_sentry) + "\n")

        # Trim Slack back to initial alert
        slack_file = os.path.join(self.connector.demo_data_dir, "slack_history.jsonl")
        initial_slack = [
            {"channel": "#incident-alerts", "username": "sentry-bot", "text": "ALERT: ZeroDivisionError division by zero in app.py", "timestamp": "2026-05-28T21:10:05Z"},
            {"channel": "#dev-chat", "username": "john_doe", "text": "hey i just updated app.py with some optimizations, let me know if anything breaks", "timestamp": "2026-05-28T20:48:00Z"}
        ]
        with open(slack_file, "w") as f:
            for s in initial_slack:
                f.write(json.dumps(s) + "\n")

        logger.info("Demo environment successfully restored to buggy state.")

if __name__ == "__main__":
    agent = CortexSREAgent()
    agent.restore_system()
    res = agent.execute_autopilot()
    print("Execution complete. Success:", res.get("success"))
