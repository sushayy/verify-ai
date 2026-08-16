"""Rules-based source credibility scoring for retrieved evidence.

Pure functions — no API calls and no network — so Agent 2 can score every
candidate passage for free, and every rule here is directly unit-testable.

The ranking follows the project spec: government and academic sources rank
above major outlets and journals, which rank above general reference works,
which rank above unknown domains and user-generated content.
"""

from urllib.parse import urlparse

GOVERNMENT_OR_ACADEMIC = 0.95
MAJOR_OUTLET = 0.85
REFERENCE_WORK = 0.7
UNKNOWN = 0.4
USER_GENERATED = 0.25

# Matched as a suffix of the hostname, so `cdc.gov` and `data.cdc.gov` both hit.
_HIGH_TRUST_SUFFIXES = (
    ".gov",
    ".edu",
    ".int",
    ".mil",
    ".ac.uk",
    ".gov.uk",
    ".edu.au",
    ".gov.au",
    ".ac.jp",
)

_MAJOR_OUTLET_DOMAINS = frozenset(
    {
        # Wire services and broadcasters with published corrections policies.
        "reuters.com",
        "apnews.com",
        "afp.com",
        "bbc.com",
        "bbc.co.uk",
        "npr.org",
        "pbs.org",
        # Newspapers of record.
        "nytimes.com",
        "washingtonpost.com",
        "theguardian.com",
        "ft.com",
        "wsj.com",
        "economist.com",
        # Peer-reviewed journals and scientific publishers.
        "nature.com",
        "science.org",
        "sciencedirect.com",
        "thelancet.com",
        "nejm.org",
        "bmj.com",
        "cell.com",
        "pnas.org",
        "plos.org",
    }
)

_REFERENCE_DOMAINS = frozenset(
    {
        "wikipedia.org",
        "britannica.com",
        "snopes.com",
        "factcheck.org",
        "politifact.com",
        "fullfact.org",
    }
)

# Platforms where anyone can publish, so the domain says nothing about the
# reliability of the individual page.
_USER_GENERATED_DOMAINS = frozenset(
    {
        "medium.com",
        "substack.com",
        "reddit.com",
        "quora.com",
        "x.com",
        "twitter.com",
        "facebook.com",
        "instagram.com",
        "tiktok.com",
        "youtube.com",
        "blogspot.com",
        "wordpress.com",
        "tumblr.com",
        "wixsite.com",
    }
)


def _hostname(value: str) -> str:
    """Extracts a bare lowercase hostname from a URL or a bare domain.

    Args:
        value: A full URL, or something that may already be a hostname.

    Returns:
        The hostname without a `www.` prefix, or an empty string if none
        could be parsed.
    """
    if not value:
        return ""
    # urlparse only populates .hostname when there's a `//`, so add one for
    # bare domains like "reuters.com".
    parsed = urlparse(value if "//" in value else f"//{value.strip()}")
    return (parsed.hostname or "").lower().removeprefix("www.")


def _matches(host: str, domains: frozenset) -> bool:
    """Reports whether a hostname is one of `domains` or a subdomain of one."""
    return any(host == domain or host.endswith(f".{domain}") for domain in domains)


def score_source(url: "str | None" = None, publisher: "str | None" = None) -> float:
    """Scores how reliable a source is, from 0 to 1, from its domain.

    Args:
        url: The URL the evidence was retrieved from, if any.
        publisher: A publisher name or bare domain, used as a fallback when
            no URL is available.

    Returns:
        A reliability score in [0, 1]. Unrecognized sources get a neutral
        `UNKNOWN` score rather than being penalized as untrustworthy.
    """
    host = _hostname(url or "") or _hostname(publisher or "")
    if not host:
        return UNKNOWN

    # Checked before the domain lists so a blog on a UGC platform can't
    # inherit the platform's reputation.
    if _matches(host, _USER_GENERATED_DOMAINS):
        return USER_GENERATED
    if host.endswith(_HIGH_TRUST_SUFFIXES):
        return GOVERNMENT_OR_ACADEMIC
    if _matches(host, _MAJOR_OUTLET_DOMAINS):
        return MAJOR_OUTLET
    if _matches(host, _REFERENCE_DOMAINS):
        return REFERENCE_WORK
    return UNKNOWN
