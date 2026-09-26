"""Compatibility re-export. Implementation: jobnlpv2/education/extractor.py."""
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[3] / "jobnlpv2"
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from education import extractor as _impl

globals().update({name: getattr(_impl, name) for name in dir(_impl) if not name.startswith("__")})
