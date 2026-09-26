"""Small, explicit configuration surface for education normalization."""
from __future__ import annotations

import os

COUNTRY = os.getenv("EDUCATION_COUNTRY", "MA").upper()
# Only entries that differ materially from the default belong here.
JURISDICTION_ALIASES: dict[str, dict[str, str]] = {
    "UK": {"hnd": "SHORT_CYCLE_TERTIARY", "a-levels": "SECONDARY"},
    "IN": {"higher secondary": "SECONDARY"},
    "DE": {"abitur": "SECONDARY"},
}
