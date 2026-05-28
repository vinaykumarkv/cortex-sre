#!/usr/bin/env python3
"""Write portable file:// paths into Coral YAML specs for this machine."""
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEMO_DATA = PROJECT_ROOT / "demo_data"
LIVE_CACHE = DEMO_DATA / "live_cache"
LIVE_CACHE.mkdir(parents=True, exist_ok=True)

CORAL_DIR = PROJECT_ROOT / "coral"


def file_uri(folder: Path) -> str:
    return folder.resolve().as_uri() + "/"


def write_mock_sources() -> None:
    uri = file_uri(DEMO_DATA)
    content = f"""name: mock_obs
version: 0.1.0
dsl_version: 3
backend: file
test_queries:
  - SELECT * FROM mock_obs.sentry_issues LIMIT 1
  - SELECT * FROM mock_obs.github_commits LIMIT 1
  - SELECT * FROM mock_obs.slack_history LIMIT 1
tables:
  - name: sentry_issues
    format: jsonl
    source:
      location: {uri}
      glob: "sentry_issues.jsonl"
    columns:
      - {{name: issue_id, type: Utf8}}
      - {{name: error_type, type: Utf8}}
      - {{name: message, type: Utf8}}
      - {{name: file, type: Utf8}}
      - {{name: line, type: Int64}}
      - {{name: status, type: Utf8}}
      - {{name: timestamp, type: Utf8}}
  - name: github_commits
    format: jsonl
    source:
      location: {uri}
      glob: "github_commits.jsonl"
    columns:
      - {{name: commit_sha, type: Utf8}}
      - {{name: author, type: Utf8}}
      - {{name: message, type: Utf8}}
      - {{name: file, type: Utf8}}
      - {{name: timestamp, type: Utf8}}
  - name: slack_history
    format: jsonl
    source:
      location: {uri}
      glob: "slack_history.jsonl"
    columns:
      - {{name: channel, type: Utf8}}
      - {{name: username, type: Utf8}}
      - {{name: text, type: Utf8}}
      - {{name: timestamp, type: Utf8}}
"""
    (CORAL_DIR / "mock_sources.yaml").write_text(content, encoding="utf-8")
    print("Wrote coral/mock_sources.yaml")


def write_live_obs() -> None:
    uri = file_uri(LIVE_CACHE)
    content = f"""name: live_obs
version: 0.1.0
dsl_version: 3
backend: file
test_queries:
  - SELECT * FROM live_obs.sentry_issues LIMIT 1
tables:
  - name: sentry_issues
    format: jsonl
    source:
      location: {uri}
      glob: "sentry_issues.jsonl"
    columns:
      - {{name: issue_id, type: Utf8}}
      - {{name: error_type, type: Utf8}}
      - {{name: message, type: Utf8}}
      - {{name: file, type: Utf8}}
      - {{name: line, type: Int64}}
      - {{name: status, type: Utf8}}
      - {{name: timestamp, type: Utf8}}
  - name: github_commits
    format: jsonl
    source:
      location: {uri}
      glob: "github_commits.jsonl"
    columns:
      - {{name: commit_sha, type: Utf8}}
      - {{name: author, type: Utf8}}
      - {{name: message, type: Utf8}}
      - {{name: file, type: Utf8}}
      - {{name: timestamp, type: Utf8}}
  - name: slack_history
    format: jsonl
    source:
      location: {uri}
      glob: "slack_history.jsonl"
    columns:
      - {{name: channel, type: Utf8}}
      - {{name: username, type: Utf8}}
      - {{name: text, type: Utf8}}
      - {{name: timestamp, type: Utf8}}
"""
    (CORAL_DIR / "live_obs.yaml").write_text(content, encoding="utf-8")
    print("Wrote coral/live_obs.yaml")


def write_cortex_system() -> None:
    uri = file_uri(DEMO_DATA)
    content = f"""name: cortex_system
version: 0.1.0
dsl_version: 3
backend: file
test_queries:
  - SELECT * FROM cortex_system.runs LIMIT 1
tables:
  - name: runs
    format: jsonl
    source:
      location: {uri}
      glob: "cortex_runs.jsonl"
    columns:
      - {{name: run_id, type: Utf8}}
      - {{name: incident_id, type: Utf8}}
      - {{name: status, type: Utf8}}
      - {{name: duration_sec, type: Int64}}
      - {{name: timestamp, type: Utf8}}
  - name: healed_files
    format: jsonl
    source:
      location: {uri}
      glob: "cortex_healed.jsonl"
    columns:
      - {{name: healed_id, type: Utf8}}
      - {{name: file, type: Utf8}}
      - {{name: lines_changed, type: Int64}}
      - {{name: test_status, type: Utf8}}
      - {{name: timestamp, type: Utf8}}
"""
    (CORAL_DIR / "cortex_system.yaml").write_text(content, encoding="utf-8")
    print("Wrote coral/cortex_system.yaml")


def main():
    write_mock_sources()
    write_live_obs()
    write_cortex_system()
    print("\nNext, register specs with Coral CLI:")
    print("  coral spec apply coral/mock_sources.yaml")
    print("  coral spec apply coral/live_obs.yaml")
    print("  coral spec apply coral/cortex_system.yaml")


if __name__ == "__main__":
    main()
