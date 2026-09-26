"""cv_parser — deterministic, CPU-only, template-independent CV extraction.

No LLM, no transformer inference, no GPU requirement. Structure is
discovered from PDF geometry (PyMuPDF) before any field is extracted;
IT skills are matched against a curated offline lexicon with Aho-Corasick
+ RapidFuzz, never invented via embeddings or generic keyword extraction.

Entry points:
- ``cv_parser.pipeline.extract_profile`` — parser draft for review
- ``cv_parser.pipeline.extract_candidate_profile`` — normalized profile for matching
"""

__all__ = ["extract_profile", "extract_candidate_profile"]
__version__ = "3.0.0"


def __getattr__(name: str):
    if name == "extract_profile":
        from cv_parser.pipeline import extract_profile

        return extract_profile
    if name == "extract_candidate_profile":
        from cv_parser.pipeline import extract_candidate_profile

        return extract_candidate_profile
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
