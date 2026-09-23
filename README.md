# Run the complete local workspace (Windows)

Double-click **Start Career Pilot.cmd** in this folder. First launch installs missing Python packages, downloads the Naukri client, builds the frontend, and opens **http://127.0.0.1:8765**. Requires Python 3.12+, Node.js 22+, Git, and internet for installation. Keep the server window open while the agent runs.

1. Start Ollama or LM Studio.
2. In **Agent settings**, select your provider, load model IDs, choose a chat model and an embedding model, then **Save & test models**.
3. Save your Naukri credentials and click **Test login**. Complete any verification on Naukri if requested.
4. Upload your resume, review its extracted facts, and save the profile.
5. Set target roles, location, match threshold, and application limit. **Run agent** prepares resumes by default. Enable automatic submission in preferences to submit qualifying Naukri Easy Apply applications.

Runs continue in the local server after closing the browser tab. Reopening restores run activity. Pausing finishes the current action first. Restarting never resumes interrupted applications automatically.

Naukri Easy Apply uses the resume saved in your Naukri account; keep it current. Tailored resumes can be downloaded. External employer forms are prepared for review and are not reported as submitted. Screening questions, MFA, and blocked pages require your attention.

Resumes, provider settings, credentials, and submission history are local and excluded from Git. Keys are never returned to the browser. The server binds only to loopback. The separately hosted preview does not run this local agent.

If installation fails, the launcher keeps its window open with the error. If submission is interrupted, review employer/Naukri history before retrying; uncertain attempts are blocked to prevent duplicates.

Tests: `python -m pytest tests/test_local_workspace.py tests/test_bulk_apply.py tests/test_llm_providers.py tests/test_model_catalog.py tests/test_source_document.py`. Set `CAREER_PILOT_LIVE_MODEL_TEST=1` to run `tests/test_live_local_model.py` against a live model. This test uses synthetic data and never submits applications.

---

# Career-Pilot

AI-powered job search and application management. Combines resume matching, Naukri job discovery, and an application workflow dashboard.

## Setup

### 1. Python backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. NopeRi (Naukri client)

```bash
git clone --depth 1 https://github.com/Traverser25/NopeRi.git third_party/NopeRi
```

### 3. Environment

Create `.env` in the project root:

```
NAUKRI_USERNAME=your_naukri_email
NAUKRI_PASSWORD=your_naukri_password
```

### 4. Frontend

```bash
cd frontend
npm install
```

## Run

**Terminal 1 — API:**

```bash
uvicorn app.main:app --reload
```

**Terminal 2 — Dashboard:**

```bash
cd frontend
npm run dev
```

Open http://localhost:5173

## API

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Health check |
| `GET /applications` | List all applications |
| `POST /jobs/search` | Search Naukri, evaluate, queue applications |
| `POST /applications/{id}/tailor` | Generate a grounded tailored resume + ATS score |
| `POST /applications/{id}/company-apply` | Prepare tailored DOCX and company/Naukri apply URL |
| `GET /applications/{id}/resume-file` | Download the tailored DOCX |
| `POST /applications/{id}/interview` | Move to interview |
| `POST /applications/{id}/offer` | Mark offer received |
| `POST /applications/{id}/reject` | Reject application |

## Tests

```bash
pytest -v
```

## New Career Pilot workspace

The new professional web app is in `career-pilot-web/`. The existing `frontend/` and Python agent are preserved.

The workspace includes resume review, searchable and saved jobs, an application pipeline, agent preferences, and bounded automatic-application runs. It starts in clearly labeled demo mode until the Python agent and model/job-board accounts are connected.

### Run the new workspace

1. Install this repository's Python dependencies and configure its model provider and Naukri account as above.
2. Set `CAREER_PILOT_GATEWAY_TOKEN` to a random secret of at least 32 characters in the backend environment.
3. From the repository root, run `python -m uvicorn pilot_gateway:app --host 127.0.0.1 --port 8000`.
4. In `career-pilot-web/`, copy `.env.example` to `.env`. Set `CAREER_PILOT_API_URL=http://127.0.0.1:8000` and `CAREER_PILOT_API_TOKEN` to the same gateway token.
5. With Node.js 22.13 or newer, run `npm ci`, then `npm run dev` from `career-pilot-web/`.
6. Open `http://localhost:5173`. The old and new frontends use the same default port, so run one at a time.

See [the connection guide](career-pilot-web/public/setup.md) and [workspace README](career-pilot-web/README.md) for details and current limits. `pilot_gateway.py` adds token authentication and durable protection against repeated or uncertain submissions; its source is also included with the standalone workspace.

Live submissions require a reachable model, Naukri sign-in, and any necessary browser setup. Company-site fallback may still need manual completion. No job applications are submitted by installing or starting the app.
