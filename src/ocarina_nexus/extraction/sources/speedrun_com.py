"""
speedrun.com API v1 — categories, levels, variables, leaderboards for OoT
(game id `j1l9qz1g`). CC BY-NC 4.0 — non-commercial only, `redistribution_ok`
is set accordingly (see config.SOURCE_LICENSES). See inventaire §4.
"""

from datetime import UTC, datetime

import httpx
from loguru import logger

from ocarina_nexus.config import SCRAPING_DELAY, SOURCE_LICENSES, USER_AGENT
from ocarina_nexus.extraction.landing_writer import write_jsonl
from ocarina_nexus.extraction.rate_limit import RateLimiter

BASE_URL = "https://www.speedrun.com/api/v1"
GAME_ABBREVIATION = "oot"

# speedrun.com allows 100 req/min/IP; keep a safety margin.
_limiter = RateLimiter(max(SCRAPING_DELAY, 0.7))


def _get(path: str, params: dict | None = None) -> dict | None:
    _limiter.wait()
    try:
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30.0) as client:
            response = client.get(f"{BASE_URL}{path}", params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as e:
        logger.warning(f"speedrun.com request failed for {path}: {e}")
        return None


def extract(top: int = 100) -> int:
    games = _get("/games", {"abbreviation": GAME_ABBREVIATION})
    if not games or not games.get("data"):
        logger.error("speedrun.com: could not resolve OoT game id")
        return 0
    game_id = games["data"][0]["id"]

    categories = (_get(f"/games/{game_id}/categories") or {}).get("data", [])
    levels = (_get(f"/games/{game_id}/levels") or {}).get("data", [])
    variables = (_get(f"/games/{game_id}/variables") or {}).get("data", [])

    now = datetime.now(UTC).isoformat()
    fetched_at_url = f"https://www.speedrun.com/api/v1/games/{game_id}"

    write_jsonl(
        source="speedrun_com",
        entity="categories",
        rows=[{**c, "fetched_at": now} for c in categories],
        source_url=f"{fetched_at_url}/categories",
        **SOURCE_LICENSES["speedrun_com"],
    )
    write_jsonl(
        source="speedrun_com",
        entity="levels",
        rows=[{**l, "fetched_at": now} for l in levels],
        source_url=f"{fetched_at_url}/levels",
        **SOURCE_LICENSES["speedrun_com"],
    )
    write_jsonl(
        source="speedrun_com",
        entity="variables",
        rows=[{**v, "fetched_at": now} for v in variables],
        source_url=f"{fetched_at_url}/variables",
        **SOURCE_LICENSES["speedrun_com"],
    )

    leaderboard_rows = []
    for category in categories:
        if category["type"] == "per-game":
            board = _get(f"/leaderboards/{game_id}/category/{category['id']}", {"top": top})
            if board and board.get("data"):
                leaderboard_rows.append(
                    {
                        "category_id": category["id"],
                        "category_name": category["name"],
                        "level_id": None,
                        "runs": board["data"].get("runs", []),
                        "fetched_at": now,
                    }
                )
        elif category["type"] == "per-level":
            for level in levels:
                board = _get(
                    f"/leaderboards/{game_id}/level/{level['id']}/{category['id']}", {"top": top}
                )
                if board and board.get("data"):
                    leaderboard_rows.append(
                        {
                            "category_id": category["id"],
                            "category_name": category["name"],
                            "level_id": level["id"],
                            "level_name": level["name"],
                            "runs": board["data"].get("runs", []),
                            "fetched_at": now,
                        }
                    )

    write_jsonl(
        source="speedrun_com",
        entity="leaderboards",
        rows=leaderboard_rows,
        source_url=f"{fetched_at_url}/records",
        **SOURCE_LICENSES["speedrun_com"],
    )

    return len(categories) + len(levels) + len(variables) + len(leaderboard_rows)
