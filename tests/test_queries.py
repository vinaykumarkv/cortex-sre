# test_queries.py - Pytest for Coral queries and mock fallback data structures
import os
import sys
import pytest

# Add backend directory to sys path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from connector import DataConnector

@pytest.fixture
def connector():
    return DataConnector(mode="demo")

def test_sentry_issues_structure(connector):
    """Verifies sentry issues query returns correct keys."""
    sql = "SELECT * FROM mock_obs.sentry_issues"
    rows = connector.run_coral_query(sql)
    assert len(rows) > 0
    first_row = rows[0]
    assert "issue_id" in first_row
    assert "error_type" in first_row
    assert "file" in first_row
    assert "status" in first_row
    assert first_row["issue_id"] == "SEN-404"

def test_github_commits_structure(connector):
    """Verifies github commits query returns correct keys."""
    sql = "SELECT * FROM mock_obs.github_commits"
    rows = connector.run_coral_query(sql)
    assert len(rows) > 0
    first_row = rows[0]
    assert "commit_sha" in first_row
    assert "author" in first_row
    assert "file" in first_row

def test_unified_incident_join(connector):
    """Verifies complex SRE join correlates Sentry with GitHub commits and Slack history."""
    sql = (
        "SELECT sentry.issue_id, github.commit_sha, slack.channel "
        "FROM mock_obs.sentry_issues AS sentry "
        "JOIN mock_obs.github_commits AS github ON github.file = sentry.file "
        "JOIN mock_obs.slack_history AS slack ON slack.text LIKE '%app.py%'"
    )
    rows = connector.run_coral_query(sql)
    assert len(rows) > 0
    joined_row = rows[0]
    
    # Assert correlation matches expectations
    assert joined_row["issue_id"] == "SEN-404"
    assert joined_row["commit_sha"] == "a1b2c3d4"
    assert joined_row["author"] == "john_doe"
    assert joined_row["slack_channel"] == "#incident-alerts"
