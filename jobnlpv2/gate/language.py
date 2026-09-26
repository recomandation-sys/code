"""One fastText lid.176 model per process. Missing model fails closed."""
from __future__ import annotations

import hashlib
import threading
from pathlib import Path

from .config import GateConfig

_LOCK = threading.Lock()
_PREDICT_LOCK = threading.Lock()
_CACHE: dict[str, "Predictor"] = {}


class ModelUnavailable(Exception):
    pass


class Predictor:
    version = "unavailable"

    def predict(self, text: str) -> tuple[str, float]:
        raise ModelUnavailable("language model unavailable")


class UnavailablePredictor(Predictor):
    def __init__(self, error: str) -> None:
        self.error = error
        self.version = "unavailable"

    def predict(self, text: str) -> tuple[str, float]:
        raise ModelUnavailable(self.error)


class FastTextPredictor(Predictor):
    def __init__(self, path: Path) -> None:
        import fasttext

        fasttext.FastText.eprint = lambda *_args: None
        self._model = fasttext.load_model(str(path))
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1 << 20), b""):
                digest.update(block)
        self.version = f"fasttext-lid.176:{digest.hexdigest()[:16]}"

    def predict(self, text: str) -> tuple[str, float]:
        # fasttext 0.9.2 calls np.array(..., copy=False), which NumPy 2 rejects.
        import numpy as np

        original = np.array

        def array(obj, dtype=None, *args, **kwargs):
            if kwargs.get("copy") is False:
                return np.asarray(obj, dtype=dtype)
            return original(obj, dtype=dtype, *args, **kwargs)

        with _PREDICT_LOCK:
            np.array = array
            try:
                labels, scores = self._model.predict(text, k=1)
            finally:
                np.array = original
        label = str(labels[0]).replace("__label__", "").strip().lower()
        return label, float(scores[0])


def open_predictor(config: GateConfig | None = None) -> Predictor:
    """Load lid.176 once. A missing file or package returns a predictor that refuses."""
    from .config import load_config

    cfg = config or load_config()
    path = cfg.model_path()
    key = str(path)
    with _LOCK:
        cached = _CACHE.get(key)
        if cached is not None:
            return cached
        if not path.is_file():
            predictor: Predictor = UnavailablePredictor(f"model file not found: {path.name}")
        else:
            try:
                predictor = FastTextPredictor(path)
            except Exception as exc:
                predictor = UnavailablePredictor(f"{type(exc).__name__}: model failed to load")
        _CACHE[key] = predictor
        return predictor
