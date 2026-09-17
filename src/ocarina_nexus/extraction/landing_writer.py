"""
Writes extracted rows to the local landing mirror, in the exact directory
shape the real Bronze Auto Loader expects on the Unity Catalog volume:

    <source>/<entity>/ingest_date=YYYY-MM-DD/part-0000.jsonl
    <source>/<entity>/ingest_date=YYYY-MM-DD/_manifest.json

`ingest_date` is a partition column (Hive-style `key=value` directory), matching
the convention already fixed in the README:
    /Volumes/<catalog>/bronze/landing/<source>/<entity>/ingest_date=YYYY-MM-DD/

This module never mutates a row's content — it only decides where it lands.
Business rules, typing and deduplication happen downstream, in Silver.
"""

import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from loguru import logger

from ocarina_nexus.config import LANDING_LOCAL_DIR
from ocarina_nexus.extraction.manifest import ExtractionManifest

_MAX_ROWS_PER_FILE = 5000


def write_jsonl(
    source: str,
    entity: str,
    rows: list[dict[str, Any]],
    source_url: str,
    license: str,
    redistribution_ok: bool,
    ingest_date: date | None = None,
) -> Path:
    """
    Writes `rows` as one or more JSONL part-files under the landing mirror,
    plus a sibling `_manifest.json` recording provenance. Returns the
    partition directory written to.

    Each row is serialized as-is (`json.dumps`, no schema enforcement) —
    Bronze is a faithful copy, not a typed table.
    """
    ingest_date = ingest_date or datetime.now(UTC).date()
    partition_dir = LANDING_LOCAL_DIR / source / entity / f"ingest_date={ingest_date.isoformat()}"
    partition_dir.mkdir(parents=True, exist_ok=True)

    files: list[str] = []
    for chunk_index, chunk_start in enumerate(range(0, len(rows), _MAX_ROWS_PER_FILE)):
        chunk = rows[chunk_start : chunk_start + _MAX_ROWS_PER_FILE]
        part_path = partition_dir / f"part-{chunk_index:04d}.jsonl"
        with part_path.open("w", encoding="utf-8") as f:
            for row in chunk:
                f.write(json.dumps(row, ensure_ascii=False, default=str))
                f.write("\n")
        files.append(part_path.name)

    if not files:
        # Still write an empty part file so an empty extraction is visible
        # (not silently indistinguishable from "never ran").
        part_path = partition_dir / "part-0000.jsonl"
        part_path.touch()
        files.append(part_path.name)

    manifest = ExtractionManifest.build(
        source=source,
        entity=entity,
        source_url=source_url,
        license=license,
        redistribution_ok=redistribution_ok,
        row_count=len(rows),
        files=files,
    )
    (partition_dir / "_manifest.json").write_text(
        manifest.model_dump_json(indent=2), encoding="utf-8"
    )

    logger.info(f"[{source}/{entity}] wrote {len(rows)} rows -> {partition_dir}")
    return partition_dir
