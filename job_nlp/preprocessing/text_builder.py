"""Build model input strings from title/description."""
from __future__ import annotations


def build(title_clean: str, description_clean: str) -> str:
    return f"[TITLE] {title_clean} [DESCRIPTION] {description_clean}"


def build_from_model_text(title_model: str, description_model: str) -> str:
    return build(title_model, description_model)


def build_plain(title_clean: str, description_clean: str) -> str:
    return f"{title_clean}\n{description_clean}".strip()
