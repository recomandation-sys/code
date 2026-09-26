"""Context disambiguation for `CONTEXT_REQUIRED` aliases (section 30).

`Go`, `R`, `C`, `JS`, `TS`, `Node`, ... are real technology names but also
plausible English words or fragments of ordinary prose. A boundary-valid
match is not enough on its own — it must additionally sit inside evidence
that the surrounding text is a technology list, not narrative sentences:

    "Languages: Python, Go, Java"      -> accept Go (comma-separated list)
    "Ready to go into production"      -> reject Go (plain prose)
    "I used Go and Kubernetes here"    -> accept Go (neighboring known skill)
"""
from __future__ import annotations

from cv_parser.config import settings
from cv_parser.skills.normalization import find_tech_list_label

_LIST_SEPARATORS = (",", "|", ";", "\u2022", "/")


def _line_span(text: str, start: int, end: int) -> str:
    line_start = text.rfind("\n", 0, start) + 1
    line_end = text.find("\n", end)
    if line_end == -1:
        line_end = len(text)
    return text[line_start:line_end]


def is_context_sufficient(
    text: str,
    start: int,
    end: int,
    *,
    in_skills_section: bool,
    other_match_spans: list[tuple[int, int]] | None = None,
    window: int | None = None,
) -> bool:
    """Decide whether a `CONTEXT_REQUIRED` match at `text[start:end]`
    has enough surrounding evidence to be accepted (section 30).

    `other_match_spans` are the (start, end) spans of *other*,
    already-accepted skill matches found in the same `text` — a
    "neighboring IT term" is itself one of the explicit context signals
    the spec calls out.
    """
    if in_skills_section:
        return True

    window = settings.ambiguous_skill_context_window_chars if window is None else window
    window_start = max(0, start - window)
    window_end = min(len(text), end + window)
    neighborhood = text[window_start:window_end]
    if any(sep in neighborhood for sep in _LIST_SEPARATORS):
        return True

    line = _line_span(text, start, end)
    if find_tech_list_label(line) is not None:
        return True

    if other_match_spans:
        for other_start, other_end in other_match_spans:
            if other_start == start and other_end == end:
                continue
            if other_start < window_end and other_end > window_start:
                return True

    return False
