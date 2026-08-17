"""Agent 2: Evidence Retrieval — gathers, scores, and stance-tags evidence.

Draws on two sources: semantic search over the curated ChromaDB corpus, and a
live Google Search grounded Gemini call. Every candidate passage is scored for
source credibility and tagged with its stance toward the claim before being
handed to Agent 3.
"""

import logging
import os

from models import Evidence, StructuredClaim
from services import vector_store
from services.credibility import score_source
from services.gemini_client import generate_grounded, generate_parsed

logger = logging.getLogger(__name__)

_LOCAL_K = 4
_MAX_WEB_SOURCES = 4
_SNIPPET_CHARS = 700


def _web_search_enabled() -> bool:
    """Reports whether the live web search step should run.

    Google Search grounding is a billing-gated Gemini feature: on a free-tier
    key every grounded call returns 429. Set ENABLE_WEB_SEARCH=false to skip
    the attempt entirely and save the latency.
    """
    return os.environ.get("ENABLE_WEB_SEARCH", "true").strip().lower() not in {
        "false",
        "0",
        "no",
    }

_SEARCH_PROMPT = """Search for current, authoritative information about whether \
the following statement is accurate. Summarize what reliable sources actually \
say, and include any sources that contradict the statement.

STATEMENT: {statement}"""

_STANCE_PROMPT = """You are an evidence classification engine. For each numbered \
PASSAGE below, decide its stance toward the CLAIM.

Return ONLY a JSON object, no other text, in this exact shape:
{{"stances": [{{"index": 0, "stance": "supporting"}}]}}

Each "stance" must be exactly one of:
- "supporting": the passage is evidence that the claim is accurate
- "contradicting": the passage is evidence that the claim is inaccurate
- "neutral": the passage concerns the topic but does not settle the claim

Include exactly one entry for every passage index shown.

CLAIM:
{claim}

PASSAGES:
{passages}"""

_VALID_STANCES = {"supporting", "contradicting", "neutral"}


def _search_query(claim: StructuredClaim) -> str:
    """Builds the web search prompt for a claim, enriched with its entities."""
    statement = claim.normalized_statement
    if claim.entities:
        statement = f"{statement} (key entities: {', '.join(claim.entities)})"
    return _SEARCH_PROMPT.format(statement=statement)


def _retrieve_local(claim: StructuredClaim) -> list[dict]:
    """Retrieves candidate passages from the curated ChromaDB corpus.

    Args:
        claim: The structured claim to search for.

    Returns:
        Candidate dicts with source_name, url, extracted_text, and
        reliability_score. Empty if the corpus has not been ingested.
    """
    candidates = []
    for hit in vector_store.query(claim.normalized_statement, k=_LOCAL_K):
        metadata = hit.get("metadata") or {}
        candidates.append(
            {
                "source_name": metadata.get("title") or metadata.get("filename", "Reference corpus"),
                "url": metadata.get("url") or None,
                "extracted_text": hit["document"],
                # Corpus documents are hand-vetted, so their curated score is
                # used directly rather than being inferred from a domain.
                "reliability_score": float(metadata.get("reliability", 0.7)),
            }
        )
    return candidates


def _web_chunk_texts(metadata, chunk_count: int, fallback: str) -> list[str]:
    """Maps each grounding chunk to the answer text it supports.

    Args:
        metadata: The response's grounding_metadata.
        chunk_count: How many grounding chunks the response carried.
        fallback: Text to use for chunks with no attributed segment.

    Returns:
        One text snippet per grounding chunk, positionally aligned.
    """
    texts: list[list[str]] = [[] for _ in range(chunk_count)]
    for support in getattr(metadata, "grounding_supports", None) or []:
        segment = getattr(support, "segment", None)
        sentence = (getattr(segment, "text", None) or "").strip()
        if not sentence:
            continue
        for index in getattr(support, "grounding_chunk_indices", None) or []:
            if 0 <= index < chunk_count:
                texts[index].append(sentence)
    return [" ".join(parts)[:_SNIPPET_CHARS] if parts else fallback for parts in texts]


