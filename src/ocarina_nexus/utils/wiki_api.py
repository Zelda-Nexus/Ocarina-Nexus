"""
MediaWiki API client for Zelda Wiki (zeldawiki.wiki).

Endpoint : https://zeldawiki.wiki/w/api.php
API docs  : https://www.mediawiki.org/wiki/API:Main_page
"""

import time
import httpx
from loguru import logger

from ocarina_nexus.config import USER_AGENT, SCRAPING_DELAY, SCRAPING_MAX_RETRIES, DATA_BASE_URL

API_URL = f"{DATA_BASE_URL}/w/api.php"
HEADERS = {"User-Agent": USER_AGENT}


def _api_get(params: dict) -> dict | None:
    params = {**params, "format": "json"}

    for attempt in range(SCRAPING_MAX_RETRIES):
        try:
            with httpx.Client(headers=HEADERS, timeout=30.0) as client:
                response = client.get(API_URL, params=params)
                response.raise_for_status()
                time.sleep(SCRAPING_DELAY)
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.warning(f"HTTP {e.response.status_code} for params={params}")
            time.sleep(3 * (attempt + 1))
        except httpx.RequestError as e:
            logger.warning(f"Network error: {e}")
            time.sleep(3 * (attempt + 1))

    logger.error(f"Failed after {SCRAPING_MAX_RETRIES} attempts: {params}")
    return None


def get_category_members(category: str, limit: int = 500) -> list[dict]:
    """Fetches all pages in a category, handling API pagination."""
    members = []
    cmcontinue = None

    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": f"Category:{category}",
            "cmlimit": limit,
            "cmtype": "page",
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue

        data = _api_get(params)
        if not data:
            break

        batch = data.get("query", {}).get("categorymembers", [])
        members.extend(batch)
        logger.debug(f"  +{len(batch)} pages (total: {len(members)})")

        cmcontinue = data.get("continue", {}).get("cmcontinue")
        if not cmcontinue:
            break

    logger.info(f"Category '{category}': {len(members)} pages found")
    return members


def get_page_data(title: str) -> dict | None:
    """Fetches full page data via action=parse."""
    params = {
        "action": "parse",
        "page": title,
        "prop": "text|wikitext|categories",
        "redirects": 1,
    }

    data = _api_get(params)
    if not data or "parse" not in data:
        logger.warning(f"No data for page: {title}")
        return None

    parsed = data["parse"]
    return {
        "title": parsed.get("title", title),
        "html": parsed.get("text", {}).get("*", ""),
        "wikitext": parsed.get("wikitext", {}).get("*", ""),
        "categories": [c["*"] for c in parsed.get("categories", [])],
    }
