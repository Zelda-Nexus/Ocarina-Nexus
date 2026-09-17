"""
Entry point for the extraction layer.

    python -m ocarina_nexus.extraction.cli --source all
    python -m ocarina_nexus.extraction.cli --source zeldawiki_pages --page-limit 3
"""

import argparse
import sys

from loguru import logger

from ocarina_nexus.extraction.sources import (
    game_text,
    oot_randomizer_github,
    speedrun_com,
    wikidata,
    wikipedia,
    zeldaret_oot_github,
    zeldawiki_cargo,
    zeldawiki_pages,
)
from ocarina_nexus.utils.logging import setup_logging

# name -> callable. Each returns the number of rows written.
SOURCE_REGISTRY = {
    "zeldawiki_pages": zeldawiki_pages.extract,
    "zeldawiki_cargo": zeldawiki_cargo.extract,
    "wikidata": wikidata.extract,
    "wikipedia": wikipedia.extract,
    "oot_randomizer": oot_randomizer_github.extract,
    "zeldaret_oot": zeldaret_oot_github.extract,
    "game_text": game_text.extract,
    "speedrun_com": speedrun_com.extract,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ocarina Nexus — extraction layer")
    parser.add_argument(
        "--source",
        action="append",
        choices=[*SOURCE_REGISTRY.keys(), "all"],
        required=True,
        help="Source to run; repeatable, or 'all'.",
    )
    parser.add_argument(
        "--page-limit",
        type=int,
        default=None,
        help="Caps pages fetched per category for zeldawiki_pages (smoke-testing only).",
    )
    args = parser.parse_args(argv)

    setup_logging()

    sources = list(SOURCE_REGISTRY.keys()) if "all" in args.source else args.source

    total = 0
    failures = []
    for name in sources:
        logger.info(f"=== extraction: {name} ===")
        try:
            if name == "zeldawiki_pages" and args.page_limit is not None:
                count = SOURCE_REGISTRY[name](page_limit=args.page_limit)
            else:
                count = SOURCE_REGISTRY[name]()
            logger.info(f"=== {name}: {count} rows ===")
            total += count
        except Exception:  # noqa: BLE001 — one source failing must not abort the others
            logger.exception(f"extraction failed for source={name}")
            failures.append(name)

    logger.info(f"Total rows written: {total}")
    if failures:
        logger.error(f"Failed sources: {failures}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
