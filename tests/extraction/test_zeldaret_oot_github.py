from ocarina_nexus.extraction import landing_writer
from ocarina_nexus.extraction.sources import zeldaret_oot_github


def test_extract_fetches_root_tables_and_sfx_subdir(tmp_path, monkeypatch):
    monkeypatch.setattr(landing_writer, "LANDING_LOCAL_DIR", tmp_path)
    monkeypatch.setattr(
        zeldaret_oot_github,
        "get_file_text",
        lambda owner, repo, path, ref="main": f"// content of {path}",
    )
    monkeypatch.setattr(
        zeldaret_oot_github,
        "list_dir",
        lambda owner, repo, path, ref="main": [
            {"name": "enemybank_table.h", "path": f"{path}/enemybank_table.h", "type": "file"},
            {"name": "some_subdir", "path": f"{path}/some_subdir", "type": "dir"},
        ],
    )

    total = zeldaret_oot_github.extract()

    # 8 root files + 1 sfx file (the subdir entry is skipped, not a file)
    assert total == len(zeldaret_oot_github._ROOT_FILES) + 1

    out_dir = tmp_path / "technical" / "zeldaret_oot_tables"
    part_files = list(out_dir.glob("*/part-0000.jsonl"))
    assert len(part_files) == 1

    import json

    rows = [json.loads(line) for line in part_files[0].read_text().splitlines()]
    filenames = {r["file"] for r in rows}
    assert "actor_table.h" in filenames
    assert "enemybank_table.h" in filenames
    assert all(r["raw_text"].startswith("// content of") for r in rows)
