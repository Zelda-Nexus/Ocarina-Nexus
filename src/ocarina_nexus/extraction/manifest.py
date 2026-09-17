"""
Per-directory extraction manifest.

Written next to every batch of JSONL files landed by `landing_writer.write_jsonl`.
Keeps the provenance trail (source URL, license, fetch time) at the file-system
level, one level below the Bronze `_source_file` column that will reference it.
"""

from datetime import UTC, datetime

from pydantic import BaseModel


class ExtractionManifest(BaseModel):
    source: str
    entity: str
    source_url: str
    license: str
    redistribution_ok: bool
    fetched_at: str
    row_count: int
    files: list[str]

    @classmethod
    def build(
        cls,
        source: str,
        entity: str,
        source_url: str,
        license: str,
        redistribution_ok: bool,
        row_count: int,
        files: list[str],
    ) -> "ExtractionManifest":
        return cls(
            source=source,
            entity=entity,
            source_url=source_url,
            license=license,
            redistribution_ok=redistribution_ok,
            fetched_at=datetime.now(UTC).isoformat(),
            row_count=row_count,
            files=files,
        )
