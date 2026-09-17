"""
Extraction layer: pulls raw data from external sources and writes it to the
local landing mirror (`./data/landing/...`), in the exact directory shape the
Bronze Auto Loader expects on the real Unity Catalog volume:

    <source>/<entity>/ingest_date=YYYY-MM-DD/part-*.jsonl

Everything here is Python (httpx), reusing `ocarina_nexus.utils.wiki_api` and
`ocarina_nexus.utils.infobox_parser`. No business rules, no typing, no dedup:
that is Silver's job. This layer only fetches and writes what it received.
"""
