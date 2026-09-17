# Ocarina Nexus

A Databricks lakehouse for *The Legend of Zelda: Ocarina of Time* — ingesting, normalizing, and modeling game data (characters, items, locations, quests) into governed Delta tables on Unity Catalog.

**Long-term goal:** build a foundation for semantic search, narrative AI reasoning, and Graph Neural Network research on the game's story structure.

---

## Architecture

The target platform is a **Databricks lakehouse** on Unity Catalog. Everything —
catalogs, schemas, volumes, jobs — is declared as code and deployed through a
Databricks Asset Bundle; nothing is created by hand in the UI.

```
Zelda Wiki · speedrun.com · Wikidata/Wikipedia · zeldaret/oot (decomp)
OoT-Randomizer (world logic) · CloudModding (game text)
        │
        │  GitHub Actions — Python extraction (src/ocarina_nexus/extraction/), raw JSONL
        ▼
  UC Volume  /Volumes/<catalog>/bronze/landing/<source>/<entity>/ingest_date=YYYY-MM-DD/
        │
        │  Auto Loader, Scala (notebooks/bronze/)
        ▼
   [ BRONZE ]   Faithful copy of the source, no business rules      <catalog>.bronze
        │
        │  typing, deduplication, historization (MERGE / SCD2), Scala (notebooks/silver/)
        ▼
   [ SILVER ]   Typed, deduplicated, trustworthy data               <catalog>.silver
        │
        │  dimensional modeling + entity-relation fusion, Scala (notebooks/gold/)
        ▼
   [  GOLD  ]   Star schema, ready for consumption                  <catalog>.gold
        │
        │  GraphFrames (notebooks/graph/) — nodes/edges from fact_entity_relation
        ▼
   [ GRAPH  ]   Knowledge graph — PageRank, connected components    <catalog>.gold (graph_*)

   [  OPS   ]   Quality checks, audit, pipeline runs                <catalog>.ops
```

Extraction (Python, `httpx`) and Silver/Gold/graph transformations (Scala,
Spark) are a deliberate split: extraction is I/O-bound scraping against
external APIs, transformation is Spark compute — see
[ADR 0002](docs/0002-scala-pour-les-transformations.md) for why the split
lands where it does, and [ADR 0003](docs/0003-graphframes-pour-le-graphe-de-connaissances.md)
for why the knowledge graph is GraphFrames-on-Delta rather than a separate
graph database.

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
    ├── smoke_test.job.yml        # Proves the platform is wired end to end
    ├── bronze_ingestion.job.yml  # Auto Loader, Scala
    ├── silver_transform.job.yml  # Typing/dedup/SCD2, Scala
    ├── ops_quality.job.yml       # Quality checks, Scala
    ├── gold_transform.job.yml    # Dimensional model + entity-relation fusion, Scala
    └── graph_build.job.yml       # GraphFrames nodes/edges + PageRank, Scala

00_bootstrap.sql                # One-off: catalogs, schemas, landing volume in UC
00_smoke_test.py                # Notebook — proves the platform is wired end to end

notebooks/
├── bronze/    # Auto Loader ingestion, one notebook group per source family
├── silver/    # Typing, dedup, SCD2, regex/JSON parsing of raw technical tables
├── gold/      # Star schema + fact_entity_relation (the graph's raw material)
├── graph/     # GraphFrames: node/edge materialization, PageRank, connected components
└── ops/       # Quality checks

src/ocarina_nexus/extraction/   # Python extraction layer — one module per source
├── landing_writer.py           # Writes JSONL to the local landing mirror (+ manifest)
├── github_client.py            # GitHub contents API wrapper (GITHUB_TOKEN-aware)
├── sources/                    # zeldawiki_pages, zeldawiki_cargo, wikidata, wikipedia,
│                                # oot_randomizer_github, zeldaret_oot_github, game_text, speedrun_com
└── cli.py                      # `python -m ocarina_nexus.extraction.cli --source <name|all>`

.github/workflows/
├── databricks.yml              # CI: validate on PR, deploy + smoke test on main
└── extraction.yml              # Weekly: run extraction, upload to the landing volume

docs/
├── 0001-delta-lake-comme-format-de-table.md
├── 0002-scala-pour-les-transformations.md
└── 0003-graphframes-pour-le-graphe-de-connaissances.md
```

Rule of the project: every job, pipeline and table is described here or under
`resources/` — nothing is ever created by hand in the Databricks UI.

### Legacy prototype

`src/ocarina_nexus/ingestion/scraper_characters.py` and
`src/ocarina_nexus/ingestion/load_duckdb.py` hold the original local
pipeline (httpx scraping straight to DuckDB, characters only) and are kept
as a **historical reference** — they're what validated the extraction logic
before it was generalized. `utils/wiki_api.py` and `utils/infobox_parser.py`
are no longer just prototype code: they're reused as-is by
`src/ocarina_nexus/extraction/sources/zeldawiki_pages.py`, the real
extraction step that writes JSONL to the landing volume.

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
