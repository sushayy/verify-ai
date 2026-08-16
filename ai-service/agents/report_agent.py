"""Agent 4: Report Generation — assembles the final VerificationReport.

Presentation only. This agent makes no API call and reaches no new judgment,
so it cannot contradict the verdict Agent 3 reached, and it costs no quota.
Its job is to clean up the evidence list and emit the validated contract shape
that the Node backend and the Postgres schema both expect.
"""

from agents.fact_check_agent import Verdict
from models import Evidence, StructuredClaim, VerificationReport

# Caps how much evidence reaches the database: report.model.js inserts one row
# per item, and past the strongest handful the extras add little.
_MAX_EVIDENCE = 6


def _dedupe(evidence: list[Evidence]) -> list[Evidence]:
    """Removes evidence repeating the same text from the same source.

    The corpus and the web search often surface the same passage, so this
    keeps the first (highest-reliability) copy and drops the rest.

    Args:
        evidence: Evidence sorted by descending reliability.

    Returns:
        The list with duplicates removed, order preserved.
    """
    seen = set()
    unique = []
    for item in evidence:
        key = (item.source_name, item.extracted_text.strip())
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def generate_report(
    claim: StructuredClaim,
    evidence: list[Evidence],
    result: Verdict,
) -> VerificationReport:
    """Builds the final report returned to the backend.

    Args:
        claim: The structured claim produced by Agent 1.
        evidence: Evidence gathered by Agent 2.
        result: The verdict reached by Agent 3.

    Returns:
        A validated VerificationReport carrying the verdict and the
        strongest supporting evidence.
    """
    top_evidence = _dedupe(
        sorted(evidence, key=lambda e: e.reliability_score, reverse=True)
    )[:_MAX_EVIDENCE]

    return VerificationReport(
        claim=claim,
        final_result=result.final_result,
        confidence_score=result.confidence_score,
        explanation=" ".join(result.explanation.split()),
        evidence=top_evidence,
    )
