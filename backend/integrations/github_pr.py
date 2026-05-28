# github_pr.py — Create real GitHub branches and pull requests after healing
import logging
import os
import re
import subprocess
from pathlib import Path

import httpx

from integrations.github_client import _headers
from integrations.http_util import make_client

logger = logging.getLogger(__name__)


def _git(args: list[str], cwd: str, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def _enabled() -> bool:
    return os.getenv("GITHUB_PR_ENABLED", "true").lower() in ("1", "true", "yes")


def _safe_branch(issue_id: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]", "-", str(issue_id))[:24]
    return f"cortexsre/fix-{slug}"


def create_healing_pull_request(
    project_root: str,
    incident: dict,
    healing_result: dict,
) -> dict | None:
    """
    Commit healed workspace_target file, push branch, open a GitHub PR.
    Returns {pr_number, html_url, branch} or None on failure (non-fatal).
    """
    if not _enabled():
        logger.info("GitHub PR creation disabled (GITHUB_PR_ENABLED=false).")
        return None

    owner = os.environ.get("GITHUB_OWNER")
    repo = os.environ.get("GITHUB_REPO")
    token = os.environ.get("GITHUB_TOKEN")
    base_branch = os.environ.get("GITHUB_DEFAULT_BRANCH", "main")

    if not all([owner, repo, token]):
        logger.warning("GitHub PR skipped: GITHUB_OWNER, GITHUB_REPO, or GITHUB_TOKEN missing.")
        return None

    target_file = incident.get("file") or "app.py"
    rel_path = Path("demo_data") / "workspace_target" / target_file
    abs_path = Path(project_root) / rel_path
    if not abs_path.exists():
        logger.warning("GitHub PR skipped: healed file not found at %s", rel_path)
        return None

    branch = _safe_branch(incident.get("issue_id", "incident"))
    error_type = incident.get("error_type", "Error")
    issue_id = incident.get("issue_id", "unknown")

    commit_msg = (
        f"fix(cortexsre): resolve {error_type} in {target_file}\n\n"
        f"Automated healing for Sentry incident {issue_id}.\n"
        f"Attempts: {healing_result.get('attempts', 1)}\n"
        f"{healing_result.get('explanation', '')}"
    ).strip()

    git_env = os.environ.copy()
    git_env["GIT_TERMINAL_PROMPT"] = "0"

    # Ensure we're on latest base and create branch
    steps = [
        (["fetch", "origin", base_branch], "fetch"),
        (["checkout", base_branch], "checkout base"),
        (["pull", "origin", base_branch], "pull"),
        (["checkout", "-B", branch], "create branch"),
        (["add", str(rel_path).replace("\\", "/")], "stage"),
    ]

    for args, label in steps:
        result = _git(args, project_root, git_env)
        if result.returncode != 0 and label in ("pull", "fetch"):
            logger.warning("Git %s warning: %s", label, result.stderr.strip()[:200])
        elif result.returncode != 0 and label != "pull":
            logger.error("Git %s failed: %s", label, result.stderr.strip())
            return None

    status = _git(["status", "--porcelain"], project_root, git_env)
    if not status.stdout.strip():
        logger.warning("GitHub PR skipped: no changes to commit.")
        return None

    commit = _git(["commit", "-m", commit_msg], project_root, git_env)
    if commit.returncode != 0:
        logger.error("Git commit failed: %s", commit.stderr.strip())
        return None

    push_url = f"https://x-access-token:{token}@github.com/{owner}/{repo}.git"
    push = _git(["push", "-u", push_url, branch], project_root, git_env)
    if push.returncode != 0:
        logger.error("Git push failed: %s", push.stderr.strip()[:300])
        return None

    pr_title = f"fix: {error_type} in {target_file} (CortexSRE #{issue_id})"
    pr_body = (
        f"## CortexSRE Autonomous Fix\n\n"
        f"- **Incident:** `{issue_id}`\n"
        f"- **Error:** `{error_type}`\n"
        f"- **File:** `{rel_path}`\n"
        f"- **Healing attempts:** {healing_result.get('attempts', 1)}\n\n"
        f"### Explanation\n{healing_result.get('explanation', 'Automated patch verified by pytest.')}\n\n"
        f"---\n*Opened by CortexSRE Autopilot — review before merge.*"
    )

    try:
        with make_client() as client:
            resp = client.post(
                f"https://api.github.com/repos/{owner}/{repo}/pulls",
                headers=_headers(),
                json={
                    "title": pr_title,
                    "head": branch,
                    "base": base_branch,
                    "body": pr_body,
                },
            )
            if resp.status_code == 422 and "already exists" in resp.text.lower():
                # PR may already exist for this branch — fetch existing
                pulls = client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/pulls",
                    headers=_headers(),
                    params={"head": f"{owner}:{branch}", "state": "open"},
                )
                if pulls.status_code == 200 and pulls.json():
                    pr = pulls.json()[0]
                    return {
                        "pr_number": pr.get("number"),
                        "html_url": pr.get("html_url"),
                        "branch": branch,
                    }
            resp.raise_for_status()
            pr = resp.json()
    except Exception as e:
        logger.error("GitHub PR API failed: %s", e)
        return None

    logger.info("Opened PR #%s %s", pr.get("number"), pr.get("html_url"))
    return {
        "pr_number": pr.get("number"),
        "html_url": pr.get("html_url"),
        "branch": branch,
    }
