"""Structural tests for the Verify AI agent pipeline.

Everything runs against a mocked Gemini client and a stubbed vector store, so
the suite needs no API key, no network, and burns no free-tier quota. The
fake-client pattern is carried over from the original CLI's test_pipeline.py.
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

import main
from agents import evidence_retrieval_agent, fact_check_agent, report_agent
from agents.fact_check_agent import Verdict, fact_check
from agents.report_agent import generate_report
from models import Evidence, StructuredClaim, VerificationReport
from services import credibility, gemini_client, vector_store
from services.credibility import score_source
from services.gemini_client import _is_rate_limited, _is_transient, parse_json


def _response(payload: "dict | list") -> SimpleNamespace:
    """Builds a fake Gemini JSON response wrapping the given object."""
    return SimpleNamespace(text=json.dumps(payload))


def _claim(statement: str = "The sky is blue.") -> StructuredClaim:
    """Builds a StructuredClaim for use as agent input."""
    return StructuredClaim(
        original_text=statement,
        normalized_statement=statement,
        entities=["sky"],
        dates=[],
        claim_type="general_fact",
    )


def _evidence(
    source_name: str = "Reference",
    text: str = "The sky appears blue.",
    stance: str = "supporting",
    reliability: float = 0.7,
) -> Evidence:
    """Builds an Evidence item with sensible defaults."""
    return Evidence(
        source_name=source_name,
        url=None,
        extracted_text=text,
        stance=stance,
        reliability_score=reliability,
    )


@pytest.fixture
def fake_client() -> MagicMock:
    """A mock Gemini client that routes on prompt content.

    Returns:
        A MagicMock whose generate_content returns a canned stance response
        for Agent 2's prompt and a canned verdict for Agent 3's.
    """
    client = MagicMock()

    def generate_content(model, contents, config=None):
        if "PASSAGES:" in contents:
            return _response(
                {
                    "stances": [
                        {"index": 0, "stance": "supporting"},
                        {"index": 1, "stance": "contradicting"},
                    ]
                }
            )
        return _response(
            {
                "final_result": "TRUE",
                "confidence_score": 0.9,
                "explanation": "The reliable sources agree with the claim.",
            }
        )

    client.models.generate_content.side_effect = generate_content
    return client


def _raises_value_error(prompt, client=None):
    """Stands in for a model whose output could not be parsed."""
    raise ValueError("Model did not return valid JSON")


def _grounded_response() -> SimpleNamespace:
    """Builds a fake grounded response with two web sources and citations."""
    return SimpleNamespace(
        text="Reliable sources broadly agree.",
        candidates=[
            SimpleNamespace(
                grounding_metadata=SimpleNamespace(
                    grounding_chunks=[
                        SimpleNamespace(
                            web=SimpleNamespace(
                                uri="https://vertexaisearch.example/redirect/1",
                                domain="nasa.gov",
                                title="NASA",
                            )
                        ),
                        SimpleNamespace(
                            web=SimpleNamespace(
                                uri="https://vertexaisearch.example/redirect/2",
                                domain="someblog.medium.com",
                                title="Someone's blog",
                            )
                        ),
                    ],
                    grounding_supports=[
                        SimpleNamespace(
                            segment=SimpleNamespace(text="Rayleigh scattering explains it."),
                            grounding_chunk_indices=[0],
                        ),
                        SimpleNamespace(
                            segment=SimpleNamespace(text="A blog disagrees."),
                            grounding_chunk_indices=[1],
                        ),
                    ],
                )
            )
        ],
    )


# --- services/gemini_client.py ------------------------------------------------


def test_parse_json_tolerates_trailing_brace() -> None:
    """The real failure seen live: Gemini appended a stray closing brace."""
    assert parse_json('{"a": 1}\n}\n') == {"a": 1}


def test_parse_json_strips_markdown_fence() -> None:
    """A fenced code block is unwrapped rather than rejected."""
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_parse_json_handles_prose_prefix_and_arrays() -> None:
    """Leading prose is skipped and top-level arrays decode fine."""
    assert parse_json('Here you go: [1, 2]') == [1, 2]


@pytest.mark.parametrize("raw", ["", "   ", None, "no json at all"])
def test_parse_json_rejects_unusable_responses(raw) -> None:
    """Genuinely unparseable output still raises rather than guessing."""
    with pytest.raises(ValueError):
        parse_json(raw)


def test_transient_errors_are_retried_but_quota_is_not() -> None:
    """Overload is retryable; a billing-gated quota error is not."""
    assert _is_transient(RuntimeError("503 UNAVAILABLE. high demand"))
    assert _is_transient(RuntimeError("500 INTERNAL"))
    assert not _is_transient(RuntimeError("429 RESOURCE_EXHAUSTED. quota"))


def test_windowed_rate_limit_is_distinguished_from_billing_gate() -> None:
    """Only a quota error carrying a retry hint is worth waiting out."""
    assert _is_rate_limited(
        RuntimeError("429 RESOURCE_EXHAUSTED. limit: 20. Please retry in 38.3s")
    )
    # Grounded search on a free key fails like this, and never clears.
    assert not _is_rate_limited(
        RuntimeError("429 RESOURCE_EXHAUSTED. check your plan and billing details")
    )
    # The per-day cap quotes a short retry delay but will not clear today.
    assert not _is_rate_limited(
        RuntimeError(
            "429 RESOURCE_EXHAUSTED. quotaId: "
            "'GenerateRequestsPerDayPerProjectPerModel-FreeTier'. Please retry in 47s"
        )
    )


def test_generate_parsed_retries_unparseable_output(monkeypatch) -> None:
    """One bad generation is regenerated rather than failing the request."""
    responses = iter(["not json at all", '{"ok": true}'])
    monkeypatch.setattr(
        gemini_client, "generate_json", lambda prompt, client=None: next(responses)
    )
    assert gemini_client.generate_parsed("p") == {"ok": True}


def test_generate_parsed_gives_up_after_all_attempts(monkeypatch) -> None:
    """Persistently unparseable output still raises."""
    monkeypatch.setattr(gemini_client, "generate_json", lambda prompt, client=None: "junk")
    with pytest.raises(ValueError):
        gemini_client.generate_parsed("p")


# --- services/credibility.py -------------------------------------------------


@pytest.mark.parametrize(
    "url,expected",
    [
        ("https://www.cdc.gov/some/page", credibility.GOVERNMENT_OR_ACADEMIC),
        ("https://data.nasa.gov/x", credibility.GOVERNMENT_OR_ACADEMIC),
        ("https://mit.edu/research", credibility.GOVERNMENT_OR_ACADEMIC),
        ("https://www.reuters.com/world/x", credibility.MAJOR_OUTLET),
        ("https://www.nature.com/articles/x", credibility.MAJOR_OUTLET),
        ("https://en.wikipedia.org/wiki/Sky", credibility.REFERENCE_WORK),
        ("https://someone.medium.com/post", credibility.USER_GENERATED),
        ("https://www.reddit.com/r/x", credibility.USER_GENERATED),
        ("https://random-unknown-site.xyz/a", credibility.UNKNOWN),
        ("", credibility.UNKNOWN),
    ],
)
def test_score_source_ranks_domains(url: str, expected: float) -> None:
    """Domains map to the reliability tier the project spec calls for."""
    assert score_source(url=url) == expected


def test_score_source_accepts_bare_domain_as_publisher() -> None:
    """A bare domain with no URL still scores, via the publisher fallback."""
    assert score_source(url=None, publisher="bbc.co.uk") == credibility.MAJOR_OUTLET


def test_user_generated_beats_domain_lists() -> None:
    """A blog on a UGC platform doesn't inherit the platform's reputation."""
    assert score_source(url="https://fake-news.wordpress.com") == credibility.USER_GENERATED


# --- services/vector_store.py -------------------------------------------------


def test_chunk_text_keeps_whole_sentences() -> None:
    """Chunks break on sentence boundaries, never mid-word."""
    text = " ".join(f"Sentence number {i} runs on for a little while." for i in range(40))
    chunks = vector_store._chunk_text(text, size=200)

    assert len(chunks) > 1
    for chunk in chunks:
        assert chunk == chunk.strip()
        assert chunk.endswith(".")
    # Nothing is lost or duplicated in the repacking.
    assert " ".join(chunks) == text


def test_chunk_text_normalizes_hard_wrapping() -> None:
    """Corpus files are hard-wrapped; chunks come out as single-spaced prose."""
    assert vector_store._chunk_text("The sky\nis  blue.\nIt scatters light.") == [
        "The sky is blue. It scatters light."
    ]


def test_query_drops_hits_beyond_max_distance(monkeypatch) -> None:
    """Irrelevant matches are filtered out instead of padding the results."""
    fake = MagicMock()
    fake.count.return_value = 3
    fake.query.return_value = {
        "documents": [["near", "far", "very far"]],
        "metadatas": [[{"filename": "a"}, {"filename": "b"}, {"filename": "c"}]],
        "distances": [[0.4, 1.5, 1.9]],
    }
    monkeypatch.setattr(vector_store, "get_collection", lambda db_path=None: fake)

    hits = vector_store.query("anything", k=3)
    assert [h["document"] for h in hits] == ["near"]


def test_query_returns_empty_for_unpopulated_store(monkeypatch) -> None:
    """An un-ingested store yields no evidence rather than raising."""
    fake = MagicMock()
    fake.count.return_value = 0
    monkeypatch.setattr(vector_store, "get_collection", lambda db_path=None: fake)
    assert vector_store.query("anything") == []


# --- Agent 2: evidence retrieval ---------------------------------------------


def test_retrieve_evidence_combines_corpus_and_web(monkeypatch, fake_client) -> None:
    """Agent 2 merges corpus and web hits, scores them, and sorts by reliability."""
    monkeypatch.setattr(
        vector_store,
        "query",
        lambda text, k=4: [
            {
                "document": "The sky scatters blue light.",
                "metadata": {
                    "title": "Sky",
                    "url": "https://en.wikipedia.org/wiki/Sky",
                    "reliability": 0.7,
                },
                "distance": 0.1,
            }
        ],
    )
    monkeypatch.setattr(
        evidence_retrieval_agent,
        "generate_grounded",
        lambda prompt, client=None: _grounded_response(),
    )

    evidence = evidence_retrieval_agent.retrieve_evidence(_claim(), client=fake_client)

    assert [e.source_name for e in evidence] == ["NASA", "Sky", "Someone's blog"]
    # Sorted by descending reliability: .gov 0.95, corpus 0.7, medium.com 0.25.
    assert [e.reliability_score for e in evidence] == [0.95, 0.7, 0.25]
    assert evidence[0].url == "https://vertexaisearch.example/redirect/1"
    assert evidence[0].extracted_text == "Rayleigh scattering explains it."


def test_retrieve_evidence_handles_ungrounded_response(monkeypatch, fake_client) -> None:
    """A response with no grounding metadata yields corpus evidence only."""
    monkeypatch.setattr(vector_store, "query", lambda text, k=4: [])
    monkeypatch.setattr(
        evidence_retrieval_agent,
        "generate_grounded",
        lambda prompt, client=None: SimpleNamespace(text="No search performed.", candidates=[]),
    )
    assert evidence_retrieval_agent.retrieve_evidence(_claim(), client=fake_client) == []


def test_retrieve_evidence_survives_web_search_failure(monkeypatch, fake_client) -> None:
    """A quota-blocked web search degrades to corpus evidence, not an error."""
    monkeypatch.setattr(
        vector_store,
        "query",
        lambda text, k=4: [
            {"document": "Corpus text.", "metadata": {"title": "Corpus", "reliability": 0.7}, "distance": 0.1}
        ],
    )

    def quota_exceeded(prompt, client=None):
        raise RuntimeError("429 RESOURCE_EXHAUSTED")

    monkeypatch.setattr(evidence_retrieval_agent, "generate_grounded", quota_exceeded)

    evidence = evidence_retrieval_agent.retrieve_evidence(_claim(), client=fake_client)
    assert [e.source_name for e in evidence] == ["Corpus"]


def test_web_search_can_be_disabled(monkeypatch, fake_client) -> None:
    """ENABLE_WEB_SEARCH=false skips the grounded call entirely."""
    monkeypatch.setenv("ENABLE_WEB_SEARCH", "false")
    monkeypatch.setattr(vector_store, "query", lambda text, k=4: [])

    def fail(prompt, client=None):
        raise AssertionError("web search should not have been attempted")

    monkeypatch.setattr(evidence_retrieval_agent, "generate_grounded", fail)
    assert evidence_retrieval_agent.retrieve_evidence(_claim(), client=fake_client) == []


def test_tag_stances_defaults_to_neutral_on_bad_json(monkeypatch) -> None:
    """A malformed stance response degrades to neutral instead of raising."""
    monkeypatch.setattr(
        evidence_retrieval_agent, "generate_parsed", _raises_value_error
    )
    candidates = [{"extracted_text": "a"}, {"extracted_text": "b"}]
    assert evidence_retrieval_agent._tag_stances(_claim(), candidates) == ["neutral", "neutral"]


def test_tag_stances_ignores_out_of_range_indices(monkeypatch) -> None:
    """Stance entries pointing past the passage list are dropped safely."""
    monkeypatch.setattr(
        evidence_retrieval_agent,
        "generate_parsed",
        lambda prompt, client=None: {
            "stances": [
                {"index": 0, "stance": "contradicting"},
                {"index": 9, "stance": "supporting"},
            ]
        },
    )
    candidates = [{"extracted_text": "a"}]
    assert evidence_retrieval_agent._tag_stances(_claim(), candidates) == ["contradicting"]


# --- Agent 3: fact checking ---------------------------------------------------


def test_fact_check_parses_verdict(fake_client) -> None:
    """Agent 3 turns the model's JSON into a Verdict."""
    verdict = fact_check(_claim(), [_evidence()], client=fake_client)
    assert verdict.final_result == "TRUE"
    assert 0.0 <= verdict.confidence_score <= 1.0
    assert verdict.explanation


