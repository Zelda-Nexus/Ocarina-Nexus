"""
Zelda Wiki (zeldawiki.wiki) — encyclopedic pages, across all OoT entity
categories. Reuses `utils/wiki_api.py` (extended `full=True` mode) and
`utils/infobox_parser.py` unchanged, per the README's explicit instruction
that these two modules are the pieces meant to carry over into extraction.

A page can belong to several categories (e.g. a boss is also an enemy): it is
then written once per category file, with `entity_types` set to the single
category queried this call — downstream Silver is responsible for merging
duplicates by `pageid` into one row with the full `entity_types` list, per
the schema cible §2.1.
"""

from datetime import UTC, datetime
from typing import Any

from bs4 import BeautifulSoup
from loguru import logger

from ocarina_nexus.config import DATA_BASE_URL, SOURCE_LICENSES
from ocarina_nexus.extraction.landing_writer import write_jsonl
from ocarina_nexus.utils.infobox_parser import get_description, parse_infobox
from ocarina_nexus.utils.wiki_api import (
    get_category_members,
    get_page_data,
    get_page_touched,
)

# category name (as it exists on Zelda Wiki) -> entity slug (Bronze file name)
CATEGORIES: dict[str, str] = {
    "Characters in Ocarina of Time": "characters",
    "Playable Characters in Ocarina of Time": "playable_characters",
    "Bosses in Ocarina of Time": "bosses",
    "Sub-Bosses in Ocarina of Time": "sub_bosses",
    "Enemies in Ocarina of Time": "enemies",
    "Species in Ocarina of Time": "species",
    "Groups in Ocarina of Time": "groups",
    "Items in Ocarina of Time": "items",
    "Items in Ocarina of Time 3D": "items_3d",
    "Objects in Ocarina of Time": "objects",
    "Locations in Ocarina of Time": "locations",
    "Dungeons in Ocarina of Time": "dungeons",
    "Abilities in Ocarina of Time": "abilities",
    "Mechanics in Ocarina of Time": "mechanics",
    "Mini-Games in Ocarina of Time": "minigames",
    "Interface in Ocarina of Time": "interface",
    "Plot Events in Ocarina of Time": "plot_events",
    "Services in Ocarina of Time": "services",
    "Symbols in Ocarina of Time": "symbols",
}


def _html_to_plaintext(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    content = soup.find("div", class_="mw-parser-output") or soup
    return content.get_text(separator=" ", strip=True)


def _page_row(title: str, slug: str, cache: dict[str, dict]) -> dict[str, Any] | None:
    page = cache.get(title)
    if page is None:
        page = get_page_data(title, full=True)
        if page is not None:
            cache[title] = page
    if page is None:
        logger.warning(f"zeldawiki: page not found: {title}")
        return None

    touched = get_page_touched(title)
    infobox = parse_infobox(page["html"])
    description = get_description(page["html"])

    return {
        "pageid": page.get("pageid"),
        "title": page["title"],
        "requested_title": title,
        "displaytitle": page.get("displaytitle"),
        "url": f"{DATA_BASE_URL}/wiki/{page['title'].replace(' ', '_')}",
        "entity_types": [slug],
        "lastrevid": page.get("lastrevid"),
        "touched": touched,
        "length": len(page.get("wikitext", "") or ""),
        "wikitext": page.get("wikitext"),
        "plaintext": _html_to_plaintext(page.get("html", "")),
        "sections": page.get("sections", []),
        "infobox": infobox,
        "categories": page.get("categories", []),
        "hidden_categories": page.get("hidden_categories", []),
        "links": page.get("links", []),
        "images": page.get("images", []),
        "templates": page.get("templates", []),
        "external_links": page.get("external_links", []),
        "description": description,
        "source": "zeldawiki",
        "fetched_at": datetime.now(UTC).isoformat(),
    }


def extract(categories: dict[str, str] | None = None, page_limit: int | None = None) -> int:
    """
    `categories`: subset of CATEGORIES to run (defaults to all 19).
    `page_limit`: caps pages fetched per category — for smoke-testing only;
    leave unset for a real run (the full run is meant to happen on a
    schedule, not interactively).
    """
    categories = categories if categories is not None else CATEGORIES
    cache: dict[str, dict] = {}
    total = 0

    for category, slug in categories.items():
        members = get_category_members(category)
        titles = [m["title"] for m in members]
        if page_limit is not None:
            titles = titles[:page_limit]

        rows = []
        for title in titles:
            row = _page_row(title, slug, cache)
            if row is not None:
                rows.append(row)

        write_jsonl(
            source="zeldawiki",
            entity=slug,
            rows=rows,
            source_url=f"{DATA_BASE_URL}/wiki/Category:{category.replace(' ', '_')}",
            **SOURCE_LICENSES["zeldawiki"],
        )
        total += len(rows)

    return total
