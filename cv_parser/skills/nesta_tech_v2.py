"""CV adapter for job_nlp EnSkillStack (Nesta + Tech Taxonomy V2).

Runs the same production job skill stack on each CV text blob so
technologies and professional skills stay aligned with job extraction.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

from cv_parser.schemas.parser_response import SkillCategory, SkillEvidenceSourceType
from cv_parser.skills.evidence import SkillHit


@lru_cache(maxsize=1)
def _stack():
    from job_nlp.skills.en_skill_stack import EnSkillStack

    stack = EnSkillStack(full_text_recovery=True)
    stack.load()
    return stack


def _category(entity_type: str) -> SkillCategory:
    if entity_type == "TECHNOLOGY":
        return "TECHNOLOGY"  # type: ignore[return-value]
    return "PROFESSIONAL_SKILL"  # type: ignore[return-value]


def extract_blob_skills(
    text: str,
    *,
    source_type: SkillEvidenceSourceType,
    source_id: str,
    source_label: str,
    title: str = "",
) -> list[SkillHit]:
    """Run Nesta+V2 on one CV section/record blob; return SkillHits."""
    if not (text or "").strip():
        return []
    try:
        ents: list[dict[str, Any]] = _stack().extract(text, title=title or "")
    except Exception:  # noqa: BLE001
        return []

    hits: list[SkillHit] = []
    for e in ents:
        et = e.get("entity_type") or "PROFESSIONAL_SKILL"
        name = (e.get("canonical") or e.get("surface") or "").strip()
        if not name:
            continue
        if et == "TECHNOLOGY":
            skill_id = e.get("taxonomy_id") or f"TECH::{name.casefold()}"
        else:
            skill_id = f"PROF::{name.casefold()}"
        hits.append(
            SkillHit(
                skill_id=skill_id,
                canonical_name=name,
                category=_category(et if et != "SKILL" else "PROFESSIONAL_SKILL"),
                raw_text=e.get("surface") or name,
                source_type=source_type,
                source_id=source_id,
                source_label=source_label,
            )
        )
    return hits
