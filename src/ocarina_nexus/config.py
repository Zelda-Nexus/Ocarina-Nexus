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


BRONZE_DIR   = _resolve("BRONZE_DIR",  "data/bronze")
SILVER_DIR   = _resolve("SILVER_DIR",  "data/silver")
GOLD_DIR     = _resolve("GOLD_DIR",    "data/gold")
DUCKDB_PATH  = _resolve("DUCKDB_PATH", "data/gold/ocarina_nexus.duckdb")

LOG_DIR  = PROJECT_ROOT / "logs"
LOG_FILE = LOG_DIR / "ocarina_nexus.log"

USER_AGENT           = os.getenv("USER_AGENT", "OcarinaNexus/0.1 (open source research project)")
SCRAPING_DELAY       = float(os.getenv("SCRAPING_DELAY", "1.0"))
SCRAPING_MAX_RETRIES = int(os.getenv("SCRAPING_MAX_RETRIES", "3"))
DATA_BASE_URL        = os.getenv("DATA_BASE_URL", "https://zeldawiki.wiki")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


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
