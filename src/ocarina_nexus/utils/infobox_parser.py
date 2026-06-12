"""
Parser for "Portable Infobox" (Fandom/Wiki.gg extension).

Typical HTML structure:
    <aside class="portable-infobox">
      <h2 class="pi-title">Saria</h2>
      <div class="pi-item">
        <h3 class="pi-data-label">Race</h3>
        <div class="pi-data-value">Kokiri</div>
      </div>
      ...
    </aside>
"""

import re
from bs4 import BeautifulSoup

_REFERENCE_PATTERN = re.compile(r"^\[\d+\]$")


def parse_infobox(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    aside = soup.find("aside", class_=lambda c: c and "portable-infobox" in c)

    if not aside:
        return {}

    result = {}
    for item in aside.find_all(class_="pi-item"):
        label_el = item.find(class_="pi-data-label")
        value_el = item.find(class_="pi-data-value")

        if not label_el or not value_el:
            continue

        label = label_el.get_text(strip=True)
        value = _extract_value(value_el)

        if label and value:
            result[label] = value

    return result


def _extract_value(value_el) -> str:
    raw_text = value_el.get_text(separator="\n", strip=True)
    parts = [p.strip() for p in raw_text.split("\n") if p.strip()]
    cleaned = [p for p in parts if not _REFERENCE_PATTERN.match(p)]
    return " | ".join(cleaned)


def get_title(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    title_el = soup.find(class_="pi-title")
    return title_el.get_text(strip=True) if title_el else None


def get_description(html: str) -> str | None:
    """Uses separator=" " to avoid merging words split across inline tags (links, italics)."""
    soup = BeautifulSoup(html, "lxml")
    content = soup.find("div", class_="mw-parser-output")
    if not content:
        return None

    for p in content.find_all("p", recursive=False):
        text = p.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\[\d+\]", "", text)
        text = re.sub(r"\s+([.,;:])", r"\1", text)
        if text and len(text) > 40:
            return text

    return None
