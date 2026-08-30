# Ocarina Nexus

A Databricks lakehouse for *The Legend of Zelda: Ocarina of Time* — ingesting, normalizing, and modeling game data (characters, items, locations, quests) into governed Delta tables on Unity Catalog.

**Long-term goal:** build a foundation for semantic search, narrative AI reasoning, and Graph Neural Network research on the game's story structure.

---

## Architecture

The target platform is a **Databricks lakehouse** on Unity Catalog. Everything —
catalogs, schemas, volumes, jobs — is declared as code and deployed through a
Databricks Asset Bundle; nothing is created by hand in the UI.

```
Zelda Wiki (MediaWiki API)   ·   speedrun.com API   ·   future sources
        │
        │  GitHub Actions — extraction, raw JSONL
        ▼
  UC Volume  /Volumes/<catalog>/bronze/landing/<source>/<entity>/ingest_date=YYYY-MM-DD/
        │
        │  Auto Loader (incremental file discovery)
        ▼
   [ BRONZE ]   Faithful copy of the source, no business rules      <catalog>.bronze
        │
        │  typing, deduplication, historization (MERGE / SCD2)
        ▼
   [ SILVER ]   Typed, deduplicated, trustworthy data               <catalog>.silver
        │
        │  dimensional modeling
        ▼
   [  GOLD  ]   Star schema, ready for consumption                  <catalog>.gold

   [  OPS   ]   Quality checks, audit, pipeline runs                <catalog>.ops
```

All tables are **Delta Lake** — ACID transactions, `MERGE INTO`, time travel, and
`CHECK` constraints. See [ADR 0001](docs/0001-delta-lake-comme-format-de-table.md)
for the rationale. Each layer stays replayable: a bug in Silver is fixed by
replaying that step from Bronze, with no re-scraping.

### Environments

Dev and prod are two **catalogs** (`ocarina_dev`, `ocarina_prod`) in a single
Databricks Free Edition workspace. The data separation is real; moving to
separate workspaces later only changes the `host` field in `databricks.yml`.

### Deployment loop

`git push` → GitHub Actions → `databricks bundle validate` on every pull request,
then `deploy` + `run smoke_test` on `main`. Nothing reaches `prod` from a local
machine.

```bash
databricks bundle validate --target dev
databricks bundle deploy   --target dev
databricks bundle run smoke_test --target dev
```

Unity Catalog itself (catalogs, schemas, landing volume) is the one manual step:
run `00_bootstrap.sql` once in the Databricks SQL editor — bundles cannot manage
account-level objects on Free Edition.

---

## Project structure

```
databricks.yml                  # Asset Bundle entry point — variables, dev/prod targets
resources/
└── jobs/
    └── smoke_test.job.yml      # Job definitions (one file per job)

00_bootstrap.sql                # One-off: catalogs, schemas, landing volume in UC
00_smoke_test.py                # Notebook — proves the platform is wired end to end

.github/workflows/
└── databricks.yml              # CI: validate on PR, deploy + smoke test on main

docs/
└── 0001-delta-lake-comme-format-de-table.md   # Architecture decision records
```

Rule of the project: every job, pipeline and table is described here or under
`resources/` — nothing is ever created by hand in the Databricks UI.

### Legacy prototype

`src/ocarina_nexus/` and `scripts/` hold the original local pipeline (httpx
scraping, Parquet, DuckDB). It is kept as a **working prototype** — it is what
validated the extraction logic and the infobox parsing — but it is not the
target platform. The scraping and parsing pieces (`utils/wiki_api.py`,
`utils/infobox_parser.py`) are the parts meant to be carried over into the
extraction step that writes JSONL to the landing volume; the DuckDB loading
step is superseded by the lakehouse layers.

---

## Contributing

Contributions are welcome, especially as the project grows beyond Phase 1.

**Good first areas:**
- Building the extraction step that writes raw JSONL to the landing volume
- Adding Auto Loader ingestion into Bronze for a new source or entity
- Silver normalizers (races, roles, timeline, family links) and `CHECK` constraints
- Data quality and audit tables in the `ops` schema
- Opening issues to discuss Phase 2 schema design (knowledge graph)

**How to contribute:**
1. Fork the repository and create a branch from `main`
2. Install dependencies with `uv sync`
3. Make your changes — keep each PR focused on a single concern
4. Check the bundle still validates: `databricks bundle validate --target dev`
5. Open a pull request with a short description of what and why

If you're unsure whether something fits the project scope, open an issue first.

You can follow the project's progress on the [Trello board]() (Soon Available).

---

## Data sourcing

Data is fetched from [Zelda Wiki](https://zeldawiki.wiki) via its official MediaWiki API (`/w/api.php`). A configurable delay is enforced between requests and a `User-Agent` header identifies the project. Raw scraped data is not redistributed in this repository; it lands in the Unity Catalog volume, never in git.
