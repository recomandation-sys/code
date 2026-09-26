"""Deterministic, verbatim-grounded experience and seniority extraction."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from enum import Enum

class ExperienceBracket(str, Enum):
    ZERO_YEARS = "0_YEARS"
    ONE_TO_TWO_YEARS = "1_2_YEARS"
    THREE_TO_FIVE_YEARS = "3_5_YEARS"
    FIVE_TO_SEVEN_YEARS = "5_7_YEARS"
    EIGHT_PLUS_YEARS = "8_PLUS_YEARS"
    UNKNOWN = "UNKNOWN"


class SeniorityLevel(str, Enum):
    INTERN_ENTRY = "INTERN_ENTRY"
    JUNIOR = "JUNIOR"
    MID = "MID"
    SENIOR = "SENIOR"
    LEAD_PRINCIPAL = "LEAD_PRINCIPAL"
    UNKNOWN = "UNKNOWN"


class Seniority(Enum):
    """Legacy vocabulary retained for existing imports."""

    INTERN = "INTERN"
    JUNIOR = "JUNIOR"
    MID_LEVEL = "MID_LEVEL"
    SENIOR = "SENIOR"
    LEAD = "LEAD"
    MANAGER = "MANAGER"
    DIRECTOR = "DIRECTOR"
    EXECUTIVE = "EXECUTIVE"
    UNSPECIFIED = "UNSPECIFIED"


@dataclass(frozen=True)
class ExperienceExtractionResult:
    min_experience_bracket: ExperienceBracket
    min_experience_months: float | None
    evidence_text: str | None
    evidence_start: int | None
    evidence_end: int | None
    comparator: str
    rule_tier: str
    seniority_level: SeniorityLevel = SeniorityLevel.UNKNOWN
    evidence_source: str = "UNKNOWN"
    warnings: list[str] | None = None

    @property
    def evidence(self) -> str | None:
        return self.evidence_text

    @property
    def _seniority(self) -> Seniority:
        return {
            SeniorityLevel.INTERN_ENTRY: Seniority.INTERN,
            SeniorityLevel.JUNIOR: Seniority.JUNIOR,
            SeniorityLevel.MID: Seniority.MID_LEVEL,
            SeniorityLevel.SENIOR: Seniority.SENIOR,
            SeniorityLevel.LEAD_PRINCIPAL: Seniority.LEAD,
        }.get(self.seniority_level, Seniority.UNSPECIFIED)

    def to_dict(self) -> dict[str, object]:
        return {
            "seniorities": [self._seniority.value] if self._seniority is not Seniority.UNSPECIFIED else [],
            "minimum_experience_months": self.min_experience_months,
            "min_experience_bracket": self.min_experience_bracket.value,
            "evidence_text": self.evidence_text,
            "evidence_start": self.evidence_start,
            "evidence_end": self.evidence_end,
            "comparator": self.comparator,
            "rule_tier": self.rule_tier,
            "seniority": self.seniority_level.value,
            "evidence_source": self.evidence_source,
            "evidence": self.evidence_text,
            "warnings": list(self.warnings or []),
        }


SeniorityExperienceResult = ExperienceExtractionResult


@dataclass(frozen=True)
class SeniorityExtractionResult:
    seniority_level: SeniorityLevel
    evidence_text: str | None
    evidence_source: str
    evidence_start: int | None = None
    evidence_end: int | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "seniority": self.seniority_level.value,
            "evidence_text": self.evidence_text,
            "evidence_source": self.evidence_source,
            "evidence_start": self.evidence_start,
            "evidence_end": self.evidence_end,
        }


_WORDS = {
    "zero": 0.0, "one": 1.0, "two": 2.0, "three": 3.0,
    "four": 4.0, "five": 5.0, "six": 6.0, "seven": 7.0,
    "eight": 8.0, "nine": 9.0, "ten": 10.0, "eleven": 11.0,
    "twelve": 12.0,
}
_NUM = r"(?:\d+(?:\.\d+)?|" + "|".join(_WORDS) + r")"
_UNIT = r"(?:years?|yrs?|months?|mos?|mo)"
_TENURE = re.compile(
    rf"(?P<full>\b(?P<qual>at\s+least|minimum(?:\s+of)?|more\s+than|over|no\s+fewer\s+than|approximately)?\s*"
    rf"(?P<low>{_NUM})(?:\s*(?P<sep>-|–|—|to|and)\s*(?P<high>{_NUM}))?\s*(?P<plus>\+|or\s+more)?\s*(?P<unit>{_UNIT})\b)",
    re.I,
)
_ZERO = re.compile(
    r"\b(?:no|without|zero)\s+(?:prior\s+|previous\s+|commercial\s+|professional\s+)?experience\s+(?:is\s+)?(?:required|necessary|needed)\b"
    r"|\b(?:entry[\s-]?level|fresh\s+graduates?|graduates?)\b[^.;\n]{0,50}\b(?:no|without)\s+(?:prior\s+)?experience\b",
    re.I,
)
_WEAK = re.compile(
    r"\b(?:prior|previous|professional|relevant|commercial|industry|hands[- ]on|proven)\s+experience\s+(?:is\s+)?(?:required|necessary|essential|mandatory|preferred|desired)\b"
    r"|\b(?:experience|background)\s+(?:is\s+)?(?:required|necessary|essential|mandatory|preferred|desired)\b"
    r"|\b(?:must\s+have|demonstrated|proven)\s+(?:hands[- ]on\s+)?experience(?:\s+with\s+[A-Za-z0-9+#./ -]+)?\b"
    r"|\bminimum\s+experience\s+in\s+[a-z][a-z /&-]{2,80}\b",
    re.I,
)
_BAD_CONTEXT = re.compile(
    r"\b(?:after|within|during|probation|vesting|benefit|tenure|in\s+business|founded|established|company\s+has|team\s+has|combined\s+experience|market\s+for|project\s+lasts?|contract\s+lasts?)\b",
    re.I,
)
_PREFERRED = re.compile(r"\b(?:preferred|preferably|desired|nice\s+to\s+have|a\s+plus|bonus|ideally|advantage|beneficial)\b", re.I)
_CANDIDATE_CONTEXT = re.compile(
    r"\b(?:experience|working\s+with|hands[- ]on|professional|relevant|commercial|industry|candidate|you|role|position|development|engineering|administration|support)\b",
    re.I,
)


def to_bracket(months: int | float | None, comparator: str = "EQ") -> str:
    """Map months onto the locked experience brackets.

    Cutoffs: <12 0_YEARS, <36 1_2_YEARS, <60 3_5_YEARS, <96 5_7_YEARS, else 8_PLUS_YEARS.
    comparator is kept because callers pass GT, GTE, and RANGE. Those cases use the
    same cutoffs. The recorded check is to_bracket(60, "GT") == 5_7_YEARS.
    """
    del comparator
    if months is None:
        return "UNKNOWN"
    value = float(months)
    if value < 12:
        return "0_YEARS"
    if value < 36:
        return "1_2_YEARS"
    if value < 60:
        return "3_5_YEARS"
    if value < 96:
        return "5_7_YEARS"
    return "8_PLUS_YEARS"


def months_to_bracket(months: int | float | None, comparator: str = "EQ") -> ExperienceBracket:
    return ExperienceBracket(to_bracket(months, comparator))


def _number(value: str) -> float:
    value = value.casefold()
    return float(value) if re.fullmatch(r"\d+(?:\.\d+)?", value) else _WORDS[value]


def _empty() -> ExperienceExtractionResult:
    return ExperienceExtractionResult(ExperienceBracket.UNKNOWN, None, None, None, None, "NONE", "WEAK", warnings=[])


def _is_non_candidate_duration(description: str, match: re.Match[str]) -> bool:
    """Reject only durations whose *local* context is clearly non-job-related.

    The previous implementation searched the complete paragraph.  A company
    biography mentioning ``founded`` or ``within`` could therefore suppress a
    valid requirement later in the same paragraph.  Keep the guard local to
    the candidate so unrelated boilerplate cannot veto it.
    """
    before = description[max(0, match.start() - 120):match.start()]
    local_patterns = (
        r"\b(?:project|contract|probation|vesting|notice|benefit|benefits)\s+"
        r"(?:period|duration|lasts?|of)?\s*(?:about|approximately|around|over|more\s+than)?\s*$",
        r"\b(?:company|team|organization|organisation)\s+(?:has|have|with)\s*"
        r"(?:about|approximately|around|over|more\s+than)?\s*$",
        r"\b(?:founded|established)\s*(?:in\s*)?$",
        r"\b(?:within|during|after)\s+(?:the\s+)?"
        r"(?:next|first|initial|probation|training|onboarding)?\s*$",
    )
    return any(re.search(pattern, before, re.I) for pattern in local_patterns)


def _title_seniority(title: str) -> SeniorityExtractionResult:
    """Resolve title-only signals without calling the full extractor."""
    title_rules = (
        (SeniorityLevel.INTERN_ENTRY, re.compile(r"\b(?:intern|internship|trainee|apprentice|stage(?:\s+pfe)?|pfe)\b", re.I)),
        (SeniorityLevel.JUNIOR, re.compile(r"\b(?:junior|jr\.?)\b|\bassociate(?=\s+(?:cloud|software|data|backend|frontend|qa|support|network|security|systems?)?\s*(?:engineer|developer|analyst|tester|administrator|architect))", re.I)),
        (SeniorityLevel.SENIOR, re.compile(r"\b(?:senior|sr\.?|confirm[eé])\b", re.I)),
        (SeniorityLevel.LEAD_PRINCIPAL, re.compile(r"\b(?:lead|tech\s+lead|staff|principal|architect|director|head\s+of)\b", re.I)),
    )
    for level, pattern in title_rules:
        hit = pattern.search(title or "")
        if hit and not (level is SeniorityLevel.INTERN_ENTRY and re.search(r"\b(?:manager|director|head|vp|chief)\b", title, re.I)):
            return SeniorityExtractionResult(level, hit.group(0), "TITLE_EXPLICIT", hit.start(), hit.end())
    return SeniorityExtractionResult(SeniorityLevel.UNKNOWN, None, "UNKNOWN", None, None)


def _numeric_candidates(description: str) -> list[ExperienceExtractionResult]:
    found: list[tuple[int, int, ExperienceExtractionResult]] = []
    for match in _TENURE.finditer(description):
        line_start = description.rfind("\n", 0, match.start()) + 1
        ends = [x for x in (description.find("\n", match.end()), description.find(".", match.end()), description.find(";", match.end())) if x >= 0]
        clause = description[line_start:min(ends, default=len(description))]
        nearby = description[max(0, match.start() - 30):min(len(description), match.end() + 90)]
        if _is_non_candidate_duration(description, match):
            continue
        low = _number(match.group("low"))
        high = _number(match.group("high")) if match.group("high") else None
        factor = 12.0 if match.group("unit").casefold().startswith(("year", "yr")) else 1.0
        months = low * factor
        qualifier = match.group("qual") or ""
        if high is not None:
            comparator = "RANGE"
        elif match.group("plus") or re.search(r"\b(?:at\s+least|minimum|no\s+fewer\s+than)\b", qualifier, re.I):
            comparator = "GTE"
        elif re.search(r"\b(?:over|more\s+than)\b", qualifier, re.I):
            comparator = "GT"
        elif re.search(r"\b(?:required|mandatory|essential)\b", clause, re.I):
            comparator = "GTE"
        else:
            comparator = "EQ"
        required = bool(re.search(r"\b(?:required|minimum|at\s+least|must|mandatory|essential)\b", clause, re.I))
        score = 0
        if required:
            score += 4
        if re.search(r"\b(?:professional|relevant|commercial|work|industry)\s+experience\b", clause, re.I):
            score += 3
        elif re.search(r"\b(?:years?|months?)\s+of\s+experience\b", clause, re.I):
            score += 2
        if re.search(r"\b(?:role|position|candidate|you|successful)\b", clause, re.I):
            score += 1
        if _PREFERRED.search(clause) and not required:
            score += 2
        if _CANDIDATE_CONTEXT.search(nearby):
            score += 2
        if score == 0:
            continue
        full_start, full_end = match.start("full"), match.end("full")
        while full_start < full_end and description[full_start].isspace():
            full_start += 1
        while full_end > full_start and description[full_end - 1].isspace():
            full_end -= 1
        found.append((int(required), score, ExperienceExtractionResult(
            months_to_bracket(months, comparator), months, description[full_start:full_end],
            full_start, full_end, comparator, "EXPLICIT"
        )))
    # Requirement strength wins over numeric magnitude.  Once candidates are
    # equally explicit, retain the strictest lower bound as the tie-breaker.
    found.sort(key=lambda item: (-item[0], -item[1], -float(item[2].min_experience_months or 0), item[2].evidence_start or 0))
    return [result for _, _, result in found]


def extract_seniority(title: str | None, description: str | None = None, contract_type: str | None = None) -> SeniorityExtractionResult:
    title = title or ""
    description = description or ""
    title_result = _title_seniority(title)
    if title_result.seniority_level is not SeniorityLevel.UNKNOWN:
        return title_result
    experience = SeniorityExperienceExtractor().extract(title, description, contract_type)
    mapping = {
        ExperienceBracket.ZERO_YEARS: SeniorityLevel.INTERN_ENTRY,
        ExperienceBracket.ONE_TO_TWO_YEARS: SeniorityLevel.JUNIOR,
        ExperienceBracket.THREE_TO_FIVE_YEARS: SeniorityLevel.MID,
        ExperienceBracket.FIVE_TO_SEVEN_YEARS: SeniorityLevel.SENIOR,
        ExperienceBracket.EIGHT_PLUS_YEARS: SeniorityLevel.LEAD_PRINCIPAL,
    }
    level = mapping.get(experience.min_experience_bracket, SeniorityLevel.UNKNOWN)
    source = "DESCRIPTION_TENURE" if level is not SeniorityLevel.UNKNOWN else "UNKNOWN"
    return SeniorityExtractionResult(level, experience.evidence_text, source, experience.evidence_start, experience.evidence_end)


class SeniorityExperienceExtractor:
    def extract(self, title: str | None = None, description: str | None = None, contract_type: str | None = None) -> ExperienceExtractionResult:
        title = title or ""
        description = description or ""
        contract = (contract_type or "").upper()
        zero = _ZERO.search(description)
        if zero:
            title_level = _title_seniority(title).seniority_level
            level = title_level if title_level is not SeniorityLevel.UNKNOWN else SeniorityLevel.INTERN_ENTRY
            return ExperienceExtractionResult(ExperienceBracket.ZERO_YEARS, 0.0, zero.group(0), zero.start(), zero.end(), "EQ", "EXPLICIT", level, "DESCRIPTION", [])
        candidates = _numeric_candidates(description)
        if candidates:
            result = candidates[0]
            if len(candidates) > 1:
                result = replace(result, warnings=["MULTIPLE_EXPERIENCE_REQUIREMENTS"])
            title_seniority = _title_seniority(title).seniority_level if title else SeniorityLevel.UNKNOWN
            seniority = title_seniority if title_seniority is not SeniorityLevel.UNKNOWN else {
                ExperienceBracket.ZERO_YEARS: SeniorityLevel.INTERN_ENTRY,
                ExperienceBracket.ONE_TO_TWO_YEARS: SeniorityLevel.JUNIOR,
                ExperienceBracket.THREE_TO_FIVE_YEARS: SeniorityLevel.MID,
                ExperienceBracket.FIVE_TO_SEVEN_YEARS: SeniorityLevel.SENIOR,
                ExperienceBracket.EIGHT_PLUS_YEARS: SeniorityLevel.LEAD_PRINCIPAL,
            }.get(result.min_experience_bracket, SeniorityLevel.UNKNOWN)
            return replace(result, seniority_level=seniority, evidence_source="DESCRIPTION")
        title_hit = re.search(r"\b(?:intern|internship|trainee|apprentice|stage(?:\s+pfe)?|pfe)\b", title, re.I)
        description_hit = re.search(r"\b(?:intern|internship|trainee|apprentice)\b", description, re.I)
        if contract == "INTERNSHIP" or title_hit or description_hit:
            hit = title_hit or description_hit
            if hit:
                source = "TITLE" if title_hit is not None else "DESCRIPTION"
                return ExperienceExtractionResult(ExperienceBracket.ZERO_YEARS, 0.0, hit.group(0), hit.start(), hit.end(), "EQ", "EXPLICIT", SeniorityLevel.INTERN_ENTRY, source, [])
            return ExperienceExtractionResult(ExperienceBracket.ZERO_YEARS, 0.0, None, None, None, "EQ", "EXPLICIT", SeniorityLevel.INTERN_ENTRY, "CONTRACT", [])
        title_seniority = _title_seniority(title).seniority_level if title else SeniorityLevel.UNKNOWN
        if title_seniority is not SeniorityLevel.UNKNOWN:
            return ExperienceExtractionResult(ExperienceBracket.UNKNOWN, None, None, None, None, "NONE", "WEAK", title_seniority, "TITLE_EXPLICIT", [])
        # Preserve the documented weak assumption, but only after explicit
        # contract/intern and seniority signals have been checked.
        weak = _WEAK.search(description)
        if weak:
            return ExperienceExtractionResult(ExperienceBracket.ONE_TO_TWO_YEARS, None, weak.group(0), weak.start(), weak.end(), "NONE", "WEAK", SeniorityLevel.JUNIOR, "DESCRIPTION", ["UNQUANTIFIED_EXPERIENCE_ASSUMED_1_2_YEARS"])
        return _empty()


def extract_minimum_experience(title: str | None = None, description: str | None = None, contract_type: str | None = None) -> dict[str, object]:
    return SeniorityExperienceExtractor().extract(title, description, contract_type).to_dict()


def extract_seniority_and_minimum_experience(title: str | None = None, description: str | None = None, contract_type: str | None = None) -> dict[str, object]:
    result = SeniorityExperienceExtractor().extract(title, description, contract_type)
    payload = result.to_dict()
    seniority = extract_seniority(title, description, contract_type)
    # Keep ``evidence_text`` as the minimum-experience evidence for legacy
    # callers; seniority evidence is exposed under its own namespaced keys.
    payload["seniority"] = seniority.seniority_level.value
    payload["seniority_evidence_text"] = seniority.evidence_text
    payload["seniority_evidence_source"] = seniority.evidence_source
    return payload


def extract_seniorities_and_minimum_experience(title: str | None = None, description: str | None = None, contract_type: str | None = None) -> dict[str, object]:
    return extract_seniority_and_minimum_experience(title, description, contract_type)


if __name__ == "__main__":
    assert to_bracket(0) == "0_YEARS"
    assert to_bracket(11) == "0_YEARS"
    assert to_bracket(12) == "1_2_YEARS"
    assert to_bracket(35) == "1_2_YEARS"
    assert to_bracket(36) == "3_5_YEARS"
    assert to_bracket(59) == "3_5_YEARS"
    assert to_bracket(60) == "5_7_YEARS"
    assert to_bracket(95) == "5_7_YEARS"
    assert to_bracket(96) == "8_PLUS_YEARS"
    assert to_bracket(60, "GT") == "5_7_YEARS"
    print("to_bracket ok")
