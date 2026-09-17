"""
Zelda Wiki Cargo tables (structured data behind Nomenclature/i18n names,
terminology, media files, location features, in-game descriptions, shop
wares, game languages) — see catalogue §1.3.

LIMITATION (documented, not silently worked around): Cargo's query API
(`action=cargoquery`) requires exact field names per table, and this wiki
blocks `Special:CargoTables` (403, likely anti-bot) which would normally let
you discover them. Field names are declared in Lua (`Module:Nomenclature`
etc.), not in wikitext, so they can't be scraped from a template page either.
Guessing field names against the live API only returns a generic
`internal_api_error_MWException` with no field list on a bad guess — dead end
for automated discovery.

What this module does today: queries each table for `_pageName` only (aliased
to `page`, since Cargo API field aliases can't start with `_` — see
inventaire §1.3), which is a real and correct page-level index of which wiki
pages participate in each Cargo table. Full column data (name/lang/meaning
for Nomenclature, price for Wares, etc.) needs the real field names, to be
obtained from a wiki admin/community documentation, then added to `TABLES`
below — at that point this same function handles it, no rewrite needed.

SCOPE WARNING: these Cargo tables are shared across every game the wiki
covers, not just OoT (confirmed live: Nomenclature alone returned ~92k rows
wiki-wide vs. the ~1k the project's own catalogue expected for OoT). Only
`Nomenclature` has a verified OoT-scoping filter so far (its rows live under
`Data:Translations/OoT/*` — confirmed live against the API). The others run
wiki-wide until someone finds their equivalent filter, capped by
`_MAX_PAGES_UNSCOPED` so an unscoped table can't silently turn into a
multi-minute, mostly-irrelevant pull.
"""

from datetime import UTC, datetime

import httpx
from loguru import logger

from ocarina_nexus.config import (
    DATA_BASE_URL,
    SCRAPING_DELAY,
    SCRAPING_MAX_RETRIES,
    SOURCE_LICENSES,
    USER_AGENT,
)
from ocarina_nexus.extraction.landing_writer import write_jsonl
from ocarina_nexus.extraction.rate_limit import RateLimiter

API_URL = f"{DATA_BASE_URL}/w/api.php"

# table name -> extra fields known to be safe (beyond _pageName=page).
# Empty for now — see module docstring.
TABLES: dict[str, list[str]] = {
    "Nomenclature": [],
    "Terminologies": [],
    "Files": [],
    "LocationFeatures": [],
    "Descriptions": [],
    "Wares": [],
    "GameLanguages": [],
}

# table name -> verified Cargo `where` clause scoping it to OoT. Tables
# absent here run wiki-wide, capped by _MAX_PAGES_UNSCOPED (see module docstring).
WHERE_CLAUSES: dict[str, str] = {
    "Nomenclature": '_pageName LIKE "Data:Translations/OoT/%"',
}

_LIMIT = 500
_MAX_PAGES_UNSCOPED = 20  # 20 * _LIMIT = 10,000 rows ceiling for tables with no known OoT filter
_limiter = RateLimiter(SCRAPING_DELAY)


def _cargoquery(table: str, extra_fields: list[str], offset: int) -> list[dict] | None:
    fields = ",".join(["_pageName=page", *extra_fields])
    params = {
        "action": "cargoquery",
        "tables": table,
        "fields": fields,
        "limit": _LIMIT,
        "offset": offset,
        "format": "json",
    }
    where = WHERE_CLAUSES.get(table)
    if where:
        params["where"] = where
    for attempt in range(SCRAPING_MAX_RETRIES):
        _limiter.wait()
        try:
            with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30.0) as client:
                response = client.get(API_URL, params=params)
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError as e:
            logger.warning(f"Cargo query failed for {table} (attempt {attempt + 1}): {e}")
            continue

        if "error" in data:
            logger.error(f"Cargo query error for table={table}: {data['error']}")
            return None
        return [row["title"] for row in data.get("cargoquery", [])]

    return None


def extract(tables: dict[str, list[str]] | None = None) -> int:
    tables = tables if tables is not None else TABLES
    total = 0

    for table, extra_fields in tables.items():
        rows: list[dict] = []
        offset = 0
        page = 0
        scoped = table in WHERE_CLAUSES
        while True:
            batch = _cargoquery(table, extra_fields, offset)
            if not batch:
                break
            for row in batch:
                row["_source"] = "zeldawiki_cargo"
                row["_table"] = table
                row["_fetched_at"] = datetime.now(UTC).isoformat()
            rows.extend(batch)
            page += 1
            if len(batch) < _LIMIT:
                break
            if not scoped and page >= _MAX_PAGES_UNSCOPED:
                logger.warning(
                    f"Cargo[{table}]: hit the {_MAX_PAGES_UNSCOPED}-page safety cap for an "
                    f"unscoped (wiki-wide) table — data is a partial sample, not exhaustive"
                )
                break
            offset += _LIMIT

        write_jsonl(
            source="zeldawiki_cargo",
            entity=table.lower(),
            rows=rows,
            source_url=f"{DATA_BASE_URL}/wiki/Special:CargoTables/{table}",
            **SOURCE_LICENSES["zeldawiki"],
        )
        total += len(rows)
        logger.info(f"Cargo[{table}]: {len(rows)} rows (page index only, see module docstring)")

    return total
