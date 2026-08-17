"""Agent 1: Claim Analysis — structures a raw claim for downstream agents."""

from models import StructuredClaim
from services.gemini_client import generate_parsed

_PROMPT_TEMPLATE = """You are a claim analysis engine. Read the CLAIM below and \
extract structured information from it.

Return ONLY a JSON object, no other text, with these fields:
- "normalized_statement": the claim rewritten as one clear, standalone factual statement
- "entities": array of named entities mentioned (people, organizations, places)
- "dates": array of any dates or time references mentioned (empty array if none)
- "claim_type": one short category label, e.g. "statistical", "event", "quote_attribution", "general_fact"

CLAIM:
{claim_text}"""


def analyze_claim(claim_text: str) -> StructuredClaim:
    """Structures a raw claim into entities, dates, type, and a normalized form."""
    prompt = _PROMPT_TEMPLATE.format(claim_text=claim_text)
    parsed = generate_parsed(prompt)

    return StructuredClaim(
        original_text=claim_text,
        normalized_statement=parsed["normalized_statement"],
        entities=parsed.get("entities", []),
        dates=parsed.get("dates", []),
        claim_type=parsed.get("claim_type", "general_fact"),
    )
