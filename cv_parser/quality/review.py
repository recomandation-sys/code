"""Review items (sections 45, 51): a flat, actionable checklist of exactly
which fields the frontend review form should highlight for the candidate
to confirm/fill in — never a re-statement of the whole draft, only the
parts genuinely worth a human glance.
"""
from __future__ import annotations

from cv_parser.schemas.parser_response import (
    ExperienceSection,
    IdentitySection,
    LanguageEntry,
    ReviewItem,
    SkillsSection,
    TargetSection,
)

_LOW_CONFIDENCE = {"MEDIUM", "LOW"}


def build_review_items(
    *,
    identity: IdentitySection,
    target: TargetSection,
    experience: ExperienceSection,
    skills: SkillsSection,
    languages: list[LanguageEntry],
) -> list[ReviewItem]:
    items: list[ReviewItem] = []

    if identity.full_name is None:
        items.append(ReviewItem(field="identity.full_name", reason="Full name could not be extracted", confidence=None))
    elif identity.full_name.confidence in _LOW_CONFIDENCE:
        items.append(
            ReviewItem(
                field="identity.full_name", reason="Full name extracted with low confidence", confidence=identity.full_name.confidence
            )
        )

    if identity.email is None:
        items.append(ReviewItem(field="identity.email", reason="Email address could not be extracted", confidence=None))

    if not target.desired_positions:
        items.append(
            ReviewItem(field="target.desired_positions", reason="No desired position stated in the CV", confidence=None)
        )

    for record in experience.records:
        if record.confidence == "LOW":
            items.append(
                ReviewItem(
                    field=f"experience.records[{record.id}]",
                    reason="Experience record has low structural coherence (missing date/title/detail)",
                    confidence="LOW",
                )
            )

    if skills.unmapped_technology_candidates:
        items.append(
            ReviewItem(
                field="skills.unmapped_technology_candidates",
                reason=f"{len(skills.unmapped_technology_candidates)} unrecognized technology mention(s) need confirmation",
                confidence=None,
            )
        )

    for language in languages:
        if language.normalized_level == "UNKNOWN":
            items.append(
                ReviewItem(
                    field=f"languages[{language.language}]",
                    reason=f"Proficiency phrase {language.raw_level!r} could not be mapped to a standard level",
                    confidence=None,
                )
            )

    return items
