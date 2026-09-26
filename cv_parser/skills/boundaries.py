"""Boundary validation (section 33).

A substring match is not sufficient on its own — "javascript" is a
substring of "javascripted", and "r" is a substring of "research". Naive
`\\b` regex boundaries also fail on purpose-built symbolic aliases like
"C++"/"C#"/".NET" (a leading `.` or trailing `#`/`+` is not a "word"
character, so a plain `\\bC#\\b` silently never matches "C# developer").

Instead we classify the *actual* characters immediately outside the
matched span: if either neighbor is alphanumeric, the match is a fragment
of a larger token and must be rejected, regardless of alias policy. This
single rule handles every alias in section 33's mandatory list (C++, C#,
.NET, Java, Go, R, C, JS, TS) uniformly, with no per-alias special cases.
"""
from __future__ import annotations


def _is_continuation_char(ch: str | None) -> bool:
    if ch is None:
        return False
    return ch.isalnum()


def is_valid_boundary(text: str, start: int, end: int) -> bool:
    """`text` is the (length-preserving normalized) search text; the
    match spans `text[start:end]`. Valid iff the characters immediately
    before `start` and at/after `end` are not alphanumeric — i.e. the
    match is not glued to a larger token on either side.
    """
    before = text[start - 1] if start > 0 else None
    after = text[end] if end < len(text) else None
    return not _is_continuation_char(before) and not _is_continuation_char(after)
