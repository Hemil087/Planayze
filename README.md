# Planalyze

**AI-powered floor plan analysis for apartment buyers.**

Upload a floor plan → get a structured, traceable pros & cons report grounded in architecture standards — not LLM guesswork.

---

## What It Does

Most buyers can't read a floor plan critically. Planalyze fills that gap. You upload a floor plan image, and the system:

1. Extracts room geometry as structured JSON using Gemini 2.5 Flash (vision only — no judgments)
2. Runs a deterministic rule engine over the extracted geometry
3. Applies a consistency filter (runs the pipeline N times, suppresses non-recurring findings)
4. Produces a scored pros/cons report where every finding cites the room and rule that triggered it
5. Lets you chat with your floor plan — ask geometry questions answered by deterministic tools

The result is a report a buyer can act on — not a generic paragraph that changes every time you ask.

---

## Architecture

```
Floor Plan Image
      │
      ▼
┌──────────────────────┐
│  Gemini 2.5 Flash    │  ← Extracts geometry only (rooms, dims, doors, windows)
│  + Schema Validator  │  ← Rejects / retries on schema violations
└────────┬─────────────┘
         │  Validated Extraction JSON
         ▼
┌─────────────────────────────────┐
│         Rule Engine              │
│  space_efficiency  ventilation  │
│  privacy_gradient  circulation  │
│  adjacency         size_adequacy│
└────────┬────────────────────────┘
         │  Raw Findings
         ▼
┌──────────────────┐
│  Consistency     │  ← Runs N times, keeps only recurring findings
│  Filter          │  ← Hallucination mitigation
└────────┬─────────┘
         │  Hardened Findings
         ▼
┌──────────────────┐
│  Report Builder  │  ← Scored JSON + Gemini-written summary
└────────┬─────────┘
         │
         ├──────────────────────┐
         ▼                      ▼
┌──────────────────┐   ┌──────────────────┐
│  React Frontend  │   │  Chat Agent      │
│  Report cards    │   │  Geometry tools   │
│  Score badge     │   │  via Gemini FC    │
└──────────────────┘   └──────────────────┘
```

**Key design decision:** Gemini is trusted only to *see*, never to *reason about rules*. All analysis is deterministic Python over the extracted geometry. This is what makes findings verifiable.

---

## Rule Categories

Each rule is grounded in the **National Building Code of India (NBC 2016)** or **RERA** definitions, so cons are defensible standards — not opinions.

| Category | What It Checks |
|---|---|
| **Space Efficiency** | Carpet-to-built-up ratio, corridor/dead space %, room proportions |
| **Ventilation & Light** | External wall exposure, window-to-floor ratio, cross-ventilation |
| **Privacy Gradient** | Guest sightlines to bedrooms, master bedroom placement, entrance exposure |
| **Circulation** | Do you cross living room to reach bedrooms? Connectivity path analysis |
| **Functional Adjacency** | Kitchen near bathroom, toilet facing dining, bedroom near lift shaft |
| **Size Adequacy** | Room dimensions vs. NBC minimums, furniture feasibility checks |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite + Tailwind CSS |
| Backend | FastAPI (Python 3.11) |
| LLM | Gemini 2.5 Flash via Vertex AI |
| Database | PostgreSQL + async SQLAlchemy + JSONB |
| Validation | Pydantic v2 |
| Infrastructure | Docker Compose |

---

## Project Structure

```
planalyze/
├── docker-compose.yml              # Backend + PostgreSQL services
│
├── frontend/
│   └── src/
│       ├── App.jsx                  # Main app — upload → analyze → report flow
│       ├── components/
│       │   ├── upload/              # Drag & drop upload zone
│       │   ├── report/              # ReportCard, FindingItem, ScoreBadge
│       │   └── chat/                # ChatPanel, ChatMessage
│       └── utils/                   # API client, formatters, constants
│
└── backend/
    └── app/
        ├── api/routes/              # /upload  /analysis  /report  /chat
        ├── core/                    # Gemini client, DB, config, storage
        ├── services/
        │   ├── extractor/           # Gemini extraction + schema validation + retry
        │   ├── engine/rules/        # One file per rule category (6 files)
        │   ├── report/              # Report builder + Gemini summary writer
        │   └── chat/                # Chat agent + 5 geometry tools
        ├── schemas/                 # Pydantic schemas — the shared extraction contract
        └── evals/                   # Ground truth labels + precision metrics
```

