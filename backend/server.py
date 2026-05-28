# server.py - Web Server & API Gateway
import os
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from agent import CortexSREAgent
from connector import DataConnector
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

app = FastAPI(title="CortexSRE Autopilot - Autonomous SRE Cockpit")
agent = CortexSREAgent()
connector = DataConnector()

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
frontend_dir = os.path.join(project_root, "frontend")
app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

class SQLQuery(BaseModel):
    query: str

@app.get("/")
def read_root():
    """Serves the main dashboard Cockpit."""
    index_path = os.path.join(frontend_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    raise HTTPException(status_code=404, detail="Frontend index.html not found.")

@app.get("/api/status")
def get_status():
    """Returns the current state of Sentry, GitHub, Slack, and Healer runs."""
    try:
        # Read the file contents of app.py to render current code in UI
        target_app_path = os.path.join(project_root, "demo_data", "workspace_target", "app.py")
        code_content = ""
        if os.path.exists(target_app_path):
            with open(target_app_path, "r") as f:
                code_content = f.read()

        sentry_issues = connector.run_coral_query("SELECT * FROM mock_obs.sentry_issues")
        github_commits = connector.run_coral_query("SELECT * FROM mock_obs.github_commits")
        slack_history = connector.run_coral_query("SELECT * FROM mock_obs.slack_history")
        agent_runs = connector.run_coral_query("SELECT * FROM cortex_system.runs")
        healed_files = connector.run_coral_query("SELECT * FROM cortex_system.healed_files")

        # Determine overall system health
        active_incidents = [x for x in sentry_issues if x.get("status") == "active"]
        system_status = "CRITICAL" if active_incidents else "HEALTHY"

        return {
            "status": "success",
            "system_status": system_status,
            "sentry_issues": sentry_issues,
            "github_commits": github_commits,
            "slack_history": slack_history,
            "agent_runs": agent_runs,
            "healed_files": healed_files,
            "active_code": code_content
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Status retrieval failed: {str(e)}")

@app.post("/api/trigger")
def trigger_autopilot():
    """Triggers a complete autonomous sensing and self-healing SRE loop."""
    try:
        result = agent.execute_autopilot()
        return {
            "status": "success",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Autopilot trigger failed: {str(e)}")

@app.post("/api/reset")
def reset_system():
    """Resets the environment back to a buggy state for demo replayability."""
    from config import is_production
    if is_production():
        raise HTTPException(
            status_code=403,
            detail="Reset is disabled in production. Use demo mode (CORTEX_ENV=demo) for replay.",
        )
    try:
        agent.restore_system()
        return {
            "status": "success",
            "message": "Environment successfully reset to buggy state for demo."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Environment reset failed: {str(e)}")

@app.post("/api/query")
def execute_query(payload: SQLQuery):
    """Executes an interactive Coral SQL query submitted via the UI SQL Console."""
    try:
        results = connector.run_coral_query(payload.query)
        return {
            "status": "success",
            "results": results
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

if __name__ == "__main__":
    # Start the server on port 8000
    print("Starting CortexSRE FastAPI Server...")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
