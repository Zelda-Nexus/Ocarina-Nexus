from ocarina_nexus.extraction import landing_writer
from ocarina_nexus.extraction.sources import zeldawiki_pages

FAKE_PAGE = {
    "title": "Saria",
    "html": '<div class="mw-parser-output"><p>Saria is a Kokiri.</p></div>',
    "wikitext": "'''Saria''' is a [[Kokiri]].",
    "categories": ["Characters_in_Ocarina_of_Time", "Kokiri"],
    "pageid": 2126,
    "lastrevid": 1383825,
    "displaytitle": "Saria",
    "hidden_categories": [],
    "links": ["Kokiri", "Kokiri Forest"],
    "images": ["Saria.png"],
    "templates": ["Infobox"],
    "external_links": [],
}


def test_extract_writes_one_row_per_page(tmp_path, monkeypatch):
    monkeypatch.setattr(landing_writer, "LANDING_LOCAL_DIR", tmp_path)
    monkeypatch.setattr(
        zeldawiki_pages,
        "get_category_members",
        lambda category: [{"title": "Saria"}],
    )
    monkeypatch.setattr(zeldawiki_pages, "get_page_data", lambda title, full=False: FAKE_PAGE)
    monkeypatch.setattr(zeldawiki_pages, "get_page_touched", lambda title: "2026-01-01T00:00:00Z")

    total = zeldawiki_pages.extract(categories={"Characters in Ocarina of Time": "characters"})

    assert total == 1
    out_dir = tmp_path / "zeldawiki" / "characters"
    part_files = list(out_dir.glob("*/part-0000.jsonl"))
    assert len(part_files) == 1

    import json

    row = json.loads(part_files[0].read_text().splitlines()[0])
    assert row["pageid"] == 2126
    assert row["title"] == "Saria"
    assert row["entity_types"] == ["characters"]
    assert row["lastrevid"] == 1383825
    assert row["touched"] == "2026-01-01T00:00:00Z"
    assert "Saria is a Kokiri." in row["plaintext"]
    assert row["source"] == "zeldawiki"


def test_extract_skips_pages_that_fail_to_fetch(tmp_path, monkeypatch):
    monkeypatch.setattr(landing_writer, "LANDING_LOCAL_DIR", tmp_path)
    monkeypatch.setattr(
        zeldawiki_pages,
        "get_category_members",
        lambda category: [{"title": "Nonexistent Page"}],
    )
    monkeypatch.setattr(zeldawiki_pages, "get_page_data", lambda title, full=False: None)
    monkeypatch.setattr(zeldawiki_pages, "get_page_touched", lambda title: None)

    total = zeldawiki_pages.extract(categories={"Characters in Ocarina of Time": "characters"})

    assert total == 0


def test_extract_respects_page_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(landing_writer, "LANDING_LOCAL_DIR", tmp_path)
    monkeypatch.setattr(
        zeldawiki_pages,
        "get_category_members",
        lambda category: [{"title": f"Page {i}"} for i in range(10)],
    )
    monkeypatch.setattr(zeldawiki_pages, "get_page_data", lambda title, full=False: FAKE_PAGE)
    monkeypatch.setattr(zeldawiki_pages, "get_page_touched", lambda title: None)

    total = zeldawiki_pages.extract(
        categories={"Characters in Ocarina of Time": "characters"}, page_limit=3
    )

    assert total == 3