def _retrieve_web(claim: StructuredClaim, client=None) -> list[dict]:
    """Retrieves candidate passages via a Google Search grounded Gemini call.

    Args:
        claim: The structured claim to search for.
        client: An existing Gemini client to reuse. A new one is created
            from GEMINI_API_KEY if omitted — pass one explicitly in tests.

    Returns:
        Candidate dicts, one per grounded web source. Empty if the model
        answered without searching, which is a normal outcome rather than
        an error.
    """
    response = generate_grounded(_search_query(claim), client=client)
    candidates = getattr(response, "candidates", None) or []
    if not candidates:
        return []

    metadata = getattr(candidates[0], "grounding_metadata", None)
    chunks = getattr(metadata, "grounding_chunks", None) or []
    if not chunks:
        return []

    fallback = (getattr(response, "text", None) or "").strip()[:_SNIPPET_CHARS]
    texts = _web_chunk_texts(metadata, len(chunks), fallback)

    results = []
    for chunk, text in zip(chunks, texts):
        web = getattr(chunk, "web", None)
        if web is None or not text:
            continue
        # `uri` is normally a redirect wrapper, so prefer the real domain and
        # title when the SDK provides them for credibility scoring.
        domain = getattr(web, "domain", None) or ""
        title = getattr(web, "title", None) or domain or "Web source"
        results.append(
            {
                "source_name": title,
                "url": getattr(web, "uri", None),
                "extracted_text": text,
                "reliability_score": score_source(url=domain, publisher=title),
            }
        )
        if len(results) >= _MAX_WEB_SOURCES:
            break
    return results


def _tag_stances(claim: StructuredClaim, candidates: list[dict], client=None) -> list[str]:
    """Classifies every candidate's stance toward the claim in one call.

    Batches all passages into a single Gemini request rather than one call
    per passage, which keeps the endpoint inside free-tier rate limits.

    Args:
        claim: The claim the passages are being judged against.
        candidates: The candidate passages to classify.
        client: An existing Gemini client to reuse.

    Returns:
        One stance string per candidate, positionally aligned. Anything the
        model omits or garbles defaults to "neutral".
    """
    passages = "\n\n".join(
        f"[{i}] {c['extracted_text']}" for i, c in enumerate(candidates)
    )
    prompt = _STANCE_PROMPT.format(claim=claim.normalized_statement, passages=passages)

    stances = ["neutral"] * len(candidates)
    try:
        parsed = generate_parsed(prompt, client=client)
    except ValueError:
        # A malformed stance response degrades the evidence rather than
        # failing the request — Agent 3 can still reason over neutral tags.
        return stances

    for item in parsed.get("stances", []):
        if not isinstance(item, dict):
            continue
        index = item.get("index")
        stance = item.get("stance")
        if isinstance(index, int) and 0 <= index < len(stances) and stance in _VALID_STANCES:
            stances[index] = stance
    return stances


def retrieve_evidence(claim: StructuredClaim, client=None) -> list[Evidence]:
    """Gathers evidence for a claim from the local corpus and the live web.

    Args:
        claim: The structured claim produced by Agent 1.
        client: An existing Gemini client to reuse. A new one is created
            from GEMINI_API_KEY if omitted — pass one explicitly in tests.

    Returns:
        Evidence passages sorted by descending reliability, each tagged
        supporting, contradicting, or neutral. Empty if nothing relevant was
        found, which Agent 3 treats as UNVERIFIED.
    """
    candidates = _retrieve_local(claim)
    if _web_search_enabled():
        try:
            candidates += _retrieve_web(claim, client=client)
        except Exception as exc:
            # Web search is an enrichment, not a hard dependency: a quota or
            # network failure degrades to corpus-only evidence rather than
            # failing the whole verification.
            logger.warning("Web search unavailable, using corpus evidence only: %s", exc)

    if not candidates:
        return []

    stances = _tag_stances(claim, candidates, client=client)
    evidence = [
        Evidence(
            source_name=candidate["source_name"],
            url=candidate["url"],
            extracted_text=candidate["extracted_text"],
            stance=stance,
            reliability_score=candidate["reliability_score"],
        )
        for candidate, stance in zip(candidates, stances)
    ]
    evidence.sort(key=lambda e: e.reliability_score, reverse=True)
    return evidence
