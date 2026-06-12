"""
OOT character scraper via the Zelda Wiki MediaWiki API.
"""

from datetime import datetime, timezone

from loguru import logger

from ocarina_nexus.models.entities import RawCharacter
from ocarina_nexus.utils.wiki_api import get_category_members, get_page_data
from ocarina_nexus.utils.infobox_parser import parse_infobox, get_title, get_description
from ocarina_nexus.utils.logging import setup_logging
from ocarina_nexus.config import get_bronze_path, DATA_BASE_URL

CATEGORY = "Characters in Ocarina of Time"


def _make_slug(name: str) -> str:
    return (
        name.lower()
        .replace(" ", "_")
        .replace("'", "")
        .replace("(", "")
        .replace(")", "")
        .replace("/", "-")
    )


def scrape_character(title: str) -> RawCharacter | None:
    data = get_page_data(title)
    if not data:
        return None

    html = data["html"]
    infobox = parse_infobox(html)
    display_name = get_title(html) or data["title"]
    description = get_description(html)

    return RawCharacter(
        name=display_name,
        url=f"{DATA_BASE_URL}/wiki/{data['title'].replace(' ', '_')}",
        infobox=infobox,
        description=description,
        categories=data["categories"],
        source="zeldawiki",
        scraped_at=datetime.now(timezone.utc).isoformat(),
    )


def run(limit: int | None = None, resume: bool = True):
    setup_logging()
    bronze_path = get_bronze_path("characters")

    logger.info("=== Ocarina Nexus — Scraping characters ===")
    logger.info(f"Category : {CATEGORY}")
    logger.info(f"Output   : {bronze_path}")

    members = get_category_members(CATEGORY)
    titles = [m["title"] for m in members]

    if limit:
        titles = titles[:limit]

    logger.info(f"{len(titles)} characters to process")

    scraped, skipped, errors = 0, 0, 0

    for i, title in enumerate(titles, 1):
        slug = _make_slug(title)
        output_file = bronze_path / f"{slug}.json"

        if resume and output_file.exists():
            skipped += 1
            continue

        logger.info(f"[{i}/{len(titles)}] {title}")
        character = scrape_character(title)

        if character:
            output_file.write_text(character.model_dump_json(indent=2), encoding="utf-8")
            scraped += 1
        else:
            errors += 1
            logger.warning(f"Failed: {title}")

    logger.info("=== Report ===")
    logger.info(f"  Scraped  : {scraped}")
    logger.info(f"  Skipped  : {skipped}")
    logger.info(f"  Errors   : {errors}")
    logger.info(f"  Total    : {len(titles)}")


if __name__ == "__main__":
    run()
