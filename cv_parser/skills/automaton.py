"""Aho-Corasick automaton over the lexicon's normalized aliases (section 32).

Built once per worker process from the cached `Lexicon` and reused for
every CV — "never rebuild per CV". `iter_long` gives longest-match,
non-overlapping results directly, so a longer alias (".NET Core") is
always preferred over a shorter one it contains (".NET") when both would
otherwise match at the same position.
"""
from __future__ import annotations

from functools import lru_cache

import ahocorasick

from cv_parser.skills.lexicon import get_lexicon
from cv_parser.skills.models import AliasEntry


@lru_cache(maxsize=1)
def get_automaton() -> ahocorasick.Automaton:
    lexicon = get_lexicon()
    automaton = ahocorasick.Automaton()
    for normalized, alias_entry in lexicon.alias_index.items():
        automaton.add_word(normalized, alias_entry)
    automaton.make_automaton()
    return automaton


def scan(normalized_text: str) -> list[tuple[int, int, AliasEntry]]:
    """Longest-match, non-overlapping raw hits as (start, end, AliasEntry)
    spans over `normalized_text` (end exclusive). Callers still owe
    boundary validation (section 33) and, for `CONTEXT_REQUIRED` aliases,
    context disambiguation (section 30) before treating a hit as real.
    """
    automaton = get_automaton()
    if not normalized_text:
        return []
    results: list[tuple[int, int, AliasEntry]] = []
    for end_index, alias_entry in automaton.iter_long(normalized_text):
        start_index = end_index - len(alias_entry.normalized_text) + 1
        results.append((start_index, end_index + 1, alias_entry))
    return results
