"""Shared data models for the Verify AI agent pipeline."""

from typing import Literal, Optional

from pydantic import BaseModel, Field

Classification = Literal["TRUE", "FALSE", "MISLEADING", "UNVERIFIED"]


class StructuredClaim(BaseModel):
    """A claim after Agent 1 has analyzed and structured it."""

    original_text: str
    normalized_statement: str
    entities: list[str] = Field(default_factory=list)
    dates: list[str] = Field(default_factory=list)
    claim_type: str


class Evidence(BaseModel):
    """A retrieved passage relevant to a claim."""

    source_name: str
    url: Optional[str] = None
    extracted_text: str
    stance: Literal["supporting", "contradicting", "neutral"]
    reliability_score: float = Field(ge=0.0, le=1.0)


class VerificationReport(BaseModel):
    """The final output of the full agent pipeline for one claim."""

    claim: StructuredClaim
    final_result: Classification
    confidence_score: float = Field(ge=0.0, le=1.0)
    explanation: str
    evidence: list[Evidence]
