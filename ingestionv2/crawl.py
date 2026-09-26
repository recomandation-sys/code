"""Crawl the English IT board. Already stored offer ids are not fetched again."""
from __future__ import annotations

import json
import time
from pathlib import Path

from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from ingestionv2.parse import BASE, parse_offer
from jobnlpv2.visible import english_offer_url, job_id_from_url

LIST_URL = BASE + "/en/offres-emploi-metiers-de-l-it.html?p={page}&s=1"
RAW_PATH = Path(__file__).resolve().parent / "output" / "rekrute_raw.jsonl"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def stored_ids(path: Path = RAW_PATH) -> set[str]:
    if not path.is_file():
        return set()
    found = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("job_id"):
            found.add(str(row["job_id"]))
    return found


def listing_offers(markup: str) -> list[tuple[str, str]]:
    soup = BeautifulSoup(markup, "html.parser")
    found: list[tuple[str, str]] = []
    seen: set[str] = set()
    for link in soup.select("a[href]"):
        href = (link.get("href") or "").split("#", 1)[0]
        if "offre-emploi" not in href:
            continue
        offer_id = job_id_from_url(href)
        if not offer_id or offer_id in seen:
            continue
        seen.add(offer_id)
        found.append((offer_id, english_offer_url(urljoin(BASE, href))))
    return found


def listing_ids(markup: str) -> list[str]:
    return [offer_id for offer_id, _url in listing_offers(markup)]


def new_ids(page_ids: list[str], seen: set[str]) -> list[str]:
    return [offer_id for offer_id in page_ids if offer_id not in seen]


def crawl(path: Path = RAW_PATH, delay: float = 0.7) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    known = stored_ids(path)
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en"})
    seen: set[str] = set()
    added = 0
    page = 1
    while True:
        response = session.get(LIST_URL.format(page=page), timeout=30)
        response.raise_for_status()
        page_offers = listing_offers(response.text)
        page_ids = [offer_id for offer_id, _url in page_offers]
        fresh = new_ids(page_ids, seen)
        if not fresh:
            break
        seen.update(fresh)
        wanted = {offer_id for offer_id in fresh if offer_id not in known}
        for offer_id, url in page_offers:
            if offer_id not in wanted:
                continue
            try:
                offer = session.get(url, timeout=30)
                offer.raise_for_status()
            except requests.RequestException:
                continue
            final = english_offer_url(offer.url)
            row = parse_offer(final, offer.text)
            row["job_id"] = row["job_id"] or offer_id
            row["url"] = final
            with path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            known.add(row["job_id"])
            added += 1
            time.sleep(delay)
        page += 1
        time.sleep(delay)
    return added
