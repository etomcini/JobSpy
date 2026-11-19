from __future__ import annotations

import math
import re
from urllib.parse import urlsplit, urlunsplit

CURRENCY_CODES = {
    "EUR",
    "USD",
    "GBP",
    "CHF",
}

CURRENCY_SYMBOLS = {
    "€": "EUR",
    "$": "USD",
    "£": "GBP",
}


def normalize_currency(value: object) -> str | None:
    """Normalize supported currency codes and symbols."""

    normalized = normalize_text(value)

    if normalized is None:
        return None

    if normalized in CURRENCY_SYMBOLS:
        return CURRENCY_SYMBOLS[normalized]

    code = normalized.upper()

    return code if code in CURRENCY_CODES else None


def normalize_salary_amount(value: object) -> float | None:
    """Return a valid non-negative salary amount or None."""

    if isinstance(value, bool):
        return None

    if not isinstance(value, (int, float)):
        return None

    amount = float(value)

    if not math.isfinite(amount) or amount < 0:
        return None

    return amount


def normalize_text(value: object) -> str | None:
    """Normalize whitespace and reject empty text values."""

    if not isinstance(value, str):
        return None

    normalized = " ".join(value.split())

    return normalized or None


def normalize_xing_job_url(value: object) -> str | None:
    """Return a canonical HTTPS XING job URL."""

    if not isinstance(value, str):
        return None

    value = value.strip()

    try:
        parsed = urlsplit(value)
    except ValueError:
        return None

    if parsed.scheme.lower() != "https":
        return None

    if parsed.hostname not in {"www.xing.com", "xing.com"}:
        return None

    try:
        port = parsed.port
    except ValueError:
        return None

    if port not in {None, 443}:
        return None

    if parsed.username is not None or parsed.password is not None:
        return None

    path = re.sub(r"/+", "/", parsed.path).rstrip("/")

    if not path.startswith("/jobs/"):
        return None

    if path == "/jobs" or path.startswith("/jobs/search/"):
        return None

    return urlunsplit(
        (
            "https",
            "www.xing.com",
            path,
            "",
            "",
        )
    )


def safe_dict(value: object) -> dict[str, object]:
    """Return a dictionary or an empty dictionary."""
    return value if isinstance(value, dict) else {}


def normalize_job_id(value: object) -> str | None:
    """Normalize a XING GraphQL job identifier."""

    normalized = normalize_text(value)

    if normalized is None:
        return None

    identifier = normalized.split(".", maxsplit=1)[0]

    return f"xing-{identifier}" if identifier else None


def normalize_xing_location(value: object) -> str | None:
    """Normalize a location label from a XING job card."""

    if not isinstance(value, str):
        return None

    location = " ".join(value.split())

    if not location:
        return None

    # Remove XING's additional-location counter.
    # Examples:
    # Berlin + 0 weitere
    # Berlin · + 2 weitere
    # Berlin + 1 weiterer
    location = re.sub(
        r"\s*(?:[·•]\s*)?\+\s*\d+\s+weitere(?:r)?\s*$",
        "",
        location,
        flags=re.IGNORECASE,
    )

    return location.strip() or None


def normalize_xing_description(
    description: str | None,
) -> str | None:
    """Remove leading artifacts from XING descriptions."""
    if not description:
        return None

    cleaned = re.sub(
        r"^\s*null[ \t]*(?:\r?\n)+",
        "",
        description,
        flags=re.IGNORECASE,
    )

    return cleaned.strip() or None
