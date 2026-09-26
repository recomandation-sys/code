"""Versioned leaf collision / precedence rules (Phase G)."""
from __future__ import annotations

# winner beats losers when winner evidence is present among candidates
COLLISION_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("FULLSTACK_DEVELOPER", ("FRONTEND_DEVELOPER", "BACKEND_DEVELOPER")),
    ("DEVSECOPS_ENGINEER", ("DEVOPS_ENGINEER",)),
    ("SITE_RELIABILITY_ENGINEER", ("DEVOPS_ENGINEER",)),
    ("SAP_DEVELOPER", ("SOFTWARE_ENGINEER", "SOFTWARE_DEVELOPER")),
    ("SAP_FUNCTIONAL_CONSULTANT", ("FUNCTIONAL_CONSULTANT",)),
    ("NETWORK_SECURITY_ENGINEER", ("NETWORK_ENGINEER",)),
    ("DATABASE_ADMINISTRATOR", ("DATABASE_ENGINEER",)),
]

HIGH_PRECISION_MIN_PRIORITY = 90


def apply_collisions(candidates: list) -> list:
    """Drop generic losers when a more specific winner is present."""
    leaves = {c.leaf for c in candidates}
    drop: set[str] = set()
    for winner, losers in COLLISION_RULES:
        if winner in leaves:
            drop.update(losers)
    if not drop:
        return candidates
    return [c for c in candidates if c.leaf not in drop]
