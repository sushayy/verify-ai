"""Shared Gemini client wrapper used by all agents."""

import os

from google import genai

_MODEL = "gemini-3.5-flash"


def get_client() -> genai.Client:
    """Builds a Gemini API client from the GEMINI_API_KEY environment variable."""
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")
    return genai.Client()


def generate_json(prompt: str, client: "genai.Client | None" = None) -> str:
    """Sends a prompt to Gemini and returns the raw text response."""
    client = client or get_client()
    response = client.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config={"response_mime_type": "application/json"},
    )
    return response.text
