"""
Wikidata — structured entity data (identifiers, dates, external ID
cross-references), CC0. See inventaire §1 "Wikidata Q213911".
"""

from datetime import UTC, datetime

import httpx
from loguru import logger

from ocarina_nexus.config import (
    SCRAPING_DELAY,
    SCRAPING_MAX_RETRIES,
    SOURCE_LICENSES,
    USER_AGENT,
)
from ocarina_nexus.extraction.landing_writer import write_jsonl
from ocarina_nexus.extraction.rate_limit import RateLimiter

# Ocarina of Time and directly related entities, per the catalogue's §6.
ENTITY_IDS = [
    "Q213911",  # The Legend of Zelda: Ocarina of Time
    "Q642526",  # Ocarina of Time 3D
    "Q110737364",  # ocarina (the instrument, as an in-universe item)
    "Q130733199",  # OoT-Randomizer
]

_limiter = RateLimiter(SCRAPING_DELAY)


def _fetch_entity(qid: str) -> dict | None:
    url = f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json"
    for attempt in range(SCRAPING_MAX_RETRIES):
        _limiter.wait()
        try:
            with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30.0) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.json().get("entities", {}).get(qid)
        except httpx.HTTPError as e:
            logger.warning(f"Wikidata fetch failed for {qid} (attempt {attempt + 1}): {e}")
    return None


def extract(entity_ids: list[str] | None = None) -> int:
    entity_ids = entity_ids if entity_ids is not None else ENTITY_IDS
    rows = []

    for qid in entity_ids:
        entity = _fetch_entity(qid)
        if entity is None:
            logger.warning(f"wikidata: no data for {qid}")
            continue
        rows.append(
            {
                "qid": qid,
                "entity": entity,
                "fetched_at": datetime.now(UTC).isoformat(),
            }
        )

    write_jsonl(
        source="wikidata_wikipedia",
        entity="wikidata_entities",
        rows=rows,
        source_url="https://www.wikidata.org/wiki/Q213911",
        **SOURCE_LICENSES["wikidata"],
    )
    return len(rows)
