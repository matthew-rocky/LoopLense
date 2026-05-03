# LoopLens

LoopLens is a Next.js + FastAPI review workspace for circular charity funding patterns. It helps reviewers inspect loaded records, rank review-priority loops, visualize transfer networks, ask evidence-grounded questions, and generate neutral memos with claim verification.

LoopLens is a triage and evidence-navigation tool. It does not allege wrongdoing, infer intent, or make legal findings.

## Primary Architecture

```text
frontend/ Next.js App Router UI
    -> backend/ FastAPI endpoints
        -> src/ reusable Python data, query, scoring, memo, verification, chat, and graph logic
            -> data/processed/ local Parquet and CSV files
```

The main product is no longer Streamlit. The old Streamlit prototype is preserved under `legacy/` only.

## Run The Web App

Prerequisites:

- Python with the project dependencies installed
- Node.js LTS
- npm
- The FastAPI backend must stay running while the frontend is open

### Backend

From the repository root:

```powershell
cd D:\AI-Hackathon\Main
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```

Backend URLs:

```text
http://localhost:8000/api/health
http://127.0.0.1:8000/docs
```

### Frontend

In a second terminal:

```powershell
cd D:\AI-Hackathon\Main\frontend
npm install
npm run dev
```

Frontend URL:

```text
http://localhost:3000
```

If needed, create `frontend/.env.local`:

```text
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000/api
```

### Windows Helper

`RUN.bat` starts the FastAPI backend and prints the frontend commands to run in a second terminal.

## API Endpoints

```text
GET  /api/health
GET  /api/summary
GET  /api/loops
GET  /api/loops/{loop_id}
GET  /api/loops/{loop_id}/network
POST /api/chat
POST /api/memo
POST /api/verify
```

## Project Structure

```text
backend/
  main.py
  schemas.py
  api/
    health.py
    loops.py
    chat.py
    memo.py
    verify.py
  services/
    loop_service.py
    graph_service.py
    chat_service.py
    memo_service.py
    verify_service.py

frontend/
  app/
    page.tsx
    dashboard/page.tsx
    loops/page.tsx
    loops/[id]/page.tsx
    network/page.tsx
    chat/page.tsx
    memo/page.tsx
  components/
  lib/
  package.json

src/
  data.py
  load.py
  query.py
  score.py
  memo.py
  verify.py
  chat.py
  graph.py
  text.py

legacy/
  app.py
  chat.py
  charts.py
  graph.py
  ui.py

data/processed/
  loops_ranked.parquet
  loop_edges.parquet
  people.parquet
  charity_profiles.parquet
```

## Backend Logic

The FastAPI backend reuses the pure modules in `src/`:

- `src/load.py` loads processed loop, edge, people, and profile data.
- `src/query.py` provides safe DuckDB query helpers.
- `src/score.py` computes deterministic review-priority labels and explanations.
- `src/graph.py` provides transfer edge normalization.
- `src/chat.py` contains evidence-grounded chat handlers without UI dependencies.
- `src/memo.py` generates neutral evidence-based memos.
- `src/verify.py` verifies chat and memo claims against attached evidence.

Backend request handling does not import Streamlit UI code.

## Frontend Pages

- Landing page: product entry point and responsible-use framing.
- Dashboard: animated metrics, review label distribution, top flow chart, score histogram, participant distribution, year-range chart, and high-priority loop cards.
- Loop Explorer: full-screen searchable/filterable/sortable loop table with sticky headers and participant-name previews.
- Loop Detail: selected loop summary, participants, edges, and score explanation.
- Network View: full-height interactive React Flow graph from `/api/loops/{loop_id}/network`.
- Chat: evidence-grounded chat using `/api/chat`, with evidence cards, tables, charts, memo rendering, and verification cards.
- Memo: memo generation and verification using `/api/memo` and `/api/verify`, with copy and markdown download.

## Data

The app expects processed files under:

```text
data/processed/
```

If processed data is missing, rebuild it with:

```bash
python scripts/build_data.py
```

## Validation

Run backend checks from the repository root:

```bash
python -m compileall backend src
pytest tests/test_backend_smoke.py
```

The smoke tests verify:

- `/api/health`
- `/api/summary`
- `/api/loops`
- `/api/loops/{loop_id}/network`

## Legacy Streamlit Prototype

The old Streamlit prototype is preserved in `legacy/` for reference only. It is not the main application path and Streamlit is not included in `requirements.txt`.

If you intentionally need the legacy prototype, install:

```bash
pip install -r requirements-legacy-streamlit.txt
```

## Responsible Use

Use LoopLens for review priority, evidence exploration, and human review workflows. Use wording such as:

- review priority
- pattern requiring human review
- circular funding pattern
- evidence-based summary
- available records suggest
- not a finding of wrongdoing

Avoid using the app to claim fraud, criminality, guilt, corruption, money laundering, fake charities, or proof of wrongdoing.
