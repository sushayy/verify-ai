"""Agent 1: Claim Analysis — structures a raw claim for downstream agents."""

from models import StructuredClaim
from services.gemini_client import generate_parsed

_PROMPT_TEMPLATE = """You are a claim analysis engine.

Read the CLAIM below and extract structured information from it.

IMPORTANT:
- Return ONLY one complete, valid JSON object.
- Do NOT use markdown or code fences.
- Do NOT add explanations before or after the JSON.
- Make sure the JSON is fully closed with all required brackets and braces.
- Use double quotes for all JSON keys and string values.
- The response MUST be valid JSON that can be parsed directly.

The JSON object MUST contain exactly these fields:
{{
  "normalized_statement": "one clear standalone factual statement",
  "entities": [],
  "dates": [],
  "claim_type": "general_fact"
}}

Field requirements:
- "normalized_statement": the claim rewritten as one clear, standalone factual statement
- "entities": array of named entities mentioned, such as people, organizations, places, countries, landmarks, or institutions
- "dates": array of any dates or time references mentioned; use [] if none
- "claim_type": one short category label such as "statistical", "event", "quote_attribution", or "general_fact"

CLAIM:
{claim_text}"""


def analyze_claim(claim_text: str) -> StructuredClaim:
    """Structures a raw claim into entities, dates, type, and a normalized form."""
    prompt = _PROMPT_TEMPLATE.format(claim_text=claim_text)
    parsed = generate_parsed(prompt)

    if not isinstance(parsed, dict):
        raise ValueError("Claim analysis agent returned an invalid JSON structure.")

    if "normalized_statement" not in parsed:
        raise ValueError("Claim analysis response is missing normalized_statement.")

    return StructuredClaim(
        original_text=claim_text,
        normalized_statement=parsed["normalized_statement"],
        entities=parsed.get("entities", []),
        dates=parsed.get("dates", []),
        claim_type=parsed.get("claim_type", "general_fact"),
    )