"""
Central configuration for the project.

Single source of truth for all data paths and scraping parameters.
No other file in the project should call os.getenv() directly.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# parents[2]: config.py is at src/ocarina_nexus/config.py -> root is 2 levels up
PROJECT_ROOT = Path(__file__).resolve().parents[2]

load_dotenv(PROJECT_ROOT / ".env")


def _resolve(env_var: str, default: str) -> Path:
    raw = os.getenv(env_var, default).lstrip("./")
    return PROJECT_ROOT / raw


BRONZE_DIR = _resolve("BRONZE_DIR", "data/bronze")
SILVER_DIR = _resolve("SILVER_DIR", "data/silver")
GOLD_DIR = _resolve("GOLD_DIR", "data/gold")
DUCKDB_PATH = _resolve("DUCKDB_PATH", "data/gold/ocarina_nexus.duckdb")

# Local mirror of the Bronze landing volume. Same directory shape as
# /Volumes/<catalog>/bronze/landing/<source>/<entity>/ingest_date=YYYY-MM-DD/
# so the extraction output can be uploaded as-is via `databricks fs cp`.
LANDING_LOCAL_DIR = _resolve("LANDING_LOCAL_DIR", "data/landing")

LOG_DIR = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "ocarina_nexus.log"

USER_AGENT = os.getenv("USER_AGENT", "OcarinaNexus/0.1 (open source research project)")
SCRAPING_DELAY = float(os.getenv("SCRAPING_DELAY", "1.0"))
SCRAPING_MAX_RETRIES = int(os.getenv("SCRAPING_MAX_RETRIES", "3"))
DATA_BASE_URL = os.getenv("DATA_BASE_URL", "https://zeldawiki.wiki")

# Optional: raises the GitHub API quota from 60/h (anonymous) to 5000/h.
# In CI, GitHub Actions injects its own ambient token under this same name.
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

# Optional: speedrun.com API reads work anonymously; a key only raises limits.
SPEEDRUN_API_KEY = os.getenv("SPEEDRUN_API_KEY")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Single source of truth for (license, redistribution_ok) per extraction
# source. `redistribution_ok=False` means: fine to ingest and index
# internally (Silver/Gold/RAG), never to republish verbatim on the public
# site. See data/Inventaire des sources de données Ocarina of Time.md §(d).
SOURCE_LICENSES: dict[str, dict[str, "bool | str"]] = {
    "zeldawiki": {"license": "CC BY-NC-SA 3.0", "redistribution_ok": False},
    "wikidata": {"license": "CC0", "redistribution_ok": True},
    "wikipedia": {"license": "CC BY-SA 4.0", "redistribution_ok": True},
    "oot_randomizer": {"license": "MIT", "redistribution_ok": True},
    "zeldaret_oot": {"license": "unspecified (reverse-engineered facts)", "redistribution_ok": False},
    "game_text": {"license": "unspecified-fan-content (© Nintendo text)", "redistribution_ok": False},
    "speedrun_com": {"license": "CC BY-NC 4.0", "redistribution_ok": False},
}


def get_bronze_path(entity: str) -> Path:
    path = BRONZE_DIR / entity
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_silver_path(entity: str) -> Path:
    path = SILVER_DIR / entity
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_gold_path() -> Path:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    return GOLD_DIR
