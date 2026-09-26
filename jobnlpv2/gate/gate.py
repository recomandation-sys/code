"""English description gate. Decisions are ACCEPT or REFUSE. No review state.

This is a predominantly-English check, not proof that every sentence is English.
A score at or above high_confidence_en accepts after one prediction and does not
look at chunks, so a non-English later section can still pass. Confirmation uses
only the first two substantive chunks, and only when the full-text English score
is uncertain. Text after those two chunks is ignored.

No IT, skill, or taxonomy rule runs here.
"""
from __future__ import annotations

import logging
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from . import text as text_stage
from .config import GateConfig, load_config
from .language import ModelUnavailable, Predictor
from .text import (
    DESCRIPTION_SELECTOR_NOT_FOUND,
    HTML_PARSE_FAILED,
    INPUT_MODES,
    IsolateError,
)

logger = logging.getLogger("job_nlp.ingestion.preprocess")

ACCEPT = "ACCEPT"
REFUSE = "REFUSE"
DECISIONS = frozenset({ACCEPT, REFUSE})

MISSING_DESCRIPTION = "MISSING_DESCRIPTION"
MISSING_JOB_IDENTITY = "MISSING_JOB_IDENTITY"
UNSUPPORTED_INPUT_MODE = "UNSUPPORTED_INPUT_MODE"
EMPTY_DESCRIPTION = "EMPTY_DESCRIPTION"
DESCRIPTION_TOO_SHORT = "DESCRIPTION_TOO_SHORT"
DESCRIPTION_TOO_LARGE = "DESCRIPTION_TOO_LARGE"
LANGUAGE_MODEL_UNAVAILABLE = "LANGUAGE_MODEL_UNAVAILABLE"
LANGUAGE_PREDICT_FAILED = "LANGUAGE_PREDICT_FAILED"
HIGH_CONFIDENCE_ENGLISH = "HIGH_CONFIDENCE_ENGLISH"
NON_ENGLISH_DESCRIPTION = "NON_ENGLISH_DESCRIPTION"
INSUFFICIENT_TEXT_FOR_CHUNK_CONFIRMATION = "INSUFFICIENT_TEXT_FOR_CHUNK_CONFIRMATION"
CHUNK_LANGUAGE_MISMATCH = "CHUNK_LANGUAGE_MISMATCH"
LOW_CHUNK_ENGLISH_CONFIDENCE = "LOW_CHUNK_ENGLISH_CONFIDENCE"
ENGLISH_CONFIRMED_BY_TWO_CHUNKS = "ENGLISH_CONFIRMED_BY_TWO_CHUNKS"

REFUSE_REASONS = frozenset({
    MISSING_DESCRIPTION,
    MISSING_JOB_IDENTITY,
    UNSUPPORTED_INPUT_MODE,
    DESCRIPTION_SELECTOR_NOT_FOUND,
    HTML_PARSE_FAILED,
    EMPTY_DESCRIPTION,
    DESCRIPTION_TOO_SHORT,
    DESCRIPTION_TOO_LARGE,
    LANGUAGE_MODEL_UNAVAILABLE,
    LANGUAGE_PREDICT_FAILED,
    NON_ENGLISH_DESCRIPTION,
    INSUFFICIENT_TEXT_FOR_CHUNK_CONFIRMATION,
    CHUNK_LANGUAGE_MISMATCH,
    LOW_CHUNK_ENGLISH_CONFIDENCE,
})
ACCEPT_REASONS = frozenset({HIGH_CONFIDENCE_ENGLISH, ENGLISH_CONFIRMED_BY_TWO_CHUNKS})

METRICS: Counter[str] = Counter()


