"""Compatibility re-export. Implementation: jobnlpv2/education."""
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[3] / "jobnlpv2"
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from education import EducationExtractor, EducationLevel, EducationResult

__all__ = ["EducationExtractor", "EducationLevel", "EducationResult"]
