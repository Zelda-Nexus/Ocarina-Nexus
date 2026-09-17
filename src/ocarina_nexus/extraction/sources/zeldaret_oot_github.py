"""
zeldaret/oot (github.com/zeldaret/oot, `main` branch) — decompilation engine
tables: every actor, scene, entrance, object, sequence and SFX bank entry in
the retail game. No LICENSE file upstream (reverse-engineered facts, not
copyrightable expression) — see inventaire §3.

These are C macro tables (`DEFINE_ACTOR(...)`, `DEFINE_SCENE(...)`, ...),
fragile to parse by regex. Captured here as raw file text only; the regex
parsing into rows happens in Silver (Risk 4 in the plan) so a parser bug
never requires re-fetching from GitHub — Bronze stays the replay point.
"""

from datetime import UTC, datetime

from ocarina_nexus.config import SOURCE_LICENSES
from ocarina_nexus.extraction.github_client import get_file_text, list_dir
from ocarina_nexus.extraction.landing_writer import write_jsonl

OWNER = "zeldaret"
REPO = "oot"
REF = "main"

_TABLES_DIR = "include/tables"
_ROOT_FILES = [
    "actor_table.h",
    "scene_table.h",
    "entrance_table.h",
    "object_table.h",
    "sequence_table.h",
    "effect_ss_table.h",
    "gamestate_table.h",
    "dmadata_table.h",
]
_SFX_DIR = f"{_TABLES_DIR}/sfx"


def _fetch_files(paths: list[str]) -> list[dict]:
    rows = []
    for path in paths:
        text = get_file_text(OWNER, REPO, path, ref=REF)
        rows.append(
            {
                "file": path.rsplit("/", 1)[-1],
                "path": path,
                "raw_text": text,
                "n_lines": text.count("\n") + 1,
                "fetched_at": datetime.now(UTC).isoformat(),
            }
        )
    return rows


def extract() -> int:
    root_paths = [f"{_TABLES_DIR}/{name}" for name in _ROOT_FILES]
    sfx_entries = list_dir(OWNER, REPO, _SFX_DIR, ref=REF)
    sfx_paths = [e["path"] for e in sfx_entries if e["type"] == "file"]

    rows = _fetch_files(root_paths) + _fetch_files(sfx_paths)

    write_jsonl(
        source="technical",
        entity="zeldaret_oot_tables",
        rows=rows,
        source_url=f"https://github.com/{OWNER}/{REPO}/tree/{REF}/{_TABLES_DIR}",
        **SOURCE_LICENSES["zeldaret_oot"],
    )
    return len(rows)
