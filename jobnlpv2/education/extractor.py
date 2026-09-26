"""Deterministic European education-level extraction."""
from __future__ import annotations

import re
from dataclasses import dataclass

from .clause_parser import Clause, parse_clauses
from .config import COUNTRY
from .models import EducationCandidate, EducationLevel, EducationResult, EvidenceSpan, Modality
from .patterns import (
    BAC_PATTERN, BAC_RANGE_PATTERN, BARE_BAC_PATTERN, CANDIDATE_PATTERNS,
    ENGINEERING_DEGREE_PATTERN, EQUIVALENT_EXPERIENCE_PATTERN,
    EXCLUSION_PATTERNS, EXPLICIT_NO_REQUIREMENT_PATTERN, FIELD_DEGREE_PATTERN,
    EXPERIENCE_IN_LIEU_PATTERN, MODALITY_PATTERNS, NO_REQUIREMENT_PATTERNS, PARENTHETICAL_BAC_PATTERN,
    SOFT_NO_REQUIREMENT_PATTERN,
)

_ENGINEERING_COUNTRIES = {"FR", "MA", "BE", "TN", "DZ", "LU", "CH"}
_COUNTRIES = {"maroc": "MA", "morocco": "MA", "france": "FR", "belgium": "BE", "belgique": "BE", "tunisia": "TN", "tunisie": "TN", "algeria": "DZ", "algerie": "DZ", "luxembourg": "LU", "switzerland": "CH", "suisse": "CH"}


@dataclass(frozen=True)
class _Hit:
    candidate: EducationCandidate
    modality: Modality
    clause: Clause


