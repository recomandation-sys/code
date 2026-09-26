"""Compatibility re-export. Implementation: jobnlpv2/contract/contract_type_extractor.py."""
import importlib.util
import sys
from pathlib import Path

_impl = Path(__file__).resolve().parents[2] / "jobnlpv2" / "contract" / "contract_type_extractor.py"
_dir = str(_impl.parent)
if _dir not in sys.path:
    sys.path.insert(0, _dir)
_spec = importlib.util.spec_from_file_location("job_nlpv2_contract_type_extractor", _impl)
if _spec is None or _spec.loader is None:
    raise ImportError(str(_impl))
_mod = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = _mod
_spec.loader.exec_module(_mod)
globals().update({name: getattr(_mod, name) for name in dir(_mod) if not name.startswith("__")})
