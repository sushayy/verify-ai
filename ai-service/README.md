# Verify AI — AI Service

FastAPI service running the four-agent claim verification pipeline. The Node
backend calls `POST /verify` with a claim and gets a structured
`VerificationReport` back; it never talks to Gemini directly.

```
Frontend → Node/Express backend → THIS SERVICE → Gemini + ChromaDB
```

## Pipeline

| Agent | File | Does | Gemini calls |
|---|---|---|---|
| 1. Claim analysis | `agents/claim_analysis_agent.py` | Raw text → `StructuredClaim` (entities, dates, type) | 1 |
| 2. Evidence retrieval | `agents/evidence_retrieval_agent.py` | ChromaDB search + web search, credibility scoring, stance tagging | 1–2 |
| 3. Fact checking | `agents/fact_check_agent.py` | Weighs evidence by reliability → verdict, confidence, rationale | 1 (0 if no evidence) |
| 4. Report generation | `agents/report_agent.py` | Dedupes/ranks evidence, assembles the final report | 0 |

A verification costs **3 Gemini calls** in the normal case, and **1** when no
evidence is found (Agent 3 short-circuits to `UNVERIFIED` without calling out).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: source .venv/Scripts/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add a free key from
[aistudio.google.com](https://aistudio.google.com):

```env
GEMINI_API_KEY=your_key_here
```

## Run

```bash
uvicorn main:app --reload --port 8000
```

The reference corpus is embedded into `chroma_db/` on startup. That is
idempotent, so restarts reuse the existing embeddings. The first run downloads
the ~80 MB embedding model to `~/.cache/chroma`.

```bash
curl -X POST http://localhost:8000/verify -H "Content-Type: application/json" \
  -d '{"claim_text":"The Great Wall of China is visible from space with the naked eye."}'
```

Other endpoints: `GET /health`, `POST /test-agent1` (Agent 1 in isolation).

## Test

Offline, mocked, no API key and no quota used:

```bash
pytest tests/ -v
```

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | — | Required. |
| `GEMINI_MODEL` | `gemini-3.5-flash` | Override the chat model. |
| `ENABLE_WEB_SEARCH` | `true` | Set `false` to skip the web search step. |

### Free-tier limits worth knowing

Both of these were hit during development, and the service is built to survive
them rather than pretend they don't exist:

- **20 requests per day, per model.** At 3 calls per verification that is about
  6 claims a day on one model. Each model has its own separate allowance, so
  `GEMINI_MODEL=gemini-3.6-flash` (or `gemini-3.5-flash-lite`,
  `gemini-3-flash-preview`) buys another 20 when one runs dry. Requests are
  retried with backoff on per-minute limits and on transient overload, but a
  per-day exhaustion fails fast rather than stalling the request.
- **Google Search grounding is billing-gated.** Every grounded call on a
  free-tier key returns 429 regardless of model. Agent 2 catches this and
  degrades to corpus-only evidence, so `/verify` keeps working — verdicts just
  rest on the local corpus alone. Set `ENABLE_WEB_SEARCH=false` to skip the
  doomed attempt and save ~30s per request until billing is enabled. The
  grounding code path is complete and starts working the moment it is.

## Reference corpus

`corpus/` holds 17 short vetted reference documents with a `sources.json`
sidecar giving each one a title, source URL, publisher, and curated
reliability score. The documents are summaries written for this project, and
each `url` points at a stable reference article on the same topic rather than
being a verbatim extract of it.

Add a document by dropping a `.txt` in `corpus/`, adding its entry to
`sources.json`, and re-running:

```bash
python scripts/ingest_corpus.py
```

Ingest prunes chunks for documents that no longer exist, so editing and
deleting both work.

Retrieval drops hits beyond `MAX_DISTANCE` (0.6, recalibrated for Gemini embeddings) in `services/vector_store.py`.
Without that cutoff the search always returns its full `k`, padding evidence
with unrelated documents; with it, a claim the corpus knows nothing about
correctly returns no evidence and comes back `UNVERIFIED`.

## Source credibility

`services/credibility.py` scores web sources by domain, no API calls:

| Tier | Score | Examples |
|---|---|---|
| Government / academic | 0.95 | `.gov`, `.edu`, `.int`, `.mil` |
| Major outlet or journal | 0.85 | Reuters, AP, BBC, Nature, The Lancet |
| Reference work | 0.7 | Wikipedia, Britannica, Snopes |
| Unknown domain | 0.4 | anything unrecognized |
| User-generated | 0.25 | Medium, Substack, Reddit, X |

Corpus documents use the curated `reliability` from `sources.json` instead.
Agent 3 is told these scores and instructed to favour reliable sources when
they conflict.

## The data contract

`models.py` is shared with Sudip's Postgres schema and Sushank's orchestrator —
**do not rename fields without flagging it to the group.** Every key in
`evidence[]` maps to a column in the `evidence` table and every report field to
one in `reports`.

`/verify` returns:
- **200** with a `VerificationReport`. A claim with no retrievable evidence is
  a normal `UNVERIFIED` report, not an error.
- **400** if `claim_text` is empty.
- **502** if the model is unreachable, misconfigured, or out of daily quota —
  the backend's `runVerification` catch marks the claim `failed`.
