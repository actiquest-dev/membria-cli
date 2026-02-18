"""Security utilities: sanitization and safe serialization."""

import json
import re
from typing import Any


_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]")
_DANGEROUS_TOKENS = [
    "<system>",
    "</system>",
    "<assistant>",
    "</assistant>",
    "<user>",
    "</user>",
]


def sanitize_text(value: str, max_len: int = 500) -> str:
    """Sanitize untrusted text before prompt injection or graph write."""
    if value is None:
        return ""

    # Remove control characters
    cleaned = _CONTROL_CHARS.sub("", str(value))

    # Neutralize common control tokens
    for token in _DANGEROUS_TOKENS:
        cleaned = cleaned.replace(token, f"[{token.strip('<>')}]")

    # Break code fences that can hijack formatting
    cleaned = cleaned.replace("```", "'''")

    # Normalize whitespace
    cleaned = " ".join(cleaned.split())

    if max_len and len(cleaned) > max_len:
        cleaned = cleaned[: max_len - 1] + "…"

    return cleaned


def sanitize_list(values: list[str], max_len: int = 500) -> list[str]:
    """Sanitize a list of strings."""
    return [sanitize_text(v, max_len=max_len) for v in (values or [])]


def safe_json_dumps(payload: Any) -> str:
    """JSON-encode with safe defaults and ASCII output."""
    return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))


def escape_cypher_string(value: str) -> str:
    """Escape string for Cypher queries."""
    if value is None:
        return ""
    return str(value).replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")
