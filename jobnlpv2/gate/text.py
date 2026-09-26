"""Isolate a description, turn HTML into text, and clean it. No language calls."""
from __future__ import annotations

import html
import re
import unicodedata

from bs4 import BeautifulSoup, Comment

from .config import GateConfig

FULL_PAGE_HTML = "full_page_html"
DESCRIPTION_HTML = "description_html"
PLAIN_TEXT = "plain_text"
INPUT_MODES = frozenset({FULL_PAGE_HTML, DESCRIPTION_HTML, PLAIN_TEXT})

DESCRIPTION_SELECTOR_NOT_FOUND = "DESCRIPTION_SELECTOR_NOT_FOUND"
HTML_PARSE_FAILED = "HTML_PARSE_FAILED"

_DROP_TAGS = ("script", "style", "template", "svg", "iframe", "noscript")
_BLOCKS = ("p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "tr", "br")
_INVISIBLE = re.compile(r"[\u200b\u200c\u200d\ufeff\u00ad]")
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
_EMAIL = re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.I)
_URL = re.compile(r"https?://[^\s<>]+|www\.[^\s<>]+", re.I)
_PHONE = re.compile(
    r"(?<![\w])(?:\+\d{1,3}[\s().-]*)?(?:\(?\d{1,4}\)?[\s().-]*){2,}\d{2,4}(?![\w])"
)
_DATE = re.compile(r"^(?:19|20)\d{2}-\d{2}-\d{2}$")
_YEAR_SPAN = re.compile(r"^(?:19|20)\d{2}\s*[-–]\s*(?:19|20)\d{2}$")
_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)

# Used only to skip a confirmation chunk that is a skills list or a nav line.
# A full English posting is never refused because these words appear in it.
_TECH = frozenset(
    """python java javascript typescript aws azure gcp docker kubernetes react angular
    vue sql linux git node django flask spring php ruby golang rust scala kotlin swift
    html css mongodb postgres mysql redis kafka spark hadoop terraform ansible jenkins
    graphql nosql oracle postgresql csharp cpp dotnet js ts k8s pytorch tensorflow
    pandas numpy sap odoo""".split()
)
_NAV = frozenset(
    """cookie cookies privacy newsletter unsubscribe sitemap navigation menu footer
    header facebook linkedin twitter instagram youtube copyright""".split()
)


class IsolateError(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def meaningful_word_count(text: str) -> int:
    return sum(1 for token in text.split() if _LETTER.search(token))


def isolate_description(
    raw: str,
    *,
    mode: str,
    source: str,
    config: GateConfig,
) -> str:
    if mode == PLAIN_TEXT:
        return raw
    try:
        soup = BeautifulSoup(html.unescape(raw), "html.parser")
    except Exception as exc:
        raise IsolateError(HTML_PARSE_FAILED) from exc
    if mode == FULL_PAGE_HTML:
        selector = config.description_selectors.get(source, "").strip()
        if not selector:
            raise IsolateError(DESCRIPTION_SELECTOR_NOT_FOUND)
        try:
            node = soup.select_one(selector)
        except Exception as exc:
            raise IsolateError(HTML_PARSE_FAILED) from exc
        if node is None:
            raise IsolateError(DESCRIPTION_SELECTOR_NOT_FOUND)
        soup = node
    elif mode != DESCRIPTION_HTML:
        raise IsolateError(HTML_PARSE_FAILED)
    _drop_unwanted(soup, config.unwanted_selectors.get(source, ()))
    try:
        return _readable(soup)
    except Exception as exc:
        raise IsolateError(HTML_PARSE_FAILED) from exc


def _drop_unwanted(soup, selectors: tuple[str, ...]) -> None:
    for selector in selectors:
        try:
            for node in soup.select(selector):
                node.decompose()
        except Exception as exc:
            raise IsolateError(HTML_PARSE_FAILED) from exc


def _readable(soup) -> str:
    for tag in soup.find_all(_DROP_TAGS):
        tag.decompose()
    for comment in soup.find_all(string=lambda value: isinstance(value, Comment)):
        comment.extract()
    for item in soup.find_all("li"):
        if not item.get_text(" ", strip=True).startswith("-"):
            item.insert(0, "- ")
    for block in soup.find_all(_BLOCKS):
        block.append("\n")
    return soup.get_text("\n")


def _is_phone(raw: str) -> bool:
    token = raw.strip()
    if _DATE.fullmatch(token) or _YEAR_SPAN.fullmatch(token):
        return False
    digits = re.sub(r"\D", "", token)
    if not 8 <= len(digits) <= 15:
        return False
    if not token.startswith("+") and not re.search(r"[\s().-]", token):
        return False
    return True


def clean_description(text: str, *, source: str, config: GateConfig) -> str:
    cleaned = html.unescape(text or "")
    cleaned = unicodedata.normalize("NFKC", cleaned)
    cleaned = _INVISIBLE.sub("", cleaned)
    cleaned = _CONTROL.sub(" ", cleaned)
    cleaned = _EMAIL.sub(" ", cleaned)
    cleaned = _URL.sub(" ", cleaned)
    cleaned = _PHONE.sub(lambda match: " " if _is_phone(match.group(0)) else match.group(0), cleaned)
    boilerplate = {line.casefold().strip() for line in config.boilerplate_lines.get(source, ())}
    if boilerplate:
        kept = []
        for line in cleaned.splitlines():
            if line.strip().casefold() not in boilerplate:
                kept.append(line)
        cleaned = "\n".join(kept)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = re.sub(r"[ \t\f\v]+", " ", cleaned)
    cleaned = re.sub(r" *\n *", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def prediction_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _norm_token(token: str) -> str:
    return re.sub(r"[^\w]+", "", token, flags=re.UNICODE).casefold()


def _substantive(tokens: list[str], minimum: int) -> bool:
    words = [token for token in tokens if _LETTER.search(token)]
    if len(words) < minimum:
        return False
    real = 0
    for token in words:
        folded = _norm_token(token)
        if folded in _TECH or folded in _NAV or token.startswith(("http", "www.")):
            continue
        real += 1
    return real >= minimum and real / len(words) >= 0.5


def confirmation_chunks(text: str, config: GateConfig) -> tuple[str, str] | None:
    """First two substantive spans. None when those two spans cannot be built."""
    tokens = text.split()
    minimum = config.min_substantive_chunk_words
    if len(tokens) < minimum * 2:
        return None
    window = min(config.chunk_words, len(tokens) // 2)
    if window < minimum:
        return None
    step = max(1, window // 4)

    def next_span(start: int):
        while start + window <= len(tokens):
            span = tokens[start:start + window]
            if _substantive(span, minimum):
                return start + window, span
            start += step
        return None

    found = next_span(0)
    if found is None:
        return None
    second = next_span(found[0])
    if second is None:
        return None
    return " ".join(found[1]), " ".join(second[1])
