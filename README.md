# 🧠 CortexSRE — Autonomous SRE with Coral SQL

> **When production breaks, engineers become human JOIN tables** — jumping between Sentry, GitHub, and Slack. **CortexSRE** uses **Coral SQL** to unify those signals in one query, then **heals the codebase**, **opens a real GitHub PR**, and **notifies Slack** — in one autopilot loop.

[![Coral](https://img.shields.io/badge/Coral-SQL%20joins-blue)](coral/)
[![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688)](https://fastapi.tiangolo.com/)
[![Ollama](https://img.shields.io/badge/Ollama-llama3.2-000)](https://ollama.com/)

---

## Demo

1. `python scripts/setup_coral.py` → `coral spec apply coral/*.yaml`
2. `cd backend && python server.py` → open **http://localhost:8000**
3. Click **Run Autopilot** — watch the thought stream, code fix, and **live GitHub PR**
4. Run a Coral query in the **SQL Console**: `SELECT * FROM cortex_system.runs`

---

### 🏴‍☠️ Potential Impact

**Problem:** Incident response is fragmented. Mean time to repair (MTTR) suffers when engineers manually correlate alerts, commits, and chat.

**Solution:** CortexSRE treats observability as a **relational layer**:

- One **Coral SQL JOIN** across Sentry + GitHub + Slack replaces three separate UI hunts
- An **autonomous agent** closes the loop: diagnose → patch → test → PR → notify

**Who benefits:** SRE teams, platform engineers, and hackathon demos of “self-healing” infrastructure.

---

### ⚓ Idea

| Idea | How we're different |
|------|---------------------|
| **Navigator / IncidentMind style joins** | We don't stop at the dashboard — we **act** on the join result |
| **Coral as the sensor layer** | Same SQL dialect for **mock demo** and **live production** (`mock_obs` vs `live_obs`) |
| **Meta-monitoring** | Agent logs runs to `cortex_system.runs` — **query the bot's own MTTR** with Coral |
| **Local LLM healing** | Ollama (`llama3.2`) patches code without sending source to a cloud LLM |

---

### 🗺️ Learning

Built while learning Coral's file-backed specs, cross-source SQL, and CLI workflow:

- Started with **JSONL + Python fallback** for reliable demos
- Graduated to **`coral sql`** with generated specs (`scripts/setup_coral.py`)
- Added **production REST adapters** (Sentry, GitHub, Slack) that **feed Coral's cache** (`demo_data/live_cache/`)
- Documented pitfalls (`.env` `#` comments, Slack channel IDs, Sentry `project:write`)

See [PROJECT_GUIDE.md](./PROJECT_GUIDE.md) and [PRODUCTION_SETUP.md](./PRODUCTION_SETUP.md) for deep dives.

---

### ⚔️ Technical Implementation

```
Sentry ──┐     ┌──► Coral CLI (SQL joins) ──► CortexSRE Agent
GitHub ──┼────►│         ▲
Slack  ──┘     │    live_cache JSONL
               └──► REST fallback (parallel fetch, 60s timeout)
                         │
                         ▼
              CodeHealer (pytest + Ollama) → git push → GitHub PR API
```

| Layer | Tech |
|-------|------|
| API | FastAPI, `/api/trigger`, `/api/query`, `/api/coral/status` |
| Data | Coral CLI + `integrations/production_data.py` |
| Healing | pytest, Ollama, `demo_data/workspace_target/` |
| Actions | GitHub PR (`integrations/github_pr.py`), Slack post, Sentry resolve |

**Signature Coral query** (autopilot sensing):

```sql
SELECT sentry.issue_id, sentry.error_type, sentry.message, sentry.file, sentry.line,
       github.commit_sha, github.author, github.message AS commit_msg,
       slack.username, slack.text AS slack_msg
FROM mock_obs.sentry_issues AS sentry
LEFT JOIN mock_obs.github_commits AS github ON github.file = sentry.file
LEFT JOIN mock_obs.slack_history AS slack ON slack.text LIKE '%app.py%'
WHERE sentry.status = 'active'
```

In **production**, `mock_obs` is rewritten to `live_obs` after syncing APIs → `demo_data/live_cache/*.jsonl`.

---

### 🎨 Frontend

- **Glassmorphic cockpit** — status badge, diagnostic cards, live code viewer
- **Agent thought stream** — staged logs (SENSING → PLANNING → HEALING → ACTION)
- **Interactive Coral SQL console** — run joins at the bottom of the dashboard
- **Real PR link** in UI when GitHub PR opens successfully

---

### 🪸 Use of Coral

| Coral feature | How CortexSRE uses it |
|---------------|----------------------|
| **SQL interface** | All sensing + UI console queries go through `coral sql --format json` |
| **Cross-source joins** | Sentry ⨝ GitHub ⨝ Slack in one statement |
| **File-backed specs** | `coral/mock_sources.yaml`, `coral/live_obs.yaml`, `coral/cortex_system.yaml` |
| **Caching** | Production APIs → `live_cache` JSONL → Coral reads stable files (TTL on REST cache) |
| **Self-query** | `SELECT * FROM cortex_system.runs` — agent observability |

**Setup Coral (required once per machine):**

```powershell
pip install -r requirements.txt
python scripts/setup_coral.py
coral spec apply coral/mock_sources.yaml
coral spec apply coral/live_obs.yaml
coral spec apply coral/cortex_system.yaml
coral sql "SELECT * FROM mock_obs.sentry_issues LIMIT 5"
```

---

## 🚀 Quick Start

### Demo mode (offline-friendly)

```powershell
copy .env.example .env
# CORTEX_ENV=demo
cd backend
..\ .venv\Scripts\python.exe server.py
```

### Production mode (live Sentry, GitHub, Slack, Ollama)

```powershell
copy .env.example .env
# Fill tokens — see PRODUCTION_SETUP.md
# CORTEX_ENV=production
ollama pull llama3.2
python scripts/setup_coral.py
cd backend
python server.py
```

**Health check:**

```powershell
python backend\check_connectivity.py
```

---

## 📂 Project Structure

```
cortex-sre/
├── backend/
│   ├── server.py              # FastAPI + dashboard
│   ├── agent.py               # Autopilot orchestrator
│   ├── connector.py           # Coral CLI → REST → JSONL
│   ├── healer.py              # pytest + Ollama patches
│   └── integrations/
│       ├── coral_runner.py    # coral sql execution
│       ├── coral_sync.py      # API → live_cache JSONL
│       ├── github_pr.py       # Real PR automation
│       ├── sentry_client.py
│       ├── github_client.py
│       └── slack_client.py
├── coral/                     # Coral metaspecs (generated paths)
├── frontend/                  # Dashboard UI
├── demo_data/                 # JSONL + workspace_target app
├── scripts/setup_coral.py     # Portable Coral YAML paths
└── tests/
```

---

## ⚙️ Key Environment Variables

| Variable | Purpose |
|----------|---------|
| `CORTEX_ENV` | `demo` or `production` |
| `CORAL_USE_CLI` | Prefer `coral sql` (default `true`) |
| `GITHUB_PR_ENABLED` | Open real PR after heal (default `true`) |
| `OLLAMA_MODEL` | e.g. `llama3.2` |
| `SENTRY_*` / `GITHUB_*` / `SLACK_*` | Production API credentials |

**Slack tip:** Use channel IDs (`C0123...`) in `.env` — never `CHANNEL=#name` (the `#` starts a comment).
