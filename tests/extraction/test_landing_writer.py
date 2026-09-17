import json

from ocarina_nexus.extraction import landing_writer


def test_write_jsonl_creates_partition_and_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(landing_writer, "LANDING_LOCAL_DIR", tmp_path)

    rows = [{"a": 1}, {"a": 2}, {"a": 3}]
    partition_dir = landing_writer.write_jsonl(
        source="test_source",
        entity="test_entity",
        rows=rows,
        source_url="https://example.com",
        license="CC0",
        redistribution_ok=True,
    )

    assert partition_dir.exists()
    assert partition_dir.parent.name == "test_entity"
    assert partition_dir.parent.parent.name == "test_source"
    assert partition_dir.name.startswith("ingest_date=")

    part_files = sorted(partition_dir.glob("part-*.jsonl"))
    assert len(part_files) == 1
    written_rows = [json.loads(line) for line in part_files[0].read_text().splitlines()]
    assert written_rows == rows

    manifest = json.loads((partition_dir / "_manifest.json").read_text())
    assert manifest["source"] == "test_source"
    assert manifest["entity"] == "test_entity"
    assert manifest["source_url"] == "https://example.com"
    assert manifest["license"] == "CC0"
    assert manifest["redistribution_ok"] is True
    assert manifest["row_count"] == 3
    assert manifest["files"] == ["part-0000.jsonl"]


def test_write_jsonl_splits_large_batches_into_multiple_parts(tmp_path, monkeypatch):
    monkeypatch.setattr(landing_writer, "LANDING_LOCAL_DIR", tmp_path)
    monkeypatch.setattr(landing_writer, "_MAX_ROWS_PER_FILE", 2)

    rows = [{"i": i} for i in range(5)]
    partition_dir = landing_writer.write_jsonl(
        source="s", entity="e", rows=rows, source_url="u", license="l", redistribution_ok=False
    )

    part_files = sorted(partition_dir.glob("part-*.jsonl"))
    assert len(part_files) == 3  # 2 + 2 + 1
    manifest = json.loads((partition_dir / "_manifest.json").read_text())
    assert manifest["row_count"] == 5
    assert len(manifest["files"]) == 3


def test_write_jsonl_empty_rows_still_writes_a_visible_part_file(tmp_path, monkeypatch):
    monkeypatch.setattr(landing_writer, "LANDING_LOCAL_DIR", tmp_path)

    partition_dir = landing_writer.write_jsonl(
        source="s", entity="e", rows=[], source_url="u", license="l", redistribution_ok=False
    )

    part_files = list(partition_dir.glob("part-*.jsonl"))
    assert len(part_files) == 1
    assert part_files[0].read_text() == ""
    manifest = json.loads((partition_dir / "_manifest.json").read_text())
    assert manifest["row_count"] == 0
