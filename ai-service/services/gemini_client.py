"""Shared Gemini client wrapper used by all agents."""

import json
import os
import re

from google import genai
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

_decoder = json.JSONDecoder()

# Confirmed available on the free tier via client.models.list().
# Overridable so the team can switch models without a code change.
_DEFAULT_MODEL = "gemini-3.5-flash"

# Free-tier capacity is shared, so overload responses are common and usually
# clear within seconds. Quota exhaustion (429 RESOURCE_EXHAUSTED) is
# deliberately excluded — that is a billing gate and retrying only adds delay.
_TRANSIENT_MARKERS = ("503", "UNAVAILABLE", "INTERNAL", "DEADLINE_EXCEEDED")


def _is_transient(exc: BaseException) -> bool:
    """Reports whether an API error is worth retrying."""
    message = str(exc)
    return any(marker in message for marker in _TRANSIENT_MARKERS)


def _is_rate_limited(exc: BaseException) -> bool:
    """Reports whether an error is a windowed rate limit that will clear.

    A short per-minute cap is worth waiting out. Two other quota errors are
    not, and both are excluded: the per-day free-tier cap (which reports a
    misleading short retry delay but will not clear until tomorrow), and a
    hard billing gate with no retry hint at all — notably Google Search
    grounding.
    """
    message = str(exc)
    if "RESOURCE_EXHAUSTED" not in message or "retry in" not in message.lower():
        return False
    return "PerDay" not in message


# For grounded search: overload clears quickly, but a quota block never will.
_retry_transient = retry(
    retry=retry_if_exception(_is_transient),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=15),
    reraise=True,
)

# For ordinary generation: also waits out the free tier's per-window request
# cap, since a single /verify makes three calls and can trip it.
_retry_generation = retry(
    retry=retry_if_exception(lambda e: _is_transient(e) or _is_rate_limited(e)),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=4, min=5, max=60),
    reraise=True,
)


def get_model() -> str:
    """Returns the chat model every agent should call."""
    return os.environ.get("GEMINI_MODEL") or _DEFAULT_MODEL


def get_client() -> genai.Client:
    """Builds a Gemini API client from the GEMINI_API_KEY environment variable."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")
    return genai.Client()


@_retry_generation
def generate_json(prompt: str, client: "genai.Client | None" = None) -> str:
    """Sends a prompt to Gemini and returns the raw text response.

    Retries with backoff on transient overload and on the free tier's
    per-window request cap.
    """
    client = client or get_client()
    response = client.models.generate_content(
        model=get_model(),
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )
    return response.text


def parse_json(raw: "str | None") -> "dict | list":
    """Parses the first JSON value out of a model response.

    Even in JSON mode, Gemini occasionally wraps its output in a markdown
    fence or appends a stray closing brace. Decoding the first complete value
    and ignoring whatever follows makes every agent tolerant of that instead
    of failing the whole request.

    Args:
        raw: The model's raw text response.

    Returns:
        The decoded JSON object or array.

    Raises:
        ValueError: If no valid JSON value could be found.
    """
    if not raw or not raw.strip():
        raise ValueError("Model returned an empty response.")

    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
        text = re.sub(r"```\s*$", "", text).strip()

    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        raise ValueError(f"Model did not return valid JSON: {raw!r}")

    try:
        # raw_decode stops at the end of the first value, so trailing junk
        # after a complete object is simply discarded.
        value, _ = _decoder.raw_decode(text[min(starts) :])
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model did not return valid JSON: {raw!r}") from exc
    return value


def generate_parsed(
    prompt: str,
    client: "genai.Client | None" = None,
    attempts: int = 2,
) -> "dict | list":
    """Generates a response and decodes the JSON out of it.

    Malformed output is non-deterministic, so one regeneration usually
    clears it — cheaper than failing the caller's whole request.

    Args:
        prompt: The prompt to send.
        client: An existing Gemini client to reuse.
        attempts: How many times to generate before giving up.

    Returns:
        The decoded JSON object or array.

    Raises:
        ValueError: If every attempt produced unparseable output.
    """
    error: ValueError | None = None
    for _ in range(attempts):
        try:
            return parse_json(generate_json(prompt, client=client))
        except ValueError as exc:
            error = exc
    raise error


@_retry_transient
def generate_grounded(prompt: str, client: "genai.Client | None" = None):
    """Sends a prompt to Gemini with Google Search grounding enabled.

    Note that grounding is a billing-gated feature: on a free-tier key every
    call here raises 429 RESOURCE_EXHAUSTED, which Agent 2 catches and
    degrades from rather than retrying.

    Returns the whole response rather than just its text because callers need
    `candidates[0].grounding_metadata` to recover the source URLs behind the
    answer. Note that grounding and `response_mime_type: application/json`
    are mutually exclusive, so this returns prose — structure it in a
    separate `generate_json` call.

    Args:
        prompt: The search-shaped prompt to send.
        client: An existing Gemini client to reuse. A new one is created
            from GEMINI_API_KEY if omitted — pass one explicitly in tests.

    Returns:
        The raw SDK response object, including grounding metadata.
    """
    client = client or get_client()
    return client.models.generate_content(
        model=get_model(),
        contents=prompt,
        config={"tools": [{"google_search": {}}]},
    )
