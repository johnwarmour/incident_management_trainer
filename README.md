# Incident Management Trainer

AI-powered ITIL incident management training. Practice all six ITIL checkpoints through realistic, Claude-generated scenarios — available as a web app or terminal TUI.

## What it does

You play the role of an incident manager responding to a live production incident. Claude acts as your monitoring system, stakeholders, and dispatcher — feeding you alerts, answering investigation queries, and escalating pressure as time goes on. You work through six structured ITIL checkpoints, and receive a scored debrief at the end.

**Checkpoints:**
1. **Detection** — Acknowledge the alert, log the incident, identify affected systems
2. **Triage** — Assess impact and urgency, set priority (P1–P4 via ITIL matrix)
3. **Escalation** — Decide who to bring in and brief them correctly
4. **Communication** — Notify stakeholders, set update cadence
5. **Resolution** — Find and verify the fix, document it
6. **Closure** — Close the ticket, raise PIR if P1/P2, capture lessons learned

**Scenarios:**
- Database outage
- DDoS attack
- Certificate expiry
- Deployment regression
- Third-party API failure
- Random (surprise)

## Setup

**Prerequisites:** Python 3.9+, Node.js 18+, an Anthropic API key

```bash
git clone git@github.com:johnwarmour/incident_management_trainer.git
cd incident_management_trainer

cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

**Install Python dependencies:**
```bash
pip install -e .
```

**Install frontend dependencies:**
```bash
cd frontend && npm install
```

## Running

### Web UI

```bash
# Terminal 1 — API server
python3 -m uvicorn backend.main:app --reload

# Terminal 2 — frontend dev server
cd frontend && npm run dev
```

Open `http://localhost:5173`.

### Terminal TUI

```bash
python3 -m tui.app
```

Keybindings: `Enter` send message, `Ctrl+S` skip checkpoint, `Ctrl+Q` quit.

## Project structure

```
incident-sim/
├── backend/
│   ├── main.py              # FastAPI routes
│   ├── core/
│   │   ├── claude.py        # Anthropic SDK client (prompt caching)
│   │   ├── scenario.py      # Seed templates + Claude expansion
│   │   ├── session.py       # ITIL checkpoint state machine
│   │   └── scoring.py       # Per-checkpoint evaluation + debrief
│   └── models/
│       └── schemas.py       # Pydantic models
├── frontend/
│   └── src/
│       ├── App.tsx
│       ├── api.ts
│       └── components/
│           ├── IncidentTicket.tsx   # Live ITIL ticket panel
│           ├── ChatPane.tsx         # Free-form chat
│           ├── CheckpointPanel.tsx  # Current checkpoint goals + score
│           └── Debrief.tsx          # End-of-session scorecard
└── tui/
    └── app.py               # Textual terminal UI (same backend, no HTTP)
```

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/session/start` | Start a new session (optionally pass `scenario_type`) |
| `POST` | `/session/{id}/input` | Send a user message |
| `GET`  | `/session/{id}` | Get current session state |
| `POST` | `/session/{id}/advance` | Force-advance the current checkpoint |
| `GET`  | `/session/{id}/debrief` | Get end-of-session report (session must be complete) |
| `GET`  | `/scenarios` | List available scenario types |

## Tech stack

- **Backend:** Python, FastAPI, Anthropic SDK (`claude-opus-4-6`)
- **Frontend:** React, Vite, TypeScript
- **TUI:** [Textual](https://textual.textualize.io/)
- **Models:** Pydantic v2

Prompt caching is used on the system prompt + scenario context, so API costs stay low across the multi-turn session.
