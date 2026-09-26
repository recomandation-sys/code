"""Thresholds for the preprocessing gate. Defaults match the yaml file."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

_YAML = Path(__file__).resolve().parent / "preprocess_gate.yaml"
_REPO = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class GateConfig:
    high_confidence_en: float = 0.95
    chunk_confidence_en: float = 0.80
    min_description_words: int = 60
    chunk_words: int = 80
    min_substantive_chunk_words: int = 30
    max_description_chars: int = 50_000
    cleaning_version: str = "preprocess_clean_v1"
    language_model_path: str = "models/lid.176.bin"
    description_selectors: dict[str, str] = field(default_factory=dict)
    unwanted_selectors: dict[str, tuple[str, ...]] = field(default_factory=dict)
    boilerplate_lines: dict[str, tuple[str, ...]] = field(default_factory=dict)

    def model_path(self) -> Path:
        override = os.environ.get("PREPROCESS_LID_MODEL", "").strip()
        raw = override or self.language_model_path
        path = Path(raw)
        if not path.is_absolute():
            path = _REPO / path
        return path


def load_config(path: Path | None = None) -> GateConfig:
    file = path or _YAML
    if not file.is_file():
        return GateConfig()
    data = yaml.safe_load(file.read_text(encoding="utf-8")) or {}

    def lines(key: str) -> dict[str, tuple[str, ...]]:
        raw = data.get(key) or {}
        return {str(name): tuple(str(item) for item in values) for name, values in raw.items()}

    selectors = {str(k): str(v) for k, v in (data.get("description_selectors") or {}).items()}
    return GateConfig(
        high_confidence_en=float(data.get("high_confidence_en", 0.95)),
        chunk_confidence_en=float(data.get("chunk_confidence_en", 0.80)),
        min_description_words=int(data.get("min_description_words", 60)),
        chunk_words=int(data.get("chunk_words", 80)),
        min_substantive_chunk_words=int(data.get("min_substantive_chunk_words", 30)),
        max_description_chars=int(data.get("max_description_chars", 50_000)),
        cleaning_version=str(data.get("cleaning_version", "preprocess_clean_v1")),
        language_model_path=str(data.get("language_model_path", "models/lid.176.bin")),
        description_selectors=selectors,
        unwanted_selectors=lines("unwanted_selectors"),
        boilerplate_lines=lines("boilerplate_lines"),
    )