@dataclass
class GateInput:
    source: str
    description: str | None
    description_mode: str
    source_job_id: str | None = None
    canonical_url: str | None = None
    title: str = ""
    company: str | None = None
    location: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class GateResult:
    decision: str
    reason: str
    source: str
    source_job_id: str | None
    canonical_url: str | None
    clean_description: str | None = field(repr=False)
    detected_language: str | None
    language_score: float | None
    predictions_count: int
    cleaning_version: str
    language_model_version: str
    total_latency_ms: float
    stage_latency_ms: dict[str, float] = field(default_factory=dict)
    raw_description: str | None = field(default=None, repr=False)
    extracted_description: str | None = field(default=None, repr=False)
    cleaned_description: str | None = field(default=None, repr=False)
    chunk_predictions: list[dict[str, Any]] = field(default_factory=list, repr=False)

    def public_dict(self) -> dict[str, Any]:
        if self.decision not in DECISIONS:
            raise RuntimeError(f"invalid decision: {self.decision}")
        return {
            "decision": self.decision,
            "reason": self.reason,
            "source": self.source,
            "source_job_id": self.source_job_id,
            "canonical_url": self.canonical_url,
            "clean_description": self.clean_description if self.decision == ACCEPT else None,
            "detected_language": self.detected_language,
            "language_score": self.language_score,
            "predictions_count": self.predictions_count,
            "cleaning_version": self.cleaning_version,
            "language_model_version": self.language_model_version,
            "total_latency_ms": self.total_latency_ms,
            "stage_latency_ms": self.stage_latency_ms,
        }


def _raw_for_audit(description: str | None, limit: int) -> str | None:
    if not isinstance(description, str) or len(description) > limit:
        return None
    return description


def _record(result: GateResult, metrics: Counter[str]) -> None:
    metrics[result.reason] += 1
    metrics[f"decision:{result.decision}"] += 1
    metrics[f"predictions:{result.predictions_count}"] += 1
    if result.reason == DESCRIPTION_SELECTOR_NOT_FOUND:
        metrics["selector_failures"] += 1
    elif result.reason == HTML_PARSE_FAILED:
        metrics["parse_failures"] += 1
    elif result.reason in {
        NON_ENGLISH_DESCRIPTION,
        CHUNK_LANGUAGE_MISMATCH,
        LOW_CHUNK_ENGLISH_CONFIDENCE,
        INSUFFICIENT_TEXT_FOR_CHUNK_CONFIRMATION,
    }:
        metrics["language_refusals"] += 1
    elif result.reason == LANGUAGE_MODEL_UNAVAILABLE:
        metrics["model_unavailable"] += 1
    logger.info(
        "preprocess_gate decision=%s reason=%s source=%s source_job_id=%s predictions=%s latency_ms=%.2f",
        result.decision,
        result.reason,
        result.source,
        result.source_job_id or "",
        result.predictions_count,
        result.total_latency_ms,
    )


