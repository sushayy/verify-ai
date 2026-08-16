"""Agent 3: Fact-Checking & Reasoning — the verification judgment itself.

Weighs the claim against the evidence Agent 2 gathered, giving more weight to
high-reliability sources, and produces the verdict, confidence, and rationale
that Agent 4 formats into the final report.
"""

from typing import NamedTuple

from models import Classification, Evidence, StructuredClaim
from services.gemini_client import generate_parsed

_NO_EVIDENCE_CONFIDENCE = 0.2
_NO_EVIDENCE_EXPLANATION = (
    "No relevant evidence could be retrieved for this claim, so it cannot be "
    "verified either way."
)

_VALID_RESULTS = {"TRUE", "FALSE", "MISLEADING", "UNVERIFIED"}

_VERIFICATION_PROMPT = """You are a fact-verification engine. Given a CLAIM and a \
set of numbered EVIDENCE passages, decide whether the evidence shows the claim \
to be true, false, misleading, or unverifiable.

Each passage is annotated with a reliability score from 0 to 1 and the stance \
it was tagged with. Weigh high-reliability passages more heavily than \
low-reliability ones. Where a high-reliability source and a low-reliability \
source conflict, follow the high-reliability source and say so.

Return ONLY a JSON object, no other text, with these fields:
- "final_result": one of "TRUE", "FALSE", "MISLEADING", "UNVERIFIED"
- "confidence_score": a number from 0 to 1
- "explanation": two or three sentences justifying the verdict, grounded only \
in the given evidence, naming the sources you relied on

Guidance on choosing the verdict:
- "TRUE": the reliable evidence supports the claim as stated
- "FALSE": the reliable evidence contradicts the claim
- "MISLEADING": the claim is technically accurate but omits context, \
overstates a real finding, or states a disputed matter as settled
- "UNVERIFIED": the evidence is absent, off-topic, or too weak to decide

Be conservative with confidence: use a value above 0.8 only when several \
reliable sources agree. Do not use outside knowledge beyond the evidence \
provided.

CLAIM:
{claim}

EVIDENCE:
{evidence}"""


class Verdict(NamedTuple):
    """The judgment Agent 3 reaches for a claim."""

    final_result: Classification
    confidence_score: float
    explanation: str


def _format_evidence(evidence: list[Evidence]) -> str:
    """Renders evidence as a numbered block annotated with stance and score."""
    return "\n\n".join(
        f"[{i}] source: {e.source_name} | reliability: {e.reliability_score:.2f} "
        f"| tagged stance: {e.stance}\n{e.extracted_text}"
        for i, e in enumerate(evidence)
    )


def _clamp(value: float) -> float:
    """Constrains a confidence score to the [0, 1] range the models require."""
    return max(0.0, min(1.0, value))


def fact_check(
    claim: StructuredClaim,
    evidence: list[Evidence],
    client=None,
) -> Verdict:
    """Judges a claim against its evidence.

    Args:
        claim: The structured claim produced by Agent 1.
        evidence: Evidence gathered by Agent 2. May be empty.
        client: An existing Gemini client to reuse. A new one is created
            from GEMINI_API_KEY if omitted — pass one explicitly in tests.

    Returns:
        A Verdict with the classification, a confidence in [0, 1], and an
        explanation grounded in the supplied evidence.

    Raises:
        ValueError: If the model response is not valid JSON, or names a
            classification outside the allowed set.
    """
    # Short-circuits without an API call: there is nothing to reason over.
    if not evidence:
        return Verdict("UNVERIFIED", _NO_EVIDENCE_CONFIDENCE, _NO_EVIDENCE_EXPLANATION)

    prompt = _VERIFICATION_PROMPT.format(
        claim=claim.normalized_statement,
        evidence=_format_evidence(evidence),
    )
    parsed = generate_parsed(prompt, client=client)

    final_result = str(parsed.get("final_result", "")).upper()
    if final_result not in _VALID_RESULTS:
        raise ValueError(f"Model returned an unknown final_result: {final_result!r}")

    try:
        confidence = _clamp(float(parsed.get("confidence_score", 0.0)))
    except (TypeError, ValueError):
        confidence = 0.0

    explanation = str(parsed.get("explanation") or "").strip() or _NO_EVIDENCE_EXPLANATION
    return Verdict(final_result, confidence, explanation)
