from ocarina_nexus.extraction import cli


def test_source_registry_has_all_planned_sources():
    expected = {
        "zeldawiki_pages",
        "zeldawiki_cargo",
        "wikidata",
        "wikipedia",
        "oot_randomizer",
        "zeldaret_oot",
        "game_text",
        "speedrun_com",
    }
    assert set(cli.SOURCE_REGISTRY.keys()) == expected


def test_main_runs_selected_source_and_returns_zero_on_success(monkeypatch):
    calls = []
    monkeypatch.setitem(cli.SOURCE_REGISTRY, "wikidata", lambda: calls.append("wikidata") or 5)

    exit_code = cli.main(["--source", "wikidata"])

    assert exit_code == 0
    assert calls == ["wikidata"]


def test_main_returns_one_when_a_source_raises(monkeypatch):
    def boom():
        raise RuntimeError("network exploded")

    monkeypatch.setitem(cli.SOURCE_REGISTRY, "wikidata", boom)

    exit_code = cli.main(["--source", "wikidata"])

    assert exit_code == 1


def test_main_all_runs_every_registered_source(monkeypatch):
    calls = []
    for name in list(cli.SOURCE_REGISTRY.keys()):
        monkeypatch.setitem(cli.SOURCE_REGISTRY, name, lambda name=name: calls.append(name) or 1)

    exit_code = cli.main(["--source", "all"])

    assert exit_code == 0
    assert set(calls) == set(cli.SOURCE_REGISTRY.keys())
