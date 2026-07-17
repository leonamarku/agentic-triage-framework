# Agentic Triage Framework

A configurable agentic AI framework that determines the appropriate **level of autonomy** for incoming work items (support tickets, incidents, bug reports) and performs the corresponding action — from fully autonomous handling to human escalation — based on risk, confidence, and organizational policy.

This is a bachelor's thesis prototype. The core research contribution is **not classification** — it is the decision layer that allocates autonomy: the same ticket can produce a different autonomy decision depending on the company profile applied to it (e.g. a FinTech profile escalates payment-related issues that a SaaS Startup profile would handle autonomously).

## How it works

For every incoming ticket, the system:

1. Runs a rule-based **risk assessment** (0–4) using profile-specific signal weights (customers affected, error rate, downtime, payment/security/data-loss flags, customer tier, sentiment, historical incidents).
2. Determines a preliminary **autonomy level** — `autonomous`, `agent_assisted`, or `human_required` — from the risk score against the active company profile's thresholds.
3. Calls an LLM (Groq) to generate the actual work output (customer response draft, investigation notes, or escalation brief) appropriate to that autonomy level, with a rule-based fallback if the LLM call fails.
4. Re-evaluates the final autonomy decision using the LLM's reported confidence, hard security/data-loss overrides, and profile-specific escalation rules (e.g. enterprise customer overrides).
5. Returns risk level, confidence score, autonomy level, escalation status, reasoning, recommended action, and the generated work output.

A dedicated `/tickets/process/compare/{ticket_id}` endpoint runs the same ticket through every registered company profile at once and reports whether the autonomy decision diverged — the central experiment for the thesis.

## Tech stack

| Layer | Technology |
|---|---|
| Backend | FastAPI, Pydantic / pydantic-settings, pandas |
| Agent / LLM | Groq API (`llama-3.3-70b-versatile` by default) |
| Frontend | React 18, Vite, Tailwind CSS |
| Data | CSV support-ticket datasets (Kaggle-style, simulating an incoming work stream) |

## Project structure

```
app/
  main.py                    FastAPI app entry point
  config.py                  Settings loaded from .env
  models/                    Pydantic models (ticket, profile)
  routers/                   /tickets and /profiles API routes
  services/
    agent.py                 LLM orchestration + rule-based fallback
    autonomy_engine.py        Risk + confidence → autonomy decision
    risk_assessor.py          Rule-based risk scoring
    dataset.py                Loads and serves the CSV dataset
    profile_registry.py       Loads company profiles from profiles/
data/                        Simulated incoming ticket datasets (CSV)
profiles/                    Company profile configs (default, fintech, saas_startup)
frontend/                    React + Vite dashboard
requirements.txt             Backend Python dependencies
run.sh                       Convenience script to install deps + start the API
```

## Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- A free [Groq API key](https://console.groq.com/keys)

## Setup

### 1. Clone and configure environment variables

```bash
git clone <this-repo-url>
cd <repo-folder>
cp .env.example .env
```

Open `.env` and fill in your own Groq API key:

```
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
DATASET_PATH=data/Support_tickets.csv
APP_ENV=development
LOG_LEVEL=INFO
```

Never commit `.env` — it's already excluded via `.gitignore`.

### 2. Run the backend

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Or simply:

```bash
./run.sh
```

The API is served at `http://localhost:8000` (interactive docs at `/docs`).

### 3. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

The dashboard is served at `http://localhost:5173` and proxies all `/api/*` calls to the backend at `localhost:8000` (see `frontend/vite.config.js`).

## Key API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/tickets/info` | Dataset statistics |
| GET | `/tickets/{ticket_id}` | Retrieve a raw ticket |
| POST | `/tickets/{ticket_id}/process?profile_id=...` | Run the full agent pipeline on a specific ticket |
| POST | `/tickets/process/random?profile_id=...` | Process a random ticket |
| POST | `/tickets/process/batch?n=5&profile_id=...` | Process N tickets and summarize autonomy distribution |
| POST | `/tickets/process/compare/{ticket_id}` | Compare the same ticket across all company profiles |
| GET | `/profiles` | List all registered company profiles |
| GET | `/profiles/{profile_id}` | Retrieve a specific profile's full configuration |
| GET | `/health` | Health check |

## Deployment (Render)

The backend (FastAPI) and frontend (Vite build) deploy as two separate Render services:

### Backend — Render Web Service

1. Create a new **Web Service** on [Render](https://render.com), pointing at this repo.
2. Build command: `pip install -r requirements.txt`
3. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Set environment variables in the Render dashboard (do **not** upload `.env`):
   - `GROQ_API_KEY` — your Groq API key
   - `GROQ_MODEL` — e.g. `llama-3.3-70b-versatile`
   - `DATASET_PATH` — e.g. `data/Support_tickets.csv`
   - `APP_ENV` — `production`
   - `LOG_LEVEL` — `INFO`
   - `PYTHON_VERSION` — e.g. `3.11.9` (pins the Python version Render uses; without it Render picks a default that may not match what this project was tested on)
5. Note the deployed backend URL (e.g. `https://your-backend.onrender.com`).

### Frontend — Render Static Site

1. Create a new **Static Site** on Render, pointing at this repo, root directory `frontend/`.
2. Build command: `npm install && npm run build`
3. Publish directory: `dist`
4. Set a build-time environment variable `VITE_API_BASE` to your deployed backend URL from the step above (e.g. `https://your-backend.onrender.com`). The frontend's API client (`frontend/src/api.js`) reads this at build time and falls back to the local dev proxy path (`/api`) if it isn't set — this is the only change needed to point the built site at a real backend instead of `localhost:8000`.

## Notes for graders / reviewers

- `ARCHITECTURE_DESIGN.md`, `PHASE1_ANALYSIS_PHASE2_DESIGN.md`, and `PHASE2_REVIEW.md` document the design rationale and evolution of the framework across phases.
- Company profiles (`profiles/*.json`) are the mechanism for organizational adaptability referenced in the thesis: identical tickets can yield different autonomy decisions depending on which profile is active.
