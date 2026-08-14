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
