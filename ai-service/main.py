"""FastAPI entry point for the Verify AI agent service.

Exposes the `/verify` endpoint the Node backend calls, which runs the full
four-agent pipeline for a single claim.
"""

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agents.claim_analysis_agent import analyze_claim
from agents.evidence_retrieval_agent import retrieve_evidence
from agents.fact_check_agent import fact_check
from agents.report_agent import generate_report
from models import VerificationReport
from services import vector_store

load_dotenv()

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Embeds the reference corpus into ChromaDB once, at startup.

    The ingest is idempotent, so restarts reuse the existing embeddings
    rather than recomputing them. A failure here is logged but not fatal —
    the pipeline can still run on web evidence alone.
    """
    try:
        count = vector_store.ingest_corpus()
        logger.info("Reference corpus ready: %d chunks indexed.", count)
    except Exception:
        logger.exception("Corpus ingest failed; continuing without local evidence.")
    yield


app = FastAPI(title="Verify AI - AI Service", lifespan=lifespan)


class ClaimInput(BaseModel):
    claim_text: str


@app.get("/health")
def health():
    return {"status": "ok", "message": "AI service is running"}


@app.post("/test-agent1")
def test_agent1(payload: ClaimInput):
    result = analyze_claim(payload.claim_text)
    return result.model_dump()


@app.post("/verify")
def verify_claim(payload: ClaimInput) -> VerificationReport:
    """Runs the full agent pipeline for one claim.

    Args:
        payload: The claim to verify.

    Returns:
        A VerificationReport. A claim with no retrievable evidence comes back
        as a normal UNVERIFIED report, not an error.

    Raises:
        HTTPException: 400 if the claim is empty, or 502 if the upstream
            model is unreachable or misconfigured — which is the backend's
            cue to mark the claim `failed`.
    """
    claim_text = payload.claim_text.strip()
    if not claim_text:
        raise HTTPException(status_code=400, detail="claim_text must not be empty.")

    try:
        structured = analyze_claim(claim_text)              # Agent 1
        evidence = retrieve_evidence(structured)            # Agent 2
        result = fact_check(structured, evidence)           # Agent 3
        return generate_report(structured, evidence, result)  # Agent 4
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Verification pipeline failed for claim: %s", claim_text[:120])
        raise HTTPException(
            status_code=502, detail=f"Verification pipeline failed: {exc}"
        ) from exc