def test_fact_check_short_circuits_without_evidence(fake_client) -> None:
    """Empty evidence returns UNVERIFIED without calling the model at all."""
    verdict = fact_check(_claim(), [], client=fake_client)
    assert verdict.final_result == "UNVERIFIED"
    fake_client.models.generate_content.assert_not_called()


def test_fact_check_clamps_out_of_range_confidence(monkeypatch) -> None:
    """A confidence above 1 is clamped before it reaches Pydantic validation."""
    monkeypatch.setattr(
        fact_check_agent,
        "generate_parsed",
        lambda prompt, client=None: {
            "final_result": "FALSE",
            "confidence_score": 4.2,
            "explanation": "x",
        },
    )
    assert fact_check(_claim(), [_evidence()]).confidence_score == 1.0


def test_fact_check_rejects_unknown_classification(monkeypatch) -> None:
    """A verdict outside the contract's enum is an error, not a silent default."""
    monkeypatch.setattr(
        fact_check_agent,
        "generate_parsed",
        lambda prompt, client=None: {
            "final_result": "PROBABLY",
            "confidence_score": 0.5,
            "explanation": "x",
        },
    )
    with pytest.raises(ValueError, match="unknown final_result"):
        fact_check(_claim(), [_evidence()])


# --- Agent 4: report generation ----------------------------------------------


