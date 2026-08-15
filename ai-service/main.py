from fastapi import FastAPI
from dotenv import load_dotenv
from pydantic import BaseModel

from agents.claim_analysis_agent import analyze_claim

load_dotenv()

app = FastAPI(title="Verify AI - AI Service")


class ClaimInput(BaseModel):
    claim_text: str


@app.get("/health")
def health():
    return {"status": "ok", "message": "AI service is running"}


@app.post("/test-agent1")
def test_agent1(payload: ClaimInput):
    result = analyze_claim(payload.claim_text)
    return result.model_dump()
