"""
In-game text (dialogue/menu script), English NTSC 1.0, keyed by hex text ID.

Primary source: CloudModding OoT Wiki (wiki.cloudmodding.com/woot/api.php),
category "Text Ids" — confirmed reachable via its MediaWiki API, license not
specified upstream (fan wiki) so treated as internal-use-only, never
republished verbatim on the public site (see config.SOURCE_LICENSES).

Secondary, best-effort: Zelda Legends' 2003-era text dumps (zeldalegends.net),
for FR/DE/JA cross-checking. That site serves its content through nested
frames with a fragile, undocumented URL scheme; this module makes one
attempt and logs+skips on failure rather than guessing at frame URLs — vague
2 is explicitly allowed to ship with CloudModding alone this round.
"""

import re
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

CLOUDMODDING_API_URL = "https://wiki.cloudmodding.com/woot/api.php"
ZELDA_LEGENDS_DUMP_PAGE = "http://www.zeldalegends.net/index.php?n=dumps_oot"

_SECTION_RE = re.compile(r"^===\s*(.+?)\s*===\s*$")
_ROW_RE = re.compile(r"^\|([0-9A-Fa-f]{4})\|\|(.*)$")

_limiter = RateLimiter(SCRAPING_DELAY)


def _api_get(params: dict) -> dict | None:
    params = {**params, "format": "json"}
    for attempt in range(SCRAPING_MAX_RETRIES):
        _limiter.wait()
        try:
            with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30.0) as client:
                response = client.get(CLOUDMODDING_API_URL, params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPError as e:
            logger.warning(f"CloudModding request failed (attempt {attempt + 1}): {e}")
    return None


def _list_text_id_pages() -> list[str]:
    data = _api_get(
        {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Text_Ids",
            "cmlimit": 50,
        }
    )
    if not data:
        return []
    return [m["title"] for m in data.get("query", {}).get("categorymembers", [])]


def _parse_wikitable(wikitext: str, page_title: str) -> list[dict]:
    rows = []
    section = None
    for line in wikitext.splitlines():
        section_match = _SECTION_RE.match(line.strip())
        if section_match:
            section = section_match.group(1)
            continue
        row_match = _ROW_RE.match(line.rstrip())
        if row_match:
            text_id, message = row_match.groups()
            rows.append(
                {
                    "text_id": text_id.upper(),
                    "section": section,
                    "message": message.strip(),
                    "lang": "en",
                    "version": "NTSC 1.0",
                    "source_page": page_title,
                }
            )
    return rows


def _extract_cloudmodding() -> list[dict]:
    pages = _list_text_id_pages()
    rows = []
    for title in pages:
        data = _api_get({"action": "parse", "page": title, "prop": "wikitext", "redirects": 1})
        if not data or "parse" not in data:
            logger.warning(f"game_text: could not fetch {title}")
            continue
        wikitext = data["parse"].get("wikitext", {}).get("*", "")
        rows.extend(_parse_wikitable(wikitext, title))

    now = datetime.now(UTC).isoformat()
    for row in rows:
        row["fetched_at"] = now
    return rows


def _extract_zelda_legends_best_effort() -> list[dict]:
    _limiter.wait()
    try:
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30.0, follow_redirects=True) as client:
            response = client.get(ZELDA_LEGENDS_DUMP_PAGE)
            response.raise_for_status()
    except httpx.HTTPError as e:
        logger.warning(f"game_text: Zelda Legends unreachable, skipping ({e})")
        return []

    return [
        {
            "kind": "dump_index_page_raw_html",
            "html": response.text,
            "note": "Frame-based site; actual dump content is one level deeper and needs manual URL discovery.",
            "fetched_at": datetime.now(UTC).isoformat(),
        }
    ]


def extract() -> int:
    cloudmodding_rows = _extract_cloudmodding()
    write_jsonl(
        source="game_text",
        entity="messages",
        rows=cloudmodding_rows,
        source_url="https://wiki.cloudmodding.com/oot/Text_IDs",
        **SOURCE_LICENSES["game_text"],
    )

    zelda_legends_rows = _extract_zelda_legends_best_effort()
    write_jsonl(
        source="game_text",
        entity="zeldalegends_raw",
        rows=zelda_legends_rows,
        source_url=ZELDA_LEGENDS_DUMP_PAGE,
        **SOURCE_LICENSES["game_text"],
    )

    return len(cloudmodding_rows) + len(zelda_legends_rows)
