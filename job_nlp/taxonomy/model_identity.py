"""Public model identifiers for production metadata."""
from __future__ import annotations

import re


E5_MODEL_ID = "Misbahuddin/job-title-normalizer-e5-base"


def public_model_identifier(value: object) -> str:
    """Redact local paths while preserving the logical model identity."""
    raw = str(value or "").strip()
    normalized = raw.replace("\\", "/")
    if not normalized or normalized.casefold() == "local-e5":
        return E5_MODEL_ID if normalized.casefold() == "local-e5" else "unknown"
    if "job-title-normalizer-e5-base" in normalized.casefold():
        return E5_MODEL_ID
    # A local path must never cross the API boundary.  Keep only its final
    # component as a useful diagnostic without exposing usernames or folders.
    if re.match(r"^(?:[A-Za-z]:/|/|//)", normalized):
        return normalized.rstrip("/").rsplit("/", 1)[-1] or "unknown"
    return raw