class EducationExtractor:
    def __init__(self, country: str | None = None) -> None:
        raw = (country or COUNTRY).strip().casefold()
        self.country = _COUNTRIES.get(raw, raw.upper())

    def extract(self, title: str, description: str) -> EducationResult:
        text = f"{title or ''}\n{description or ''}".translate(str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'}))
        clauses = parse_clauses(text)
        hits = [
            hit for hit in self._candidates(text, clauses, title)
            if hit.modality not in {Modality.NEGATED, Modality.BACKGROUND_ONLY}
        ]

        # Explicit no-requirement language wins over illustrative/background
        # credentials, but never masks a real required degree elsewhere.
        no_requirement = self._no_requirement_signal(text, clauses)
        positive = [hit for hit in hits if hit.modality not in {Modality.UNKNOWN} or self._is_credential_hit(hit)]
        if no_requirement and not positive:
            match, hard = no_requirement
            if hard:
                # A negated *specific* credential (for example "a
                # four-year degree is not required") is explicit no-
                # requirement status, but does not assert that every form of
                # education is unnecessary.
                value = "UNKNOWN"
                return EducationResult(
                    value=value,
                    status="EXPLICIT_NO_REQUIREMENT",
                    confidence=0.98,
                    evidence=[EvidenceSpan(match.group(), match.start(), match.end())],
                    method="rule+dictionary",
                    missing_reason=None,
                )
            # "No specific degree is mandated" deliberately means that the
            # posting did not state a level; it is not the same as an explicit
            # no-formal-education policy.
            return EducationResult(
                value=None,
                status="NOT_STATED",
                confidence=0.98,
                method="rule+dictionary",
                missing_reason="no specific education level required",
            )

        if not hits:
            if no_requirement and no_requirement[1]:
                match, _ = no_requirement
                return EducationResult(
                    value="UNKNOWN",
                    status="EXPLICIT_NO_REQUIREMENT",
                    confidence=0.98,
                    evidence=[EvidenceSpan(match.group(), match.start(), match.end())],
                    method="rule+dictionary",
                )
            return EducationResult(
                status="NOT_STATED",
                confidence=1.0,
                method="rule+dictionary",
                experience_in_place_of_education=self._experience_in_lieu(text, clauses),
                missing_reason="no education mention found",
            )

        # Keep all non-negated canonical tiers for candidate display.
        levels = {hit.candidate.level for hit in hits}
        if re.search(r"\bbac\s*\+\s*[567]\b", text, re.I) and re.search(r"\bbachelor(?:'s|s)?\b", text, re.I):
            levels.add(EducationLevel.BACHELOR)
        order = {
            EducationLevel.UNKNOWN: 0,
            EducationLevel.ASSOCIATE: 1,
            EducationLevel.BACHELOR: 2,
            EducationLevel.MASTER_OR_HIGHER: 3,
        }

        required = [hit for hit in hits if hit.modality in {Modality.REQUIRED, Modality.UNKNOWN}]
        preferred = [hit for hit in hits if hit.modality is Modality.PREFERRED]
        alternatives = [hit for hit in hits if hit.modality is Modality.ACCEPTED_ALTERNATIVE]

        # A clause with an explicit OR is a minimum-level choice; an AND (or
        # separate required clauses) requires the strongest level present.
        primary_hits = required or alternatives
        value_level = self._select_primary(primary_hits)
        value = value_level.name if value_level else None
        preferred_level = None
        if preferred:
            preferred_level = max((hit.candidate.level for hit in preferred), key=lambda level: order[level]).name

        accepted_levels = self._accepted_levels(hits, value_level)
        # "without a PhD ... Master's ... may be considered" is a
        # conditional exception, not an accepted education alternative for
        # the minimum requirement.  Keep the primary PhD decision stable.
        if required and re.search(
            r"\bwithout\s+(?:a\s+)?(?:ph\.?d|doctorate|master|bachelor)\b.*?"
            r"(?:master|ph\.?d|doctorate|bachelor)[^.;—–]*\b(?:may|will)\s+also\s+be\s+considered\b",
            text,
            re.I | re.S,
        ):
            accepted_levels = list(dict.fromkeys(hit.candidate.level for hit in required))
        status = "EXPLICIT_REQUIRED" if required or alternatives else ("EXPLICIT_PREFERRED" if preferred else "NOT_STATED")
        if status == "EXPLICIT_PREFERRED":
            value = None

        relevant = required or alternatives or preferred or hits
        confidence = 0.60 if any(hit.candidate.source_phrase == "generic-field-degree" for hit in relevant) else (0.80 if alternatives or preferred else 0.95)
        flags = ["DEGREE_LEVEL_UNSPECIFIED"] if any(hit.candidate.source_phrase == "generic-field-degree" for hit in hits) else []
        lieu = self._experience_in_lieu(text, clauses)
        evidence = self._dedupe_evidence([hit.candidate.span for hit in relevant])
        return EducationResult(
            required_education_levels=sorted(levels, key=lambda level: order[level]),
            value=value,
            status=status,
            accepted_alternatives=[level.name for level in accepted_levels],
            preferred_level=preferred_level,
            experience_in_place_of_education=lieu,
            confidence=confidence,
            evidence=evidence,
            raw_credential_text=evidence[0].text if evidence else None,
            method="rule+dictionary",
            inferred=False,
            missing_reason=None,
            flags=flags,
        )

    @staticmethod
    def _generic_degree(text: str) -> bool:
        # Kept as a compatibility helper; generic fields are now represented
        # by one low-confidence FIELD_DEGREE_PATTERN hit, never three levels.
        return bool(FIELD_DEGREE_PATTERN.search(text))

    def _no_requirement(self, text: str, clauses: list[Clause]) -> bool:
        return self._no_requirement_signal(text, clauses) is not None

    @staticmethod
    def _is_credential_hit(hit: _Hit) -> bool:
        return hit.candidate.level in set(EducationLevel)

    def _no_requirement_signal(self, text: str, clauses: list[Clause]) -> tuple[re.Match[str], bool] | None:
        # Hard phrases are explicit policy statements.  Ignore matches in a
        # background clause, but allow a negated clause because that is exactly
        # the signal we need to return NO_FORMAL_REQUIREMENT.
        hard_patterns = [*NO_REQUIREMENT_PATTERNS, EXPLICIT_NO_REQUIREMENT_PATTERN]
        for pattern in hard_patterns:
            match = pattern.search(text)
            if match:
                clause = self._clause_at(clauses, match.start())
                if clause.modality is not Modality.BACKGROUND_ONLY:
                    return match, True
        soft = SOFT_NO_REQUIREMENT_PATTERN.search(text)
        if soft:
            clause = self._clause_at(clauses, soft.start())
            if clause.modality is not Modality.BACKGROUND_ONLY:
                return soft, False
        return None

    @staticmethod
    def _select_primary(hits: list[_Hit]) -> EducationLevel | None:
        if not hits:
            return None
        order = {
            EducationLevel.UNKNOWN: 0,
            EducationLevel.ASSOCIATE: 1,
            EducationLevel.BACHELOR: 2,
            EducationLevel.MASTER_OR_HIGHER: 3,
        }
        by_clause: dict[int, list[_Hit]] = {}
        for hit in hits:
            by_clause.setdefault(hit.clause.index, []).append(hit)
        selected: list[EducationLevel] = []
        for group in by_clause.values():
            # A field phrase ("degree in computer science") is not a second
            # level when the same clause already names Bac+5 or an engineering
            # school.  Keeping it made "engineering school or Bac+5 degree in
            # Computer Science" collapse to BACHELOR.
            explicit = [hit for hit in group if hit.candidate.source_phrase != "generic-field-degree"]
            group = explicit or group
            distinct = {hit.candidate.level for hit in group}
            clause_text = group[0].clause.text.casefold()
            ordered = sorted(group, key=lambda hit: hit.candidate.span.start)
            connectors = [
                clause_text[max(0, left.candidate.span.end - group[0].clause.start):
                            max(0, right.candidate.span.start - group[0].clause.start)]
                for left, right in zip(ordered, ordered[1:])
            ]
            has_and = any(re.search(r"\band\b", connector, re.I) for connector in connectors)
            has_or = any(re.search(r"\bor\b", connector, re.I) for connector in connectors)
            if len(distinct) > 1 and has_or and not has_and:
                selected.append(min(distinct, key=lambda level: order[level]))
            else:
                selected.append(max(distinct, key=lambda level: order[level]))
        return max(selected, key=lambda level: order[level]) if selected else None

    @staticmethod
    def _accepted_levels(hits: list[_Hit], value_level: EducationLevel | None) -> list[EducationLevel]:
        """Return distinct education alternatives while preserving OR groups.

        An ``or equivalent experience`` clause is an alternative path for the
        *degree*, not another education level, so its degree candidate is not
        emitted here.  Explicit education OR groups retain their levels; a
        same-level aliases collapse to an empty set except when the posting
        explicitly presents HND as a separate accepted branch (the legacy
        public contract retains that normalized candidate).
        """
        order = {
            EducationLevel.UNKNOWN: 0,
            EducationLevel.ASSOCIATE: 1,
            EducationLevel.BACHELOR: 2,
            EducationLevel.MASTER_OR_HIGHER: 3,
        }
        levels: list[EducationLevel] = []
        required = [hit for hit in hits if hit.modality in {Modality.REQUIRED, Modality.UNKNOWN}]
        alternatives = [hit for hit in hits if hit.modality is Modality.ACCEPTED_ALTERNATIVE]

        for clause_index in {hit.clause.index for hit in required}:
            group = sorted(
                [hit for hit in required if hit.clause.index == clause_index],
                key=lambda hit: hit.candidate.span.start,
            )
            distinct_levels = {hit.candidate.level for hit in group}
            if len(distinct_levels) <= 1:
                # HND is a separately named post-secondary credential even
                # though it normalizes to the same ordinal as Associate.  Keep
                # that explicit branch visible; GED/high-school and MBA/
                # Master's are aliases and remain deduplicated.
                if (
                    len(distinct_levels) == 1
                    and EducationLevel.ASSOCIATE in distinct_levels
                    and any(hit.candidate.raw_text.casefold() == "hnd" for hit in group)
                ):
                    levels.extend(distinct_levels)
                continue
            connectors = [
                group[0].clause.text[
                    left.candidate.span.end - group[0].clause.start :
                    right.candidate.span.start - group[0].clause.start
                ]
                for left, right in zip(group, group[1:])
            ]
            if any(re.search(r"\bor\b", connector, re.I) for connector in connectors) and not any(
                re.search(r"\band\b", connector, re.I) for connector in connectors
            ):
                levels.extend(hit.candidate.level for hit in group)

        if alternatives:
            for hit in alternatives:
                if EXPERIENCE_IN_LIEU_PATTERN.search(hit.clause.text) or EQUIVALENT_EXPERIENCE_PATTERN.search(hit.clause.text):
                    continue
                levels.append(hit.candidate.level)
            # A normal explicit alternative ("Master required; PhD welcome")
            # keeps the required level visible in the candidate set.
            if not any(re.search(r"without\s+(?:a\s+)?(?:ph\.?d|doctorate|master|bachelor)", hit.clause.text, re.I) for hit in alternatives):
                levels.extend(hit.candidate.level for hit in required)

        return sorted(set(levels), key=lambda level: order[level])

    @staticmethod
    def _experience_in_lieu(text: str, clauses: list[Clause]) -> bool:
        for pattern in (EXPERIENCE_IN_LIEU_PATTERN, EQUIVALENT_EXPERIENCE_PATTERN):
            for match in pattern.finditer(text):
                clause = EducationExtractor._clause_at(clauses, match.start())
                if clause.modality not in {Modality.BACKGROUND_ONLY, Modality.NEGATED}:
                    return True
        return False

    @staticmethod
    def _dedupe_evidence(spans: list[EvidenceSpan]) -> list[EvidenceSpan]:
        seen: set[tuple[int, int, str]] = set()
        result: list[EvidenceSpan] = []
        for span in sorted(spans, key=lambda item: (item.start, item.end)):
            key = (span.start, span.end, span.text)
            if key not in seen:
                seen.add(key)
                result.append(span)
        return result

    def _candidates(self, text: str, clauses: list[Clause], title: str) -> list[_Hit]:
        found: list[_Hit] = []
        occupied: list[tuple[int, int]] = []

        def add(level: EducationLevel, match: re.Match[str], *, allow_overlap: bool = False) -> None:
            if not allow_overlap and any(match.start() < end and match.end() > start for start, end in occupied):
                return
            raw = match.group()
            source_phrase = raw.casefold()
            if match.re is FIELD_DEGREE_PATTERN:
                # Keep evidence bounded to the credential phrase rather than
                # swallowing the trailing modality/requirements text.
                trimmed = re.split(
                    r"\s+(?:is\s+)?(?:required|preferred|essential|mandatory|needed|necessary)\b",
                    raw,
                    maxsplit=1,
                    flags=re.I,
                )[0].rstrip(" ,;:")
                if trimmed:
                    raw = trimmed
                    source_phrase = "generic-field-degree"
            parenthetical = PARENTHETICAL_BAC_PATTERN.search(text, match.end(), min(len(text), match.end() + 60))
            if parenthetical and not allow_overlap and level is not EducationLevel.MASTER_OR_HIGHER:
                if any(candidate.candidate.level is EducationLevel.MASTER_OR_HIGHER
                       for candidate in found if candidate.candidate.span and candidate.candidate.span.end <= match.start() + 2):
                    return
                if max(self._bac_levels(int(parenthetical["n"])), key=lambda item: item.rank).rank > level.rank:
                    return
            if not self._valid(raw, text, match.start(), match.end()) or self._template_conflict(text, match.start(), title):
                return
            clause = self._clause_at(clauses, match.start())
            before_match = clause.text[:max(0, match.start() - clause.start)]
            if re.search(r"\bwithout\s+(?:a\s+)?(?:ph\.?d|doctorate|master'?s?|bachelor'?s?)\s*$", before_match, re.I):
                return
            if re.search(r"\b(?:only|just)\s+(?:a\s+)?(?:ph\.?d|doctorate|master'?s?|bachelor'?s?)\b.*\b(?:will|would)\s+not\s+be\s+considered\b", clause.text, re.I):
                return
            if any(pattern.search(clause.text) for pattern in EXCLUSION_PATTERNS):
                return
            evidence_end = match.start() + len(raw)
            modality = self._candidate_modality(clause, match.start(), evidence_end)
            found.append(_Hit(EducationCandidate(raw, level, EvidenceSpan(raw, match.start(), evidence_end), source_phrase, clause.index), modality, clause))
            if not allow_overlap:
                occupied.append((match.start(), match.end()))

        if self.country in _ENGINEERING_COUNTRIES:
            for match in ENGINEERING_DEGREE_PATTERN.finditer(text):
                if not self._engineering_is_field(text, match):
                    add(EducationLevel.MASTER_OR_HIGHER, match)
            for match in re.finditer(r"\bengineering\b(?=\s+or\s+(?:a\s+)?master)", text, re.I):
                    add(EducationLevel.MASTER_OR_HIGHER, match)
        for match in BAC_RANGE_PATTERN.finditer(text):
            for number in range(int(match["low"]), int(match["high"]) + 1):
                for level in self._bac_levels(number):
                    add(level, match, allow_overlap=True)
            occupied.append((match.start(), match.end()))
        for match in BAC_PATTERN.finditer(text):
            if re.search(r"(?:engineering degree|engineer's degree|dipl[oô]me d['’]ing[eé]nieur|master(?:'s)? degree)\s*\(", text[max(0, match.start() - 60):match.start() + 1], re.I):
                continue
            for level in self._bac_levels(int(match["n"])):
                add(level, match, allow_overlap=True)
            occupied.append((match.start(), match.end()))
        for match in BARE_BAC_PATTERN.finditer(text):
            add(EducationLevel.UNKNOWN, match)
        for level, pattern in CANDIDATE_PATTERNS.items():
            for match in pattern.finditer(text):
                add(level, match)
        for match in FIELD_DEGREE_PATTERN.finditer(text):
            add(EducationLevel.BACHELOR, match)
        for hit in list(found):
            end = hit.candidate.span.end if hit.candidate.span else 0
            if hit.candidate.level is EducationLevel.MASTER_OR_HIGHER:
                continue
            match = PARENTHETICAL_BAC_PATTERN.search(text, end, min(len(text), end + 60))
            if match and match.start() <= end + 25:
                for level in self._bac_levels(int(match["n"])):
                    span = EvidenceSpan(match.group(), match.start(), match.end())
                    found.append(_Hit(EducationCandidate(match.group(), level, span, match.group().casefold(), hit.clause.index), hit.modality, hit.clause))
        return found

    @staticmethod
    def _candidate_modality(clause: Clause, start: int, end: int) -> Modality:
        """Resolve mixed required/preferred cues at candidate level.

        A single posting bullet can contain ``required ... or ... preferred``.
        Clause-level classification alone would assign one modality to both
        credentials, so use the nearest local cue while preserving inherited
        section modality when no cue is present.
        """
        if clause.modality in {Modality.NEGATED, Modality.BACKGROUND_ONLY}:
            return clause.modality
        rel_start = max(0, start - clause.start)
        rel_end = max(rel_start, end - clause.start)
        text = clause.text
        cue_patterns = (
            (Modality.REQUIRED, MODALITY_PATTERNS["REQUIRED"]),
            (Modality.PREFERRED, MODALITY_PATTERNS["PREFERRED"]),
            (Modality.ACCEPTED_ALTERNATIVE, MODALITY_PATTERNS["ALTERNATIVE"]),
            (Modality.NEGATED, MODALITY_PATTERNS["NEGATION"]),
            (Modality.BACKGROUND_ONLY, MODALITY_PATTERNS["BACKGROUND"]),
        )
        candidates: list[tuple[int, Modality]] = []
        # Cues before a candidate can govern it (e.g. a section header), but a
        # cue from a different later branch should not.  Limit the search to a
        # compact local window and prefer cues after the credential.
        window_start = max(0, rel_start - 80)
        window_end = min(len(text), rel_end + 100)
        for modality, pattern in cue_patterns:
            for cue in pattern.finditer(text, window_start, window_end):
                distance = abs(cue.start() - rel_end)
                if cue.start() < rel_start:
                    distance += 12
                candidates.append((distance, modality))
        if candidates:
            return min(candidates, key=lambda item: item[0])[1]
        return clause.modality

    @staticmethod
    def _bac_levels(number: int) -> tuple[EducationLevel, ...]:
        if number <= 2:
            return (EducationLevel.ASSOCIATE,)
        if number <= 4:
            return (EducationLevel.BACHELOR,)
        if number <= 7:
            return (EducationLevel.MASTER_OR_HIGHER,)
        return (EducationLevel.MASTER_OR_HIGHER,)

    @staticmethod
    def _engineering_is_field(text: str, match: re.Match[str]) -> bool:
        before = text[max(0, match.start() - 35):match.start()].casefold()
        after = text[match.end():match.end() + 35].casefold()
        return bool(re.search(r",|\bor\b|\band\b", before) or re.search(r"\bor\s+(?:a\s+)?related(?:\s+field)?", after))

    @staticmethod
    def _valid(raw: str, text: str, start: int, end: int) -> bool:
        folded = raw.casefold().rstrip(".")
        window = text[max(0, start - 12): min(len(text), end + 35)].casefold()
        if folded in {"ba", "bs", "ms", "ma"} and "degree" not in window and " in " not in window:
            return False
        if folded.startswith("master") and not re.search(r"master(?:'s|s)?(?:\s+degree|\s+of\s+(?:science|arts|engineering|business)|\s+in\b|$)", raw, re.I):
            return False
        return True

    @staticmethod
    def _template_conflict(text: str, start: int, title: str) -> bool:
        clause_end = text.find(".", start)
        window = text[start:clause_end if clause_end >= 0 else len(text)].casefold()
        domains = re.search(r"\b(finance|accounting|marketing|sales|hr|human resources|legal|law|payroll|treasury)\b", window)
        # An explicit credential clause is stronger than a domain word.  The
        # previous title-only gate dropped valid requirements such as a
        # Bachelor's in Finance from a "Financial Analyst" posting.
        if re.search(r"\b(?:degree|diploma|bachelor|master|ph\.?d|doctorate|associate|hnd|bac\s*\+)\b", window, re.I):
            return False
        return bool(domains and not re.search(r"\b(finance|accounting|marketing|sales|hr|human resources|legal|law|payroll|treasury)\b", title, re.I))

    @staticmethod
    def _clause_at(clauses: list[Clause], offset: int) -> Clause:
        return next((clause for clause in clauses if clause.start <= offset < clause.end), Clause("", offset, offset, -1, Modality.UNKNOWN))
