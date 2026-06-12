# Ocarina Nexus

A structured data pipeline for *The Legend of Zelda: Ocarina of Time* — scraping, normalizing, and storing game data (characters, items, locations, quests) into a queryable local database.

**Long-term goal:** build a foundation for semantic search, narrative AI reasoning, and Graph Neural Network research on the game's story structure.

---

## Architecture

Data flows through three immutable layers (medallion pattern):

```
Zelda Wiki (MediaWiki API)
        │
        ▼
   [ BRONZE ]   Raw JSON — one file per wiki page        data/bronze/
        │
        ▼
   [ SILVER ]   Typed, normalized Parquet                data/silver/
        │
        ▼
   [  GOLD  ]   Analytical tables in DuckDB              data/gold/
```

If a transformation bug is found in Silver, only that step is replayed — no re-scraping needed.

---

## Project structure

```
src/ocarina_nexus/
├── config.py                   # Single source of truth for all paths and settings
├── models/
│   └── entities.py             # Pydantic schemas: RawCharacter, Character, enums
├── utils/
│   ├── wiki_api.py             # MediaWiki API client (pagination + retries)
│   ├── infobox_parser.py       # Portable Infobox HTML extractor
│   └── logging.py              # Loguru setup
└── ingestion/
    ├── scraper_characters.py   # Bronze: fetch and store raw wiki pages
    ├── transform_characters.py # Silver: normalize races, roles, timelines
    └── load_duckdb.py          # Gold: load Parquet into DuckDB + create views

scripts/
└── run_pipeline.py             # Entry point — orchestrates all three steps

data/                           # Generated — not committed to git
├── bronze/characters/          # One JSON file per wiki page
├── silver/characters/          # characters.parquet
└── gold/
    └── ocarina_nexus.duckdb
```

---

## Contributing

Contributions are welcome, especially as the project grows beyond Phase 1.

**Good first areas:**
- Adding normalizers for missing fields in Silver (roles, timeline, family links)
- Writing `scripts/run_pipeline.py` (the orchestration entry point)
- Adding pytest coverage for `infobox_parser.py` and `entities.py`
- Opening issues to discuss Phase 2 schema design (knowledge graph)

**How to contribute:**
1. Fork the repository and create a branch from `main`
2. Install dependencies with `uv sync`
3. Make your changes — keep each PR focused on a single concern
4. Open a pull request with a short description of what and why

If you're unsure whether something fits the project scope, open an issue first.

You can follow the project's progress on the [Trello board]() (Soon Available).

---

## Data sourcing

Data is fetched from [Zelda Wiki](https://zeldawiki.wiki) via its official MediaWiki API (`/w/api.php`). A configurable delay is enforced between requests and a `User-Agent` header identifies the project. Raw scraped data is not redistributed in this repository.