---

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Node.js 18+
- A Google Cloud project with Vertex AI enabled
- A service account key with Vertex AI permissions

### Backend (Docker)

```bash
# 1. Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env:
#   DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/planalyze
#   PROJECT_ID=your-gcp-project
#   REGION=asia-south1
#   GOOGLE_APPLICATION_CREDENTIALS_JSON={"type":"service_account",...}  (single-line JSON)

# 2. Start services
docker-compose up --build -d

# 3. Run migrations
docker-compose exec backend alembic upgrade head

# 4. Verify
curl http://localhost:8000/health
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Backend runs on `http://localhost:8000`, frontend on `http://localhost:5173`.

The Vite dev server proxies `/api/*` to the backend automatically — no CORS configuration needed in development.

---

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/upload` | Upload floor plan image, returns `plan_id` |
| `POST` | `/analysis/{plan_id}` | Start analysis (async, returns 202) |
| `GET` | `/analysis/{plan_id}/status` | Poll analysis status |
| `GET` | `/report/{plan_id}` | Fetch structured findings report |
| `POST` | `/chat/{plan_id}` | Chat with the floor plan using geometry tools |
| `GET` | `/health` | Health check |

---

## Chat Agent — Geometry Tools

The chat endpoint uses Gemini function calling with 5 deterministic tools. The LLM decides *which* tool to call; the tool returns factual data; the LLM narrates it.

| Tool | What It Does |
|---|---|
| `room_area` | Returns area and dimensions of a room |
| `fits_furniture` | Checks if furniture fits with clearance (knows standard bed/sofa/desk sizes) |
| `path_between` | BFS shortest path between two rooms through door connections |
| `sun_exposure` | Reports wall orientations → morning/evening sun based on cardinal direction |
| `list_rooms` | Lists all rooms with type and dimensions |

---

## Evaluation

The `evals/` folder contains a hand-labeled ground truth set. Run metrics with:

```bash
docker-compose exec backend python -m app.evals.eval_runner
```

This reports per-rule precision, recall, and hallucination rate. The eval runs the full production pipeline (extraction + consistency filter) per plan.

Targets: per-rule precision ≥ 0.80, hallucination rate < 0.10.

---

## Build Phases

| Phase | Description | Status |
|---|---|---|
| 0 | Docker + FastAPI + PostgreSQL setup | ✅ |
| 1 | Pydantic extraction schema contract | ✅ |
| 2 | SQLAlchemy models + Alembic migrations | ✅ |
| 3 | Upload route + image storage | ✅ |
| 4 | Gemini extractor + schema validation + retry | ✅ |
| 5 | Deterministic rule engine (6 categories) | ✅ |
| 6 | Consistency filter (N runs, threshold suppression) | ✅ |
| 7 | Report builder + Gemini summary writer | ✅ |
| 8 | Analysis route (async) + report route | ✅ |
| 9 | Eval framework (metrics, runner, ground truth) | ✅ |
| 10 | Chat agent with geometry tool calling | ✅ |
| — | React frontend | ✅ |

---

## Why Not Just Use ChatGPT?

ChatGPT can comment on a floor plan. Planalyze produces *verifiable* analysis:

- **Schema-validated extraction** — Gemini returns structured JSON matching a frozen Pydantic contract, with retry on violations
- **Deterministic rule engine** — every finding is produced by Python code, not LLM reasoning. Same extraction → same findings, every time
- **Self-consistency filtering** — runs the pipeline N times, suppresses findings that don't recur above a threshold
- **Measurable precision** — a hand-labeled eval set with per-rule precision and hallucination rate metrics
- **Evidence-backed findings** — every finding cites the specific room, rule, and standard that triggered it
- **Tool-backed chat** — geometry questions are answered by deterministic functions, not hallucination

> *"ChatGPT is the model. I built the system around the model."*

---

## Docker Commands

```bash
docker-compose up --build -d          # Start all services
docker-compose logs -f backend        # View backend logs
docker-compose exec backend alembic upgrade head   # Run migrations
docker-compose exec backend python -m app.evals.eval_runner  # Run evals
docker-compose down                   # Stop everything
docker-compose down -v                # Stop + wipe DB volume
```