def test_generate_report_dedupes_sorts_and_caps() -> None:
    """Agent 4 drops duplicate passages, sorts by reliability, and caps the list."""
    evidence = [_evidence("Dup", "same text", reliability=0.4)] * 2
    evidence += [
        _evidence(f"Source {i}", f"text {i}", reliability=0.5 + i / 100) for i in range(8)
    ]

    report = generate_report(_claim(), evidence, Verdict("TRUE", 0.8, "  spaced   out  "))

    assert isinstance(report, VerificationReport)
    assert len(report.evidence) == report_agent._MAX_EVIDENCE
    scores = [e.reliability_score for e in report.evidence]
    assert scores == sorted(scores, reverse=True)
    assert report.explanation == "spaced out"


def test_generate_report_handles_no_evidence() -> None:
    """An evidence-free verdict still produces a valid report."""
    report = generate_report(_claim(), [], Verdict("UNVERIFIED", 0.2, "Nothing found."))
    assert report.evidence == []
    assert report.final_result == "UNVERIFIED"


# --- /verify endpoint ---------------------------------------------------------


@pytest.fixture
def client(monkeypatch) -> TestClient:
    """A TestClient with the whole pipeline stubbed out.

    Instantiated without a `with` block so the startup corpus ingest never
    runs, keeping the endpoint tests offline.
    """
    monkeypatch.setattr(main, "analyze_claim", lambda text: _claim(text))
    monkeypatch.setattr(main, "retrieve_evidence", lambda claim: [_evidence()])
    monkeypatch.setattr(
        main, "fact_check", lambda claim, evidence: Verdict("TRUE", 0.9, "Because.")
    )
    return TestClient(main.app)


def test_verify_returns_report_shape(client) -> None:
    """/verify returns JSON matching the locked VerificationReport contract."""
    response = client.post("/verify", json={"claim_text": "The sky is blue."})
    assert response.status_code == 200

    body = response.json()
    # Parsing back into the model is the contract check the backend relies on.
    report = VerificationReport.model_validate(body)
    assert report.final_result == "TRUE"
    assert report.claim.original_text == "The sky is blue."
    assert body["evidence"][0]["stance"] == "supporting"


def test_verify_rejects_empty_claim(client) -> None:
    """A blank claim is a client error, not a pipeline run."""
    assert client.post("/verify", json={"claim_text": "   "}).status_code == 400


def test_verify_returns_502_when_pipeline_fails(client, monkeypatch) -> None:
    """An upstream model failure surfaces as 502 so the backend marks it failed."""

    def boom(text):
        raise RuntimeError("GEMINI_API_KEY environment variable is not set.")

    monkeypatch.setattr(main, "analyze_claim", boom)
    assert client.post("/verify", json={"claim_text": "x"}).status_code == 502
