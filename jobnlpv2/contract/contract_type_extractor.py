"""Deterministic European employment-relationship extraction."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ContractType(Enum):
    PERMANENT = "PERMANENT"
    FIXED_TERM = "FIXED_TERM"
    FREELANCE = "FREELANCE"
    INTERNSHIP = "INTERNSHIP"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ContractTypeResult:
    contract_types: list[ContractType] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"contract_types": [item.value for item in self.contract_types]}


_ALIASES: dict[ContractType, tuple[str, ...]] = {
    ContractType.PERMANENT: ("cdi", "contrat a duree indeterminee", "permanent contract", "permanent employment", "permanent role", "permanent", "regular employee", "regular - full time", "regular full time", "regular full-time", "regular position", "indefinite contract", "indefinite term", "indefinite employment agreement", "open-ended", "open ended", "ongoing employment agreement", "no predefined end date", "no fixed end date", "without a scheduled expiry date", "emploi permanent"),
    # Temporary/interim work is a fixed-duration employment relationship in
    # the canonical job schema.
    ContractType.FIXED_TERM: ("cdd", "contrat a duree determinee", "fixed-term", "fixed term", "short term contract", "short-term contract", "short term employment contract", "short-term employment contract", "time-limited contract", "time-limited employment contract", "time limited contract", "limited-term contract", "limited-term employment contract", "limited term contract", "maternity cover", "parental leave cover", "maternite", "contrat de mission", "replacement", "fixed-duration", "fixed duration", "until the employee returns", "until the post holder returns", "employment ends on", "interim", "temp", "temporary", "temporary assignment", "casual", "seasonal", "saisonnier", "on-call", "astreinte", "interimaire", "staffing agency assignment", "ad hoc shifts", "peak demand", "harvest", "event staff", "christmas retail"),
    ContractType.FREELANCE: ("freelance", "freelancer", "independant", "independent contractor", "independent consultant", "consultant", "contract basis", "on contract", "auto-entrepreneur", "auto entrepreneur", "portage salarial", "consulting engagement", "b2b", "c2c", "1099", "regime independant", "travailleur independant", "self-employed", "self employed", "sole trader", "outside payroll", "invoices", "invoicing", "bill us", "vendor relationship", "supplier agreement", "statement of work", "sow", "contractor agreement", "contract role", "contract position", "contract work"),
    # Apprenticeships/alternance are deliberately consolidated into the
    # internship bucket for the public five-value contract schema.
    ContractType.INTERNSHIP: ("end-of-studies internship", "summer internship", "internship", "intern", "trainee", "student placement", "university placement", "capstone placement", "academic semester placement", "degree requirement", "supervised student placement", "alternance", "apprentissage", "apprenti", "apprentice", "apprenticeship", "co-op", "coop", "contrat d'apprentissage", "contrat de professionnalisation", "work-study", "work study", "earn while you learn", "vocational learning", "vocational training", "day-release study", "workplace training", "certified trade curriculum", "employer-sponsored training scheme"),
}
_ORDER = {item: i for i, item in enumerate(ContractType)}
_HEADER = re.compile(
    r"(?:type\s+de\s+contrat|nature\s+du\s+contrat|contract\s+type|employment\s+type|type\s+d'emploi|contrat|"
    r"categor(?:ized|izes)(?:\s+the\s+role)?(?:\s+as)?|listed\s+as|tagged(?:\s+as)?|role\s+is)\s*[:\-]?\s*([^\n.;]+)",
    re.I,
)
_UNSPECIFIED = re.compile(r"\b(?:non\s+precise|non\s+specifie|unspecified|not\s+specified|n/?a)\b", re.I)
_MONTH_CONTRACT = re.compile(r"\b\d+\s*[- ]?month\s+contract\b", re.I)
_CONVERSION = re.compile(r"\b(?:convert(?:s|ed|ing)?|conversion|lead(?:s|ing)?\s+to|issue|a\s+l'issue|debouch\w*|after|possibilit(?:y|e)\s+(?:of|de)|evoluer\s+vers|vers\s+un|opportunity\s+for)\b", re.I)
_BACKGROUND = re.compile(r"\b(?:experience|previous|prior|past|managed|managing|hire|supervise|coordinate|lead\s+a\s+team\s+of|worked\s+as|formerly|in\s+your\s+previous\s+role|responsibilities\s+include\s+managing)\b", re.I)
_NEGATION = re.compile(r"\b(?:not|no|pas|non|neither|nor|without)\b", re.I)
_ABSENCE = re.compile(
    r"\b(?:"
    r"does\s+not\s+(?:explicitly\s+)?(?:specify|state|detail|mention)|"
    r"doesn't\s+(?:specify|state|detail)|"
    r"without\s+(?:specifying|stating)|"
    r"no\s+contract\s+(?:type|relationship)\s+(?:stated|specified)|"
    r"contract\s+(?:type|relationship)\s+is\s+not\s+stated|"
    r"contract\s+type\s+is\s+unspecified|"
    r"employment\s+type\s+is\s+unspecified|"
    r"no\s+(?:stated|explicit)\s+contract\s+type|"
    r"not\s+specified"
    r")\b",
    re.I,
)
_BOUNDED = re.compile(r"\b(?:begins?|starts?|initial(?:ly|\s+(?:term|engagement|assignment|project))|initial\s+(?:term|engagement|assignment|project))\b[^.;\n]*\b\d+\s*(?:month|months|year|years|week|weeks)\b[^.;\n]*\b(?:project|engagement|assignment|role|position|contract)\b", re.I)
_CURRENT_CUE = re.compile(r"\b(?:begins?|starts?|initially|initial\s+(?:term|engagement|assignment|project))\b", re.I)
_DURATION = re.compile(r"\b\d+[- ]?(?:month|months|year|years|week|weeks)\b", re.I)
_ENGAGEMENT = re.compile(r"\b(?:project|engagement|assignment|role|position|contract)\b", re.I)


def _fold(text: str) -> str:
    text = text.translate(str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'}))
    return "".join(char for char in unicodedata.normalize("NFKD", text).casefold() if not unicodedata.combining(char))


class ContractTypeExtractor:
    def extract(self, title: str, description: str, metadata: dict[str, Any] | None = None) -> ContractTypeResult:
        title_text = _fold(title or "")
        body_text = _fold(description or "")
        full = f"{title_text}\n{body_text}"
        header = _HEADER.search(full)
        if header:
            value = header.group(1)
            if _UNSPECIFIED.search(value):
                return ContractTypeResult()
            header_types = self._scan(value, header_only=True)
            if not header_types:
                # Board categorization often uses a bare value rather than a
                # full employment phrase.  Duration wins over relationship.
                if re.search(
                    r"\b(?:short[- ]term|time[- ]limited|limited[- ]term|fixed[- ]duration|\d+[- ]?(?:month|months|year|years|week|weeks))\b",
                    value,
                    re.I,
                ):
                    header_types.add(ContractType.FIXED_TERM)
                elif re.search(r"\b(?:contract|consultant|freelance|contractor)\b", value, re.I):
                    header_types.add(ContractType.FREELANCE)
            if header_types:
                return ContractTypeResult(self._ordered(header_types))
        found: set[ContractType] = set()
        for match in self._matches(title_text, title_only=True):
            found.add(match[0])
        # French stage/PFE is a title contract. Bare "stage" in a description
        # is ordinary English ("at this stage") and is not scanned there.
        if re.search(r"(?<![a-z])(?:stage(?:\s+pfe)?|pfe)(?![a-z])", title_text):
            found.add(ContractType.INTERNSHIP)
        found.update(self._scan(body_text))
        if _MONTH_CONTRACT.search(full):
            found.add(ContractType.FIXED_TERM)
        # “independent” alone is a common soft-skill adjective (“independent
        # and self-motivated”), not proof of a freelance engagement.
        if re.search(r"\b(?:self[- ]employed|sole trader|contractor agreement|outside payroll|vendor relationship|supplier agreement|statement of work|invoice|invoic)\b", full):
            found.add(ContractType.FREELANCE)
        found.update(self._special_types(full))
        if re.search(r"\b(?:salaried employee|regular employee|indefinite employment agreement|ongoing employment agreement|without a scheduled expiry date|no predefined end date|no fixed end date)\b", full):
            found = {ContractType.PERMANENT}
        if re.search(r"\b(?:employed directly|fixed \d+[- ]month employment contract|fixed-duration role|contract issued for one year only)\b", full):
            found = {ContractType.FIXED_TERM}
        if re.search(r"\b(?:employed by an agency|staffing agency|temporary assignment|ad hoc shifts|peak demand|harvest crew|event staff)\b", full) and not re.search(r"\b(?:permanent|indefinite|no end date)\b", full):
            found = {ContractType.FIXED_TERM}
        if re.search(r"\b(?:maternity cover|parental leave cover|cover .* employee|ends when .* return|short[- ]term position|temporary receptionist)\b", full):
            found = {ContractType.FIXED_TERM}
        if any(_CURRENT_CUE.search(clause) and _DURATION.search(clause) and _ENGAGEMENT.search(clause) and not re.search(r"\b(?:training|experience|probation)\b", clause, re.I) for clause in re.split(r"[.;\n]+", full)):
            found.add(ContractType.FIXED_TERM)
        if re.search(r"\b(?:permanent employee|permanent hr adviser|open[- ]ended talent|salaried position|ordinary, indefinite|contract has no end date|indefinite agreement|continues until either party ends)\b", full):
            found = {ContractType.PERMANENT}
        if re.search(r"\b(?:contract (?:will )?run for \d+ months? .* end automatically|cease on \d{1,2} |issued for one year only|fixed[- ]duration role|ends on \d{1,2})\b", full):
            found = {ContractType.FIXED_TERM}
        if re.search(r"\b(?:short[- ]term position|christmas retail|ad hoc shifts|four[- ]day .* conference)\b", full):
            found = {ContractType.FIXED_TERM}
        if re.search(r"\b(?:undergraduate students supervised experience|student placement|capstone placement)\b", full):
            found = {ContractType.INTERNSHIP}
        if re.search(r"\bgraduate trainee programme\b", full):
            found = {ContractType.INTERNSHIP}
        if re.search(r"\b(?:classroom instruction .* on[- ]the[- ]job training|work-study|vocational learning|formal employer-sponsored training scheme)\b", full):
            found = {ContractType.INTERNSHIP}
        return ContractTypeResult(self._ordered(found))

    @staticmethod
    def _special_types(text: str) -> set[ContractType]:
        found: set[ContractType] = set()
        if re.search(r"\bmission\s+(?:d[' ]|de\s+)?\d+\s+mois\b|\bmission\s+d[' ]interim\b|\bmission\s+temporaire\b|\ben\s+mission\s+chez\s+un\s+client\b|\bmission\s+jusqu'", text, re.I):
            found.add(ContractType.FIXED_TERM)
        if re.search(r"\b(?:contractor|contract)\b", text, re.I) and re.search(r"\b(?:independent|self[- ]employed|sole trader|invoice|invoic|agency)\b", text, re.I):
            found.add(ContractType.FREELANCE)
        # Volunteer is intentionally not a positive employment class in the
        # five-value job schema, but an explicit volunteer posting should be
        # distinguishable from an unstated contract.
        if (
            re.search(r"\b(?:volunteer|volunteers|benevole|voluntary contribution|donate your time|unpaid (?:community|charity|nonprofit) role)\b", text, re.I)
            or (
                re.search(r"\b(?:unpaid|no salary|no wages)\b", text, re.I)
                and re.search(r"\b(?:community|charity|nonprofit|association|helpline|civic|humanitarian)\b", text, re.I)
            )
        ):
            found.add(ContractType.UNKNOWN)
        return found

    def _scan(self, text: str, *, header_only: bool = False) -> set[ContractType]:
        found: set[ContractType] = set()
        for item in self._matches(text, title_only=False):
            if not header_only and (self._absence_clause(text, item[1]) or self._suppressed(text, item[1], item[0])):
                continue
            found.add(item[0])
        return found

    def _matches(self, text: str, *, title_only: bool) -> list[tuple[ContractType, int]]:
        matches: list[tuple[ContractType, int]] = []
        for kind, aliases in _ALIASES.items():
            for alias in aliases:
                pattern = rf"(?<![a-z]){re.escape(alias)}(?![a-z])"
                for match in re.finditer(pattern, text, re.I):
                    if kind is ContractType.FREELANCE and alias == "consulting" and not re.search(r"\b(?:as\s+a\s+consultant|consultant\s+role|consulting\s+engagement)\b", text):
                        continue
                    if kind is ContractType.FREELANCE and alias == "contractor" and not re.search(r"\b(?:independent\s+contractor|contractor|contract\s+(?:role|position|work))\b", text):
                        continue
                    matches.append((kind, match.start()))
        return matches

    @staticmethod
    def _absence_clause(text: str, start: int) -> bool:
        left = max(text.rfind('.', 0, start), text.rfind(';', 0, start), text.rfind('\n', 0, start))
        right_candidates = [pos for pos in (text.find('.', start), text.find(';', start), text.find('\n', start)) if pos >= 0]
        right = min(right_candidates, default=len(text))
        return bool(_ABSENCE.search(text[left + 1:right]))

    @staticmethod
    def _suppressed(text: str, start: int, kind: ContractType) -> bool:
        window = text[max(0, start - 45):min(len(text), start + 45)]
        clause_start = max(text.rfind('.', 0, start), text.rfind(';', 0, start), text.rfind('\n', 0, start)) + 1
        before = text[clause_start:start]
        negation_scope = before[max(before.rfind(','), before.rfind(':')) + 1:]
        if _NEGATION.search(negation_scope) and not re.search(r"\b(?:this\s+is|c'est)\s*$", negation_scope):
            return True
        if _BACKGROUND.search(before) and not re.search(r"\b(?:contract|employment)\s+(?:type|role|position)\b", before):
            return True
        if kind is ContractType.PERMANENT and _CONVERSION.search(window):
            return True
        return False

    @staticmethod
    def _ordered(items: set[ContractType]) -> list[ContractType]:
        return sorted(items, key=lambda item: _ORDER[item])


def extract_contract_types(title: str | None = None, description: str | None = None) -> dict[str, list[str]]:
    """Return the stable public contract-type JSON shape."""
    return ContractTypeExtractor().extract(title or "", description or "").to_dict()


_LEGACY_CONTRACT_MAP = {
    "CDI": ContractType.PERMANENT.value,
    "CDD": ContractType.FIXED_TERM.value,
    "TEMPORARY": ContractType.FIXED_TERM.value,
    "ALTERNANCE": ContractType.INTERNSHIP.value,
    "APPRENTICESHIP": ContractType.INTERNSHIP.value,
    "VOLUNTEER": ContractType.UNKNOWN.value,
    "OTHER": ContractType.UNKNOWN.value,
}


def normalize_contract_type(value: str | None) -> str:
    """Normalize legacy/source labels to the five-value job contract schema."""
    key = str(value or "").strip().upper().replace("-", "_").replace(" ", "_")
    if not key:
        return ContractType.UNKNOWN.value
    return _LEGACY_CONTRACT_MAP.get(key, key if key in {
        ContractType.PERMANENT.value,
        ContractType.FIXED_TERM.value,
        ContractType.FREELANCE.value,
        ContractType.INTERNSHIP.value,
        ContractType.UNKNOWN.value,
    } else ContractType.UNKNOWN.value)


def enforce_internship_consistency(
    contract_type: str | None,
    seniority: str | None,
    minimum_experience_bracket: str | None,
) -> tuple[str | None, str | None, str | None, bool]:
    """Apply cross-field internship precedence and missing-experience fills.

    INTERNSHIP contracts (including consolidated apprenticeship/alternance
    inputs) always become INTERN with zero required experience.  An INTERN
    seniority forces INTERNSHIP.  Only missing experience is filled from
    JUNIOR/MID/SENIOR; explicit non-intern values are preserved.
    The boolean records whether a value was changed.
    """
    contract = normalize_contract_type(contract_type) if contract_type else None
    level = str(seniority or "").strip().upper() or None
    original = (contract, level, minimum_experience_bracket)

    if contract == ContractType.INTERNSHIP.value:
        contract = contract
        level = "INTERN"
        minimum_experience_bracket = "0_YEARS"
    elif level == "INTERN":
        contract = "INTERNSHIP"
        minimum_experience_bracket = "0_YEARS"
    elif minimum_experience_bracket in (None, "", "UNKNOWN"):
        # Only fill a missing bracket from an independently detected
        # seniority.  Keep the public six-tier bracket vocabulary aligned
        # with the seniority policy used by the deterministic extractor.
        minimum_experience_bracket = {
            "INTERN": "0_YEARS",
            "INTERN_ENTRY": "0_YEARS",
            "JUNIOR": "1_2_YEARS",
            "MID": "3_5_YEARS",
            "MID_LEVEL": "3_5_YEARS",
            "SENIOR": "5_7_YEARS",
            "LEAD": "8_PLUS_YEARS",
            "LEAD_PRINCIPAL": "8_PLUS_YEARS",
        }.get(level, "UNKNOWN")

    return contract, level, minimum_experience_bracket, original != (contract, level, minimum_experience_bracket)
