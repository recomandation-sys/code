"""English IT board pages. Description is the visible contentbloc, never the JSON-LD body."""
from __future__ import annotations

from urllib.parse import urljoin

from bs4 import BeautifulSoup

from jobnlpv2.visible import (
    job_id_from_url,
    parse_jsonld_jobposting,
    squash,
    visible_description,
)

BASE = "https://www.rekrute.com"
_SIDEBAR = {
    "education": ("Level of education and training", "Niveau d'études", "Niveau d’études"),
    "experience": ("Experience required", "Niveau d'expérience", "Niveau d’expérience"),
    "contract": ("Contract type", "Type de contrat"),
    "teleworking": ("Teleworking", "Télétravail", "Teletravail"),
}


def _sidebar(soup: BeautifulSoup, titles: tuple[str, ...]) -> str | None:
    wanted = {title.casefold() for title in titles}
    for node in soup.select("li[title]"):
        if (node.get("title") or "").casefold() not in wanted:
            continue
        return squash(node.get_text(" ", strip=True))
    return None


def _deadline(soup: BeautifulSoup, posted: dict) -> str | None:
    value = squash(posted.get("validThrough"))
    if value:
        return value
    for node in soup.select("span.newjob b"):
        text = squash(node.get_text(" ", strip=True))
        if text:
            return text
    return None


def parse_offer(url: str, markup: str) -> dict:
    soup = BeautifulSoup(markup, "html.parser")
    posted = parse_jsonld_jobposting(markup)
    org = posted.get("hiringOrganization") or {}
    if not isinstance(org, dict):
        org = {}
    location = posted.get("jobLocation") or {}
    address = location.get("address") if isinstance(location, dict) else {}
    if not isinstance(address, dict):
        address = {}
    country = address.get("addressCountry")
    if isinstance(country, dict):
        country = country.get("name")
    title = squash(posted.get("title"))
    if not title and soup.h1:
        title = squash(soup.h1.get_text(" ", strip=True))
        if title and " - " in title:
            title = squash(title.rsplit(" - ", 1)[0])
    logo = org.get("logo")
    if not logo:
        photo = soup.select_one("img.photo")
        logo = photo.get("src") if photo else None
    return {
        "job_id": job_id_from_url(url) or "",
        "url": url,
        "title": title,
        "company": squash(org.get("name")),
        "company_logo": urljoin(BASE, logo) if logo else None,
        "country": squash(country) if isinstance(country, str) else None,
        "date_posted": squash(posted.get("datePosted")),
        "deadline": _deadline(soup, posted),
        "education": _sidebar(soup, _SIDEBAR["education"]),
        "teleworking": _sidebar(soup, _SIDEBAR["teleworking"]),
        "contract": _sidebar(soup, _SIDEBAR["contract"]),
        "experience": _sidebar(soup, _SIDEBAR["experience"]),
        "description": visible_description(soup),
    }
