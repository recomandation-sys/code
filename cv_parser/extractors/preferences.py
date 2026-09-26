"""Contract and work-mode preference extraction (section 23).

"Only explicit preference language counts." A contract-type or work-mode
word is only ever picked up from a line that *also* contains an explicit,
forward-looking "seeking/looking for" trigger phrase in the same line —
this is what keeps "Stage chez Company X — 2024" (a past internship,
mentioned in the experience section) from ever being read as a current
`INTERNSHIP` preference, while "Recherche CDI ou CDD" correctly is.
"""
from __future__ import annotations

from cv_parser.schemas.internal import Document
from cv_parser.schemas.parser_response import ContractType, WorkMode

_SEEKING_TRIGGERS = [
    "seeking", "looking for", "open to", "available for", "disponible pour",
    "recherche", "recherchant", "à la recherche", "a la recherche", "en recherche de",
]

_CONTRACT_KEYWORDS: dict[ContractType, list[str]] = {
    "CDI": ["cdi", "contrat à durée indéterminée", "contrat a duree indeterminee", "permanent contract", "full-time permanent"],
    "CDD": ["cdd", "contrat à durée déterminée", "contrat a duree determinee", "fixed-term contract"],
    "INTERNSHIP": ["internship", "stage"],
    "ALTERNANCE": ["alternance", "apprentissage", "apprenticeship", "work-study"],
    "FREELANCE": ["freelance", "freelancing", "contractor", "indépendant", "independant"],
}

_WORK_MODE_KEYWORDS: dict[WorkMode, list[str]] = {
    "REMOTE": ["remote", "work from home", "telecommute", "télétravail", "teletravail", "à distance", "a distance"],
    "HYBRID": ["hybrid", "hybride"],
    "ONSITE": ["on-site", "onsite", "in office", "in-person", "sur site", "présentiel", "presentiel"],
}

_CONTRACT_ORDER: list[ContractType] = ["CDI", "CDD", "INTERNSHIP", "ALTERNANCE", "FREELANCE", "OTHER"]
_WORK_MODE_ORDER: list[WorkMode] = ["REMOTE", "HYBRID", "ONSITE"]


def extract_preferences(document: Document) -> tuple[list[ContractType], list[WorkMode]]:
    contract_types: set[ContractType] = set()
    work_modes: set[WorkMode] = set()

    for block in document.blocks:
        for line in block.lines:
            lowered = line.text.lower()
            if not any(trigger in lowered for trigger in _SEEKING_TRIGGERS):
                continue
            for contract_type, keywords in _CONTRACT_KEYWORDS.items():
                if any(kw in lowered for kw in keywords):
                    contract_types.add(contract_type)
            for work_mode, keywords in _WORK_MODE_KEYWORDS.items():
                if any(kw in lowered for kw in keywords):
                    work_modes.add(work_mode)

    ordered_contracts = [c for c in _CONTRACT_ORDER if c in contract_types]
    ordered_modes = [m for m in _WORK_MODE_ORDER if m in work_modes]
    return ordered_contracts, ordered_modes
