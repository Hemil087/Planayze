# Planalyze

**AI-powered floor plan analysis for apartment buyers.**

Upload a floor plan → get a structured, traceable pros & cons report grounded in architecture standards — not LLM guesswork.

---

## What It Does

Most buyers can't read a floor plan critically. Planalyze fills that gap. You upload a floor plan image, and the system:

1. Extracts room geometry as structured JSON using Gemini (vision only — no judgments)
2. Runs a deterministic rule engine over the extracted geometry
3. Produces a scored pros/cons report where every finding cites the room and rule that triggered it
4. Highlights findings visually on the floor plan itself

The result is a report a buyer can act on — not a generic paragraph that changes every time you ask.

---

## Architecture

```
Floor Plan Image
      │
      ▼
┌──────────────────────┐
│  Gemini (Vision)     │  ← Extracts geometry only (rooms, dims, doors, windows)
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
│  Report Builder  │  ← Structured JSON + LLM-written human summary
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  React Frontend  │  ← Report cards + visual overlays on the plan
└──────────────────┘
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
| Frontend | React + Vite |
| Backend | FastAPI (Python) |
| LLM | Gemini 1.5 Pro (multimodal extraction) |
| Database | PostgreSQL + JSONB |
| Geometry | Shapely, NumPy |
| Validation | Pydantic v2 |

---

## Project Structure

```
planalyze/
├── frontend/
│   └── src/
│       ├── components/
│       │   ├── upload/        # Floor plan upload UI
│       │   ├── report/        # ReportCard, FindingItem, ScoreBadge
│       │   ├── overlay/       # Visual highlight layer on the plan
│       │   └── chat/          # Phase C — chat with your floor plan
│       ├── pages/             # Home, Analysis, Compare
│       ├── hooks/             # useUpload, useAnalysis, useChat
│       └── store/             # analysisStore, chatStore
│
└── backend/
    └── app/
        ├── api/routes/        # /upload  /analysis  /report  /chat
        ├── core/              # Gemini client, DB, config
        ├── services/
        │   ├── extractor/     # Gemini extraction + schema validation + retry
        │   ├── engine/rules/  # One file per rule category
        │   ├── report/        # Report builder + LLM summary writer
        │   └── chat/          # Chat agent + geometry tools (Phase C)
        ├── schemas/           # Pydantic schemas — the shared extraction contract
        └── evals/             # Ground truth labels + precision metrics
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL
- Gemini API key

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add GEMINI_API_KEY and DATABASE_URL
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env          # add VITE_API_URL
npm run dev
```

Backend runs on `http://localhost:8000`, frontend on `http://localhost:5173`.

---

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/upload` | Upload floor plan image, returns `plan_id` |
| `POST` | `/analysis/{plan_id}` | Run extraction + rule engine |
| `GET` | `/report/{plan_id}` | Fetch structured findings report |
| `POST` | `/chat/{plan_id}` | Phase C — ask geometry questions |
| `GET` | `/health` | Health check |

---

## Evaluation

The `evals/` folder contains a hand-labeled ground truth set. Run metrics with:

```bash
python -m app.evals.eval_runner
```

This reports per-rule precision and overall hallucination rate (findings with no grounding in the extracted geometry). The consistency filter target is < 1 ungrounded finding per 10 plans.

---

## Phases

- **Phase A** ✅ — Gemini extraction spike + schema contract
- **Phase B** ✅ — Rule engine + consistency filter + report pipeline + evals
- **Phase C** 🔄 — "Chat with your floor plan" agent using geometry tools

---

## Why Not Just Use ChatGPT?

ChatGPT can comment on a floor plan. Planalyze produces *verifiable* analysis:

- Every finding cites the specific room and rule that triggered it
- Schema-validated extraction with retry on violations
- Self-consistency filtering to suppress hallucinations
- Measurable precision from a hand-labeled eval set
- Visual overlays that tie findings to the actual plan

> *"ChatGPT is the model. This is the system built around the model."*

---

## License

MIT