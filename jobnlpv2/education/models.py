"""Public types for deterministic education extraction."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class EducationLevel(Enum):
    """Production four-tier education ontology.

    Legacy labels are normalized at ingestion and are intentionally not enum
    members, so they cannot leak into public extraction output.
    """

    UNKNOWN = ("UNKNOWN", 0)
    ASSOCIATE = ("ASSOCIATE", 5)
    BACHELOR = ("BACHELOR", 6)
    MASTER_OR_HIGHER = ("MASTER_OR_HIGHER", 7)

    @property
    def rank(self) -> int:
        return self.value[1]


@dataclass(frozen=True)
class EvidenceSpan:
    text: str
    start: int
    end: int


class Modality(str, Enum):
    REQUIRED = "REQUIRED"
    PREFERRED = "PREFERRED"
    ACCEPTED_ALTERNATIVE = "ACCEPTED_ALTERNATIVE"
    NEGATED = "NEGATED"
    BACKGROUND_ONLY = "BACKGROUND_ONLY"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class EducationCandidate:
    raw_text: str
    level: EducationLevel
    span: EvidenceSpan
    source_phrase: str
    clause_index: int


@dataclass(frozen=True)
class EducationResult:
    """Education extraction result.

    ``required_education_levels`` and the default ``to_dict`` representation
    are kept for compatibility with the original CLI and pipeline adapters.
    The richer fields are deliberately available on the same immutable result
    so callers that need auditability do not have to re-run extraction.
    """

    required_education_levels: list[EducationLevel] = field(default_factory=list)
    value: str | None = None
    status: str = "NOT_STATED"
    accepted_alternatives: list[str] = field(default_factory=list)
    preferred_level: str | None = None
    experience_in_place_of_education: bool = False
    confidence: float = 1.0
    evidence: list[EvidenceSpan] = field(default_factory=list)
    raw_credential_text: str | None = None
    method: str = "rule+dictionary"
    inferred: bool = False
    missing_reason: str | None = None
    flags: list[str] = field(default_factory=list)

    def to_dict(self, detailed: bool = False) -> dict[str, Any]:
        """Return the original public shape.

        ``detailed=True`` is intentionally opt-in so existing integrations
        that compare the one-field dictionary continue to work unchanged.
        """
        if detailed:
            return self.to_rich_dict()
        return {"required_education_levels": [level.name for level in self.required_education_levels]}

    def to_rich_dict(self) -> dict[str, Any]:
        """Return the auditable education result without changing ``to_dict``."""
        return {
            "value": self.value,
            "status": self.status,
            "confidence": self.confidence,
            "evidence": [
                {"text": span.text, "start": span.start, "end": span.end}
                for span in self.evidence
            ],
            "accepted_alternatives": list(self.accepted_alternatives),
            "experience_in_place_of_education": self.experience_in_place_of_education,
            "preferred_level": self.preferred_level,
            "raw_credential_text": self.raw_credential_text,
            "method": self.method,
            "inferred": self.inferred,
            "missing_reason": self.missing_reason,
            "flags": list(self.flags),
            "required_education_levels": [level.name for level in self.required_education_levels],
        }
