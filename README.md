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
        │  Auto Loader, PySpark (notebooks/bronze/)
        ▼
   [ BRONZE ]   Faithful copy of the source, no business rules      <catalog>.bronze
        │
        │  typing, deduplication, historization (MERGE / SCD2), PySpark (notebooks/silver/)
        ▼
   [ SILVER ]   Typed, deduplicated, trustworthy data               <catalog>.silver
        │
        │  dimensional modeling + entity-relation fusion, PySpark (notebooks/gold/)
        ▼
   [  GOLD  ]   Star schema, ready for consumption                  <catalog>.gold
        │
        │  PySpark, hand-rolled (notebooks/graph/) — nodes/edges from fact_entity_relation
        ▼
   [ GRAPH  ]   Knowledge graph — PageRank, connected components    <catalog>.gold (graph_*)

   [  OPS   ]   Quality checks, audit, pipeline runs                <catalog>.ops

   [  APP   ]   Databricks App (app/) — live graph stats + a         served over HTTPS,
                read-only SQL console over gold/silver               UC-permissioned
```

Extraction (Python, `httpx`) and Silver/Gold/graph transformations (PySpark)
are a deliberate split: extraction is I/O-bound scraping against external
APIs, transformation is Spark compute. Both layers being Python is itself
a platform constraint, not the original plan — see
[ADR 0004](docs/0004-pyspark-serverless-remplace-scala-et-graphframes.md):
the target workspace's serverless-only compute doesn't support Scala or
GraphFrames's Maven dependency, which is what [ADR 0002](docs/0002-scala-pour-les-transformations.md)
and [ADR 0003](docs/0003-graphframes-pour-le-graphe-de-connaissances.md)
had originally chosen, before either notebook had actually been run on the
real workspace. PageRank and connected components are now a small
hand-rolled PySpark implementation instead of GraphFrames.

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

### The lakehouse App

`app/` is a small [Databricks App](https://docs.databricks.com/en/dev-tools/databricks-apps/index.html)
(FastAPI, no JS build step) with three pages:

- `/` — live graph stats computed straight from `gold.graph_nodes` /
  `gold.graph_edges` / `gold.fact_entity_relation`.
- `/lakehouse` — a catalog sidebar (`gold`/`silver` tables, click one to
  query it or open its column list — types, `NOT NULL`, declared
  `PRIMARY KEY`/`FOREIGN KEY`, read from `information_schema`, see
  `app/catalog.py`) next to a read-only SQL console (`SELECT`/`WITH` only,
  one statement, capped at 500 rows).
- `/pipelines` — the 6 bundle jobs with their latest run status and a
  "Lancer" button (`app/jobs.py`, Jobs API `run_now`/`list_runs`).

It's declared as a bundle resource (`resources/apps/lakehouse_app.yml`) and
deployed like anything else:

```bash
databricks bundle deploy --target dev
databricks bundle run lakehouse_app --target dev
```

Two manual grants after the first deploy, same spirit as `00_bootstrap.sql`
(and already wired into `resources/jobs/*.job.yml`'s `permissions:` block for
the second one — nothing to redo there on a redeploy):

1. **Unity Catalog** — the App's service principal needs `USE CATALOG` /
   `USE SCHEMA` / `SELECT` on `gold` and `silver` (never `bronze`/`ops` —
   that's the real read-only boundary, not the app-level keyword filter in
   `app/db.py`, which only stops obviously destructive SQL). Run once, with
   the service principal's application id from
   `databricks apps get ocarina-lakehouse`:

   ```sql
   GRANT USE CATALOG ON CATALOG ocarina_dev TO `<app-service-principal-id>`;
   GRANT USE SCHEMA, SELECT ON SCHEMA ocarina_dev.gold TO `<app-service-principal-id>`;
   GRANT USE SCHEMA, SELECT ON SCHEMA ocarina_dev.silver TO `<app-service-principal-id>`;
   ```

2. **Jobs** — `/pipelines` needs the App's service principal to have
   `CAN_MANAGE_RUN` (monitor + trigger, never edit the job definition) on
   each of the 6 jobs. Declared as code in every `resources/jobs/*.job.yml`
   via `${var.app_service_principal_id}` (set in `databricks.yml`) — update
   that variable if the App is ever recreated (its service principal id
   changes) and redeploy.

### The interactive map (`site/`)

`site/` also has a real, data-backed interactive map of Hyrule
(`.hymap` component, `site/js/hyrule-map.js`) — one pin per row of
`gold.map_location`, each opening an era-aware
[noclip.website](https://noclip.website) embed of the real decomp scene
(N64 `zelview` / 3DS `oot3d`). `notebooks/gold/04_gold_map_location.py`
joins `gold.dim_location` (title/summary/region) against two hand-maintained
reference tables that can't be derived from any upstream source — a drawn
map has no in-game coordinate system, and the decomp's scene short names
(`spot00`, `ydan`, `Bmori1`, ...) aren't in any scraped source either:

- `gold.ref_map_pin` — pin position (x/y, % of the 1000×640 SVG viewBox) and
  which era(s) a location is visitable in.
- `gold.ref_noclip_scene` — decomp scene key -> noclip scene id, per
  platform.

Because `site/` is a fully static folder (no server, no build step),
`site/data/locations.json` is a **committed, regeneratable export** rather
than something the site fetches live from the warehouse:

```bash
databricks bundle run gold_transform --target dev   # refreshes gold.map_location
uv run python scripts/export_site_locations.py       # -> site/data/locations.json
```

`scripts/gen_hyrule_map.py` regenerates the SVG background art itself
(fractal coastlines, same seed = same map) — unrelated to location data, run
it only to redraw the map.

---

## Project structure

```
databricks.yml                  # Asset Bundle entry point — variables, dev/prod targets
resources/
├── jobs/
│   ├── smoke_test.job.yml        # Proves the platform is wired end to end
│   ├── bronze_ingestion.job.yml  # Auto Loader, PySpark
│   ├── silver_transform.job.yml  # Typing/dedup/SCD2, PySpark
│   ├── ops_quality.job.yml       # Quality checks, PySpark
│   ├── gold_transform.job.yml    # Dimensional model + entity-relation fusion, PySpark
│   └── graph_build.job.yml       # Node/edge materialization + hand-rolled PageRank, PySpark
└── apps/
    └── lakehouse_app.yml         # Databricks App resource — see app/

00_bootstrap.sql                # One-off: catalogs, schemas, landing volume in UC
00_smoke_test.py                # Notebook — proves the platform is wired end to end

notebooks/
├── bronze/    # Auto Loader ingestion, one notebook group per source family
├── silver/    # Typing, dedup, SCD2, regex/JSON parsing of raw technical tables
├── gold/      # Star schema + fact_entity_relation (the graph's raw material)
├── graph/     # Node/edge materialization, hand-rolled PageRank + connected components
└── ops/       # Quality checks

app/                             # Databricks App — FastAPI, no JS build step
├── app.yaml                       # App runtime manifest (command, env)
├── app.py                         # Routes: / (stats), /lakehouse (SQL console), /api/*
├── db.py                          # Statement Execution API — read-only query guard
├── templates/                     # index.html, lakehouse.html
└── static/                        # style.css, stats.js, lakehouse.js

src/ocarina_nexus/extraction/   # Python extraction layer — one module per source
├── landing_writer.py           # Writes JSONL to the local landing mirror (+ manifest)
├── github_client.py            # GitHub contents API wrapper (GITHUB_TOKEN-aware)
├── sources/                    # zeldawiki_pages, zeldawiki_cargo, wikidata, wikipedia,
│                                # oot_randomizer_github, zeldaret_oot_github, game_text, speedrun_com
└── cli.py                      # `python -m ocarina_nexus.extraction.cli --source <name|all>`

scripts/
├── export_site_locations.py    # gold.map_location -> site/data/locations.json
└── gen_hyrule_map.py           # regenerates the map's SVG background art

.github/workflows/
├── databricks.yml              # CI: validate on PR, deploy + smoke test on main
└── extraction.yml              # Weekly: run extraction, upload to the landing volume

docs/
├── 0001-delta-lake-comme-format-de-table.md
├── 0002-scala-pour-les-transformations.md               # remplace par 0004
├── 0003-graphframes-pour-le-graphe-de-connaissances.md  # amende par 0004
└── 0004-pyspark-serverless-remplace-scala-et-graphframes.md
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
