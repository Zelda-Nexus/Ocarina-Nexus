"""
Wikipedia — encyclopedic/reception/development context, CC BY-SA 4.0.
EN only this round (confirmed scope); `lang` is a plain parameter, extending
to FR/JA/DE later is a call-site change, not a rewrite.
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

ARTICLES = [
    "The Legend of Zelda: Ocarina of Time",
    "The Legend of Zelda: Ocarina of Time 3D",
    "The Legend of Zelda: Master Quest",
]

_limiter = RateLimiter(SCRAPING_DELAY)


def _fetch_article(title: str, lang: str) -> dict | None:
    page_title = title.replace(" ", "_")
    summary_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{page_title}"
    wikitext_url = f"https://{lang}.wikipedia.org/w/api.php"

    for attempt in range(SCRAPING_MAX_RETRIES):
        _limiter.wait()
        try:
            with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30.0) as client:
                summary = client.get(summary_url)
                if summary.status_code == 404:
                    return None
                summary.raise_for_status()
                summary_data = summary.json()

                wikitext_resp = client.get(
                    wikitext_url,
                    params={
                        "action": "parse",
                        "page": title,
                        "prop": "wikitext",
                        "format": "json",
                        "redirects": 1,
                    },
                )
                wikitext_resp.raise_for_status()
                wikitext_data = wikitext_resp.json()

            return {
                "title": summary_data.get("title", title),
                "lang": lang,
                "extract": summary_data.get("extract"),
                "wikitext": wikitext_data.get("parse", {}).get("wikitext", {}).get("*"),
                "pageid": summary_data.get("pageid"),
                "url": summary_data.get("content_urls", {}).get("desktop", {}).get("page"),
                "thumbnail_url": summary_data.get("thumbnail", {}).get("source"),
            }
        except httpx.HTTPError as e:
            logger.warning(f"Wikipedia fetch failed for {title} ({lang}, attempt {attempt + 1}): {e}")

    return None


def extract(articles: list[str] | None = None, langs: list[str] | None = None) -> int:
    articles = articles if articles is not None else ARTICLES
    langs = langs if langs is not None else ["en"]

    rows = []
    for lang in langs:
        for title in articles:
            article = _fetch_article(title, lang)
            if article is None:
                logger.warning(f"wikipedia: not found: {title} ({lang})")
                continue
            article["fetched_at"] = datetime.now(UTC).isoformat()
            rows.append(article)

    write_jsonl(
        source="wikidata_wikipedia",
        entity="wikipedia_articles",
        rows=rows,
        source_url="https://en.wikipedia.org/wiki/The_Legend_of_Zelda:_Ocarina_of_Time",
        **SOURCE_LICENSES["wikipedia"],
    )
    return len(rows)
