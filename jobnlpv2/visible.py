"""Visible Rekrute offer text. Copied from job_nlp/ingestion/rekrute_scraper.py."""
from __future__ import annotations

import html
import json
import re
from typing import Any
from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup


def squash(text: str | None) -> str | None:
    if text is None:
        return None
    cleaned = re.sub(r"\s+", " ", html.unescape(text)).strip()
    return cleaned or None


def job_id_from_url(url: str) -> str | None:
    match = re.search(r"-(\d+)\.html(?:\?|$)", url)
    return match.group(1) if match else None


def english_offer_url(url: str) -> str:
    """Ask for the /en/ page, which shows the translated offer body."""
    parsed = urlparse(url)
    path = parsed.path or "/"
    if path.startswith("/en/"):
        return url
    if path.startswith("/fr/"):
        path = "/en/" + path[4:]
    else:
        path = "/en" + path
    return urlunparse(parsed._replace(path=path))


def visible_description(soup: BeautifulSoup) -> str | None:
    """Offer text shown on the page. The hidden JobPosting field stays in the employer's language."""
    bloc = soup.select_one("div.contentbloc")
    if bloc is None:
        return None
    parts: list[str] = []
    for node in bloc.find_all("div", class_="blc", recursive=False):
        classes = set(node.get("class") or [])
        if "info" in classes or "center" in classes:
            continue
        text = html_to_text(node.decode_contents())
        if not text or len(text) < 40:
            continue
        if text.casefold().startswith("head office"):
            continue
        parts.append(text)
    return "\n".join(parts) or None


def html_to_text(raw: str | None) -> str | None:
    if not raw:
        return None
    text = BeautifulSoup(html.unescape(raw), "html.parser").get_text("\n")
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line) or None


def parse_jsonld_jobposting(markup: str) -> dict[str, Any]:
    soup = BeautifulSoup(markup, "html.parser")
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text() or ""
        try:
            payload = json.loads(raw, strict=False)
        except (json.JSONDecodeError, TypeError):
            # fallback: regex fields if JSON is dirty
            continue
        blocks = payload if isinstance(payload, list) else [payload]
        for block in blocks:
            if isinstance(block, dict) and str(block.get("@type", "")).lower() == "jobposting":
                return block
    # regex fallback when ld+json is present but not parseable
    out: dict[str, Any] = {}
    for key in ("title", "datePosted", "description", "employmentType"):
        m = re.search(rf'"{key}"\s*:\s*"(.*?)"\s*,', markup, re.S)
        if m:
            out[key] = m.group(1)
    org = re.search(r'"hiringOrganization"\s*:\s*\{[^}]*"name"\s*:\s*"([^"]+)"', markup)
    if org:
        out["hiringOrganization"] = {"name": org.group(1)}
    return out
