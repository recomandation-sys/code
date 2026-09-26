"""Production-equivalent title_model / description_model derivation."""
from __future__ import annotations

import re
import unicodedata

from job_nlp.preprocessing.cleaner import clean_description, clean_title

# The lookarounds keep a word-final letter out of the match: without them
# "Applicatif - H/F" matches F-H across "f - H" and loses the "f".
_GENDER_NOISE = re.compile(
    r"\s*[\(\[]?\s*"
    r"(?<![^\W\d_])(?:H\s*[/\-]\s*F|F\s*[/\-]\s*H|M\s*/\s*F\s*/\s*X)(?![^\W\d_])"
    r"\s*[\)\]]?\s*",
    re.IGNORECASE,
)


def strip_gender_noise(title: str) -> str:
    """Remove H/F-style suffixes from derived title only."""
    out = _GENDER_NOISE.sub(" ", title)
    return re.sub(r"\s{2,}", " ", out).strip(" -–—,")


def to_model_text(title: str, description: str) -> tuple[str, str]:
    title_clean = clean_title(title)
    description_clean = clean_description(description)
    title_model = strip_gender_noise(title_clean)
    return title_model, description_clean