def run_gate(
    offer: GateInput,
    predictor: Predictor | None,
    config: GateConfig | None = None,
    metrics: Counter[str] | None = None,
) -> GateResult:
    cfg = config or load_config()
    started = time.perf_counter()
    stages: dict[str, float] = {}
    version = getattr(predictor, "version", None) or "unavailable"
    bucket = metrics if metrics is not None else METRICS

    def finish(reason: str, *, decision: str = REFUSE, **kwargs: Any) -> GateResult:
        result = GateResult(
            decision=decision,
            reason=reason,
            source=offer.source or "",
            source_job_id=offer.source_job_id,
            canonical_url=offer.canonical_url,
            cleaning_version=cfg.cleaning_version,
            language_model_version=version,
            total_latency_ms=round((time.perf_counter() - started) * 1000, 3),
            stage_latency_ms={key: round(value * 1000, 3) for key, value in stages.items()},
            raw_description=_raw_for_audit(offer.description, cfg.max_description_chars),
            predictions_count=kwargs.pop("predictions_count", 0),
            clean_description=None,
            detected_language=kwargs.pop("detected_language", None),
            language_score=kwargs.pop("language_score", None),
            **kwargs,
        )
        if result.decision == ACCEPT:
            result.clean_description = result.cleaned_description
        else:
            result.clean_description = None
        _record(result, bucket)
        return result

    if not (offer.source_job_id or offer.canonical_url) or not (offer.source or "").strip():
        return finish(MISSING_JOB_IDENTITY)
    if offer.description_mode not in INPUT_MODES:
        return finish(UNSUPPORTED_INPUT_MODE)
    if not isinstance(offer.description, str) or not offer.description.strip():
        return finish(MISSING_DESCRIPTION)

    stamp = time.perf_counter()
    try:
        extracted = text_stage.isolate_description(
            offer.description,
            mode=offer.description_mode,
            source=offer.source,
            config=cfg,
        )
    except IsolateError as exc:
        stages["isolate"] = time.perf_counter() - stamp
        return finish(exc.reason, extracted_description=None)
    stages["isolate"] = time.perf_counter() - stamp

    stamp = time.perf_counter()
    cleaned = text_stage.clean_description(extracted, source=offer.source, config=cfg)
    stages["clean"] = time.perf_counter() - stamp

    stamp = time.perf_counter()
    if not cleaned:
        stages["quality"] = time.perf_counter() - stamp
        return finish(EMPTY_DESCRIPTION, extracted_description=extracted, cleaned_description=cleaned)
    if len(cleaned) > cfg.max_description_chars:
        stages["quality"] = time.perf_counter() - stamp
        return finish(DESCRIPTION_TOO_LARGE, extracted_description=None, cleaned_description=None)
    if text_stage.meaningful_word_count(cleaned) < cfg.min_description_words:
        stages["quality"] = time.perf_counter() - stamp
        return finish(
            DESCRIPTION_TOO_SHORT,
            extracted_description=extracted,
            cleaned_description=cleaned,
        )
    stages["quality"] = time.perf_counter() - stamp

    if predictor is None:
        return finish(
            LANGUAGE_MODEL_UNAVAILABLE,
            extracted_description=extracted,
            cleaned_description=cleaned,
        )

    predictions = 0
    stamp = time.perf_counter()
    try:
        language, score = predictor.predict(text_stage.prediction_line(cleaned))
        predictions += 1
    except ModelUnavailable:
        stages["language"] = time.perf_counter() - stamp
        return finish(
            LANGUAGE_MODEL_UNAVAILABLE,
            predictions_count=predictions,
            extracted_description=extracted,
            cleaned_description=cleaned,
        )
    except Exception:
        stages["language"] = time.perf_counter() - stamp
        logger.warning(
            "preprocess_gate language_predict_failed source=%s source_job_id=%s",
            offer.source,
            offer.source_job_id or "",
        )
        return finish(
            LANGUAGE_PREDICT_FAILED,
            predictions_count=predictions,
            extracted_description=extracted,
            cleaned_description=cleaned,
        )

    common = dict(
        detected_language=language,
        language_score=score,
        extracted_description=extracted,
        cleaned_description=cleaned,
    )
    if language == "en" and score >= cfg.high_confidence_en:
        stages["language"] = time.perf_counter() - stamp
        return finish(
            HIGH_CONFIDENCE_ENGLISH,
            decision=ACCEPT,
            predictions_count=predictions,
            **common,
        )
    if language != "en":
        stages["language"] = time.perf_counter() - stamp
        return finish(NON_ENGLISH_DESCRIPTION, predictions_count=predictions, **common)

    chunks = text_stage.confirmation_chunks(cleaned, cfg)
    if chunks is None:
        stages["language"] = time.perf_counter() - stamp
        return finish(
            INSUFFICIENT_TEXT_FOR_CHUNK_CONFIRMATION,
            predictions_count=predictions,
            **common,
        )
    chunk_predictions: list[dict[str, Any]] = []
    try:
        for chunk in chunks:
            chunk_language, chunk_score = predictor.predict(text_stage.prediction_line(chunk))
            predictions += 1
            chunk_predictions.append({"language": chunk_language, "score": chunk_score})
    except ModelUnavailable:
        stages["language"] = time.perf_counter() - stamp
        return finish(
            LANGUAGE_MODEL_UNAVAILABLE,
            predictions_count=predictions,
            chunk_predictions=chunk_predictions,
            **common,
        )
    except Exception:
        stages["language"] = time.perf_counter() - stamp
        return finish(
            LANGUAGE_PREDICT_FAILED,
            predictions_count=predictions,
            chunk_predictions=chunk_predictions,
            **common,
        )
    stages["language"] = time.perf_counter() - stamp
    languages = [item["language"] for item in chunk_predictions]
    scores = [item["score"] for item in chunk_predictions]
    if languages != ["en", "en"]:
        return finish(
            CHUNK_LANGUAGE_MISMATCH,
            predictions_count=predictions,
            chunk_predictions=chunk_predictions,
            **common,
        )
    if any(item < cfg.chunk_confidence_en for item in scores):
        return finish(
            LOW_CHUNK_ENGLISH_CONFIDENCE,
            predictions_count=predictions,
            chunk_predictions=chunk_predictions,
            **common,
        )
    return finish(
        ENGLISH_CONFIRMED_BY_TWO_CHUNKS,
        decision=ACCEPT,
        predictions_count=predictions,
        chunk_predictions=chunk_predictions,
        **common,
    )
