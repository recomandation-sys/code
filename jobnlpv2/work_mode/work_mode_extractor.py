"""Deterministic work-mode extraction for job postings."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WorkMode(Enum):
    ONSITE = "ONSITE"
    HYBRID = "HYBRID"
    REMOTE = "REMOTE"


@dataclass(frozen=True)
class WorkModeResult:
    work_modes: list[WorkMode] = field(default_factory=list)

    def to_dict(self) -> dict[str, list[str]]:
        return {"work_modes": [mode.value for mode in self.work_modes]}


_ORDER = {WorkMode.ONSITE: 0, WorkMode.HYBRID: 1, WorkMode.REMOTE: 2}
_HEADER = re.compile(r"(?:work\s+mode|working\s+mode|work\s+arrangement|workplace\s+type|work\s+location\s+type|location\s+type|remote\s+policy|workplace|work\s+style|mode\s+de\s+travail|organisation\s+du\s+travail|lieu\s+de\s+travail|type\s+de\s+travail|teletravail|travail\s+a\s+distance|travail\s+hybride)\s*:\s*([^\n.;]*)", re.I)
_UNSPECIFIED = re.compile(r"\b(?:unspecified|unknown|n/?a|not\s+specified|non\s+precise|non\s+specifie|to\s+be\s+discussed)\b", re.I)
_ABSENCE = re.compile(r"\b(?:work\s+mode\s+not\s+specified|work\s+mode\s+is\s+unspecified|does\s+not\s+specify.*(?:remote|hybrid|onsite)|no\s+work\s+arrangement\s+stated|workplace\s+type\s+not\s+stated|location\s+type\s+not\s+specified|mode\s+de\s+travail\s+non\s+precise|teletravail\s+non\s+precise)", re.I)
_REMOTE = re.compile(r"\b(?:fully\s+remote|full\s+remote|100\s*%\s*remote|100\s+percent\s+remote|remote[- ]first\s+role|remote\s+position|remote\s+role|work(?:ing)?\s+remotely|work(?:ing)?\s+from\s+home|wfh|home[- ]based|location[- ]independent|telecommut(?:e|ing)|virtual\s+role|teletravail|a\s+distance|travail\s+a\s+distance|poste\s+a\s+distance|travail\s+remote|en\s+teletravail|remote)", re.I)
_HYBRID = re.compile(r"\b(?:hybrid(?:\s+(?:work|working|role|position))?|flexible\s+hybrid|office\s+and\s+remote|remote\s+and\s+office|home\s+and\s+office|split\s+between\s+home\s+and\s+office|mix\s+of\s+home\s+and\s+office|work\s+from\s+home\s+and\s+office|hybride|travail\s+hybride|mode\s+hybride|teletravail\s+hybride|alternance\s+bureau\s+et\s+teletravail|teletravail\s+partiel|bureau\s+et\s+teletravail)", re.I)
_ONSITE = re.compile(r"\b(?:on[- ]?site|office[- ]based|in[- ]office|work\s+from\s+our\s+office|based\s+in\s+our\s+office|office\s+presence\s+(?:is\s+)?required|office\s+attendance\s+(?:is\s+)?required|site[- ]based|on[- ]premises|workplace[- ]based|must\s+be\s+present\s+in\s+the\s+office|must\s+work\s+from\s+the\s+office|100\s*%\s+onsite|fully\s+onsite|sur\s+site|en\s+presentiel|au\s+bureau|travail\s+au\s+bureau|presence\s+au\s+bureau\s+obligatoire|sur\s+place|en\s+agence|en\s+magasin|en\s+usine|sur\s+campus|travail\s+sur\s+site)", re.I)
_HYBRID_SPLIT = re.compile(r"(?:remote|home|teletravail|a\s+distance)[^.;\n]{0,80}(?:office|onsite|bureau|sur\s+site)|(?:office|onsite|bureau|sur\s+site)[^.;\n]{0,80}(?:remote|home|teletravail|a\s+distance)", re.I)
_FALSE = re.compile(r"\b(?:remote\s+(?:interview|desktop|access|monitoring|support|sensing|users|teams|employees|workers)|hybrid[- ](?:cloud|infrastructure|architecture|app)|company\s+is\s+remote[- ]first|remote[- ]first\s+company|offices?\s+in|headquarters?\s+in|office\s+located\s+in|team\s+based\s+in|experience\s+(?:managing|working)\s+remote|worked\s+remotely|previous(?:ly)?\s+remote|manage(?:s|d)?\s+(?:remote|distributed)\s+teams?|coordinate onsite|support remote|recruit remote|client sites?|occasional travel to the office|flexible working)", re.I)
_NEGATED = re.compile(r"\b(?:not|no|neither|nor|without|pas\s+de|non|sans)\b", re.I)
_PAGE = re.compile(r"\b(?:teleworking|teletravail)\s*:\s*(hybrid|hybride|yes|oui|no|non|remote)\b", re.I)
_PAGE_MODE = {
    "hybrid": WorkMode.HYBRID, "hybride": WorkMode.HYBRID,
    "yes": WorkMode.REMOTE, "oui": WorkMode.REMOTE, "remote": WorkMode.REMOTE,
    "no": WorkMode.ONSITE, "non": WorkMode.ONSITE,
}
_BARE = {"hybrid": WorkMode.HYBRID, "hybride": WorkMode.HYBRID, "remote": WorkMode.REMOTE, "on site": WorkMode.ONSITE, "onsite": WorkMode.ONSITE, "on-site": WorkMode.ONSITE}


def _fold(text: str) -> str:
    text = (text or "").translate(str.maketrans({"’": "'", "‘": "'", "“": '"', "”": '"'}))
    return "".join(c for c in unicodedata.normalize("NFKD", text).casefold() if not unicodedata.combining(c))


class WorkModeExtractor:
    def __init__(self, default_mode: WorkMode | None = WorkMode.ONSITE):
        # Keep the legacy standalone default, while allowing production callers
        # to require explicit evidence by passing default_mode=None.
        self.default_mode = default_mode

    def extract(self, title: str | None = None, description: str | None = None, workplace: str | None = None) -> WorkModeResult:
        raw_title, raw_body = title or "", description or ""
        t, body = _fold(raw_title), _fold(raw_body)
        stated = self._stated(workplace) or self._stated(body) or self._stated(t)
        if stated:
            return WorkModeResult([stated])
        header = _HEADER.search(body)
        if header:
            value = header.group(1).strip()
            if value and _UNSPECIFIED.search(value):
                return WorkModeResult([self.default_mode] if self.default_mode else [])
            modes = self._scan(value, header=True) if value else set()
            if modes:
                return self._resolved(modes)
        title_modes = self._title_modes(t)
        body_modes = self._body_modes(body)
        if re.search(r"\binitially\b[^.;\n]{0,80}\b(?:office|onsite|on-site|bureau|sur\s+site)\b", body, re.I):
            return WorkModeResult([WorkMode.ONSITE])
        if re.search(r"remote[- ]first[^.;\n]{0,100}(?:requires|must)[^.;\n]{0,60}(?:office|onsite|on-site)", body, re.I):
            return self._resolved({WorkMode.ONSITE})
        if _HYBRID_SPLIT.search(body) and not _ABSENCE.search(body):
            return self._resolved({WorkMode.HYBRID})
        if self._explicit_current(body):
            return self._resolved(self._explicit_current(body))
        modes = body_modes or title_modes
        return self._resolved(modes)

    def _title_modes(self, text: str) -> set[WorkMode]:
        if re.match(r"^remote\s*[-|—:]", text): return {WorkMode.REMOTE}
        if re.match(r"^hybrid\s*[-|—:]", text): return {WorkMode.HYBRID}
        if re.match(r"^(?:onsite|on[- ]site|sur\s+site)\s*[-|—:]", text): return {WorkMode.ONSITE}
        if re.match(r"^(?:teletravail|hybride)\s*[-|—:]", text): return {WorkMode.REMOTE if text.startswith("tele") else WorkMode.HYBRID}
        return set()

    def _body_modes(self, text: str) -> set[WorkMode]:
        modes: set[WorkMode] = set()
        for clause in re.split(r"[.;\n]+", text):
            if not clause.strip() or _ABSENCE.search(clause) or _FALSE.search(clause): continue
            if _HYBRID_SPLIT.search(clause): modes.add(WorkMode.HYBRID); continue
            if _HYBRID.search(clause) and not self._negated(clause, _HYBRID) and not re.search(r"hybrid[- ](?:cloud|infrastructure|architecture|app)", clause): modes.add(WorkMode.HYBRID)
            if _REMOTE.search(clause) and not self._negated(clause, _REMOTE): modes.add(WorkMode.REMOTE)
            if _ONSITE.search(clause) and not self._negated(clause, _ONSITE): modes.add(WorkMode.ONSITE)
        return modes

    @staticmethod
    def _negated(clause: str, pattern: re.Pattern[str]) -> bool:
        for match in pattern.finditer(clause):
            before = clause[max(0, match.start() - 25):match.start()]
            scope = before[max(before.rfind(','), before.rfind(';'), before.rfind(':')) + 1:]
            if _NEGATED.search(scope): return True
        return False

    @staticmethod
    def _explicit_current(text: str) -> set[WorkMode]:
        modes: set[WorkMode] = set()
        if re.search(r"\b(?:requires?|must be|present|work from|work at)\b[^.;\n]{0,70}\b(?:office|onsite|on-site|bureau|sur site)\b", text, re.I): modes.add(WorkMode.ONSITE)
        if re.search(r"\b(?:fully remote|remote work arrangement|position is fully remote|remote position)\b", text, re.I): modes.add(WorkMode.REMOTE)
        return modes

    @staticmethod
    def _scan(text: str, header: bool = False) -> set[WorkMode]:
        modes: set[WorkMode] = set()
        if _HYBRID_SPLIT.search(text) or _HYBRID.search(text): modes.add(WorkMode.HYBRID)
        if _REMOTE.search(text) and not WorkModeExtractor._negated(text, _REMOTE): modes.add(WorkMode.REMOTE)
        if _ONSITE.search(text) and not WorkModeExtractor._negated(text, _ONSITE): modes.add(WorkMode.ONSITE)
        return modes

    @staticmethod
    def _ordered(modes: set[WorkMode]) -> list[WorkMode]:
        return sorted(modes, key=lambda mode: _ORDER[mode])

    @staticmethod
    def _stated(text: str | None) -> WorkMode | None:
        folded = _fold(text or "").strip()
        if not folded:
            return None
        if folded in _BARE:
            return _BARE[folded]
        page = _PAGE.search(folded)
        return _PAGE_MODE[page.group(1)] if page else None

    def _resolved(self, modes: set[WorkMode]) -> WorkModeResult:
        if WorkMode.HYBRID in modes or (WorkMode.REMOTE in modes and WorkMode.ONSITE in modes):
            return WorkModeResult([WorkMode.HYBRID])
        if WorkMode.REMOTE in modes:
            return WorkModeResult([WorkMode.REMOTE])
        if WorkMode.ONSITE in modes:
            return WorkModeResult([WorkMode.ONSITE])
        return WorkModeResult([self.default_mode] if self.default_mode else [])


def extract_work_modes(title: str | None = None, description: str | None = None, workplace: str | None = None) -> dict[str, list[str]]:
    """Return the stable public work-mode JSON shape."""
    return WorkModeExtractor().extract(title, description, workplace).to_dict()


if __name__ == "__main__":
    check = WorkModeExtractor(default_mode=None)
    assert check.extract(workplace="Teleworking : Hybrid").to_dict()["work_modes"] == ["HYBRID"]
    assert check.extract(workplace="Teleworking : No").to_dict()["work_modes"] == ["ONSITE"]
    assert check.extract(workplace="Teleworking : Yes").to_dict()["work_modes"] == ["REMOTE"]
    assert check.extract("", "Hybrid role. Office attendance is required.").to_dict()["work_modes"] == ["HYBRID"]
    assert check.extract("", "The role is remote and also in the office.").to_dict()["work_modes"] == ["HYBRID"]
    assert check.extract("", "This role is on-site.").to_dict()["work_modes"] == ["ONSITE"]
    assert check.extract("", "Fully remote position.").to_dict()["work_modes"] == ["REMOTE"]
