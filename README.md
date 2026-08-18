# Verify AI

**A Multi-Agent Misinformation Verification Platform via Retrieval-Grounded Architectures**

Verify AI lets a user submit a claim — as typed text, a URL, or a PDF — and returns an AI-generated verification report: a verdict (TRUE / FALSE / MISLEADING / UNVERIFIED), a confidence score, a plain-language explanation, and the evidence behind it, each source tagged as supporting, contradicting, or neutral and scored for reliability.

**Live app:** [verify-ai-gules.vercel.app](https://verify-ai-gules.vercel.app)

---

## Architecture

The frontend (React, hosted on Vercel) only ever talks to the Node/Express backend (Render) — it never calls the AI service directly. The backend handles auth and data, and hands off each claim to the Python AI service (also on Render), which runs the four-agent pipeline using Gemini and a ChromaDB vector store. Everything persists to PostgreSQL on Supabase. This keeps auth, data ownership, and the AI pipeline cleanly separated. Full detail on the AI service specifically is in [`ai-service/README.md`](./ai-service/README.md).

---

## Tech stack

- **Frontend:** React (Vite), Tailwind CSS, react-router, axios — deployed on Vercel
- **Backend:** Node.js, Express, PostgreSQL (`pg`), JWT auth, `express-rate-limit` — deployed on Render
- **AI Service:** Python, FastAPI, Google Gemini API, ChromaDB — deployed on Render
- **Database:** PostgreSQL, hosted on Supabase

---

## Repository structure

```
verify-ai/
|- frontend/       # React app
|- backend/        # Express API + orchestrator
|- ai-service/     # FastAPI multi-agent pipeline (see its own README)
|- database/       # schema.sql — table definitions and constraints
|- docs/
```

---

## Running locally

Each service needs its own `.env` — none are committed (see `.gitignore`). You'll need your own free Supabase project and a free Gemini API key.

### 1. Database
Create a Supabase project, then run `database/schema.sql` in its SQL Editor.

### 2. Backend
```bash
cd backend
npm install
```
Create `backend/.env`:
```
DATABASE_URL=your_supabase_connection_string
JWT_SECRET=any_random_string
PORT=5000
AI_SERVICE_URL=http://localhost:8000
USE_MOCK_AI=false
```
```bash
npm run dev
```

### 3. AI service
```bash
cd ai-service
python -m venv .venv
source .venv/Scripts/activate   # Mac/Linux: source .venv/bin/activate
pip install -r requirements.txt
```
Create `ai-service/.env`:
```
GEMINI_API_KEY=your_gemini_key
```
```bash
uvicorn main:app --reload --port 8000
```
Full detail (agents, corpus, credibility scoring, free-tier limits) in [`ai-service/README.md`](./ai-service/README.md).

### 4. Frontend
```bash
cd frontend
npm install
npm run dev
```
By default the frontend points at the deployed backend (`https://verify-ai-backend.onrender.com`) — edit `frontend/src/api/client.js` to point at `http://localhost:5000` instead if running the backend locally too.

---

## Key design decisions

- **Multi-agent, not a single prompt.** Each agent has one responsibility and a typed hand-off to the next (`StructuredClaim` → `Evidence[]` → verdict → `VerificationReport`), matching the project's multi-agent brief rather than a single large prompt doing everything.
- **RAG + live grounded search, hybrid.** A curated 17-document corpus (ChromaDB, semantic search) covers common claims cheaply and fast; Gemini's grounded web search extends coverage to claims outside that corpus.
- **Database-enforced data integrity.** `CHECK` constraints on `claims`, `evidence`, and `reports` (not just application-level validation) reject invalid data at the database layer.
- **Access control at the query level.** Claims are fetched filtered by both `claim_id` and `user_id`, so one user can never retrieve another's claim by guessing an ID — verified in QA testing (see `backend/TESTING.md`).
- **Async verification.** Submitting a claim returns immediately (`pending`); the AI pipeline runs in the background and the frontend polls a lightweight status endpoint rather than blocking the request.

## Known limitations

- **Verification latency.** Each claim runs a sequential four-agent pipeline plus live grounded search — typically slower than a single-shot response, prioritizing evidence quality over speed. Free-tier hosting also introduces cold-start delays after inactivity.
- **Semantic precision over surface similarity.** The system distinguishes technically-different claims that sound equivalent in casual language (e.g. "highest" vs. "tallest" mountain) — this is intentional and correct behavior, not an error, though it can surprise a reader expecting a looser match.
- **Confidence is rarely 100%,** even for well-established facts — reflecting genuine evidence-based reasoning rather than an axiomatic "yes/no," consistent with how real fact-checking organizations rate claims.

---

## Team

 Role 

| Sushank | Backend, architecture, orchestrator, database, PDF/URL upload, deployment |
| Habeeb | AI/RAG — multi-agent pipeline, evidence retrieval, Gemini integration |
| Jasnoor | Frontend — React UI, all pages, API integration |
| Sudip | Database constraints, QA testing (see `backend/TESTING.md`) |

University final-year project: *Verify AI: A Multi-Agent Misinformation Verification Platform via Retrieval-Grounded Architectures*.