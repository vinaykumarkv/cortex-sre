"""One-off connectivity check — run: python check_connectivity.py"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from config import get_mode, use_ollama, ollama_model

def main():
    print("=== CortexSRE connectivity check ===\n")
    print(f"CORTEX_ENV -> {get_mode()}")
    print(f"USE_OLLAMA -> {use_ollama()} | model: {ollama_model()}\n")

    # Ollama
    try:
        from llm.ollama_client import is_available
        ok = is_available()
        print(f"Ollama: {'OK' if ok else 'NOT READY'}")
        if not ok:
            print("  -> Run: ollama serve  &&  ollama pull llama3.2")
    except Exception as e:
        print(f"Ollama: ERROR — {e}")

    # Sentry
    print()
    try:
        from integrations.sentry_client import fetch_active_issues
        issues = fetch_active_issues()
        print(f"Sentry: OK | unresolved issues: {len(issues)}")
        for i, x in enumerate(issues[:3]):
            print(f"  [{i+1}] id={x.get('issue_id')} type={x.get('error_type')} file={x.get('file')}")
    except Exception as e:
        print(f"Sentry: FAIL — {type(e).__name__}: {e}")

    # GitHub
    print()
    try:
        from integrations.github_client import fetch_all_recent
        commits = fetch_all_recent(5)
        print(f"GitHub: OK | recent commits: {len(commits)}")
        for c in commits[:3]:
            msg = (c.get("message") or "")[:50]
            print(f"  sha={c.get('commit_sha')} author={c.get('author')} msg={msg}")
    except Exception as e:
        print(f"GitHub: FAIL — {type(e).__name__}: {e}")

    # Slack auth
    print()
    try:
        import httpx
        token = os.environ.get("SLACK_BOT_TOKEN", "")
        r = httpx.get(
            "https://slack.com/api/auth.test",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        )
        d = r.json()
        if d.get("ok"):
            print(f"Slack auth.test: OK | team={d.get('team')} bot={d.get('user')}")
        else:
            print(f"Slack auth.test: FAIL | {d.get('error')}")
    except Exception as e:
        print(f"Slack auth: FAIL — {e}")

    # Slack history
    print()
    try:
        from integrations.slack_client import fetch_all_configured_history
        msgs = fetch_all_configured_history()
        print(f"Slack history: OK | messages: {len(msgs)}")
        for m in msgs[:2]:
            text = (m.get("text") or "")[:60]
            print(f"  @{m.get('username')} in {m.get('channel')}: {text}")
    except Exception as e:
        print(f"Slack history: FAIL — {type(e).__name__}: {e}")

    # Production join
    print()
    try:
        from connector import DataConnector
        c = DataConnector()
        q = (
            "SELECT sentry.issue_id, sentry.error_type, sentry.file, "
            "github.commit_sha, slack.username "
            "FROM mock_obs.sentry_issues AS sentry "
            "LEFT JOIN mock_obs.github_commits AS github ON github.file = sentry.file "
            "LEFT JOIN mock_obs.slack_history AS slack ON slack.text LIKE '%app.py%' "
            "WHERE sentry.status = 'active'"
        )
        rows = c.run_coral_query(q)
        print(f"Production JOIN: OK | rows: {len(rows)}")
        if rows:
            print(f"  first row issue_id={rows[0].get('issue_id')} file={rows[0].get('file')}")
    except Exception as e:
        print(f"Production JOIN: FAIL — {type(e).__name__}: {e}")

    print("\n=== Done ===")


if __name__ == "__main__":
    main()
