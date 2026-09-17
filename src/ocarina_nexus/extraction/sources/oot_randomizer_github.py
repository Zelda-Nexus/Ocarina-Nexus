"""
OoT-Randomizer (github.com/OoTRandomizer/OoT-Randomizer, `Dev` branch) — the
world logic graph: locations, items, regions, region exits with access-rule
expressions. MIT license. See inventaire §3 "OoT-Randomizer".

`data/World/*.json` are not strict JSON: they carry `#` comments (both
whole-line and trailing after a value) and some string values wrap across
physical lines with a literal newline inside the quotes (rule expressions
like `"Deku Baba Nuts": "\n    is_adult or ..."`, confirmed by fetching a
real file during development — see `_clean_pseudo_json`). A plain
`json.loads` after only stripping whole-line comments fails on every single
file; this cleaner handles both cases in one pass, tracking string state so
`#` inside a string is never mistaken for a comment. `LocationList.py` /
`ItemList.py` / `HintList.py` are executable Python modules, not data files:
they are captured as raw text rows here (Risk 3 in the plan) and structured
later in Silver via a dedicated parser, so a bad guess at parsing them never
costs a re-scrape.
"""

import json
import re
from datetime import UTC, datetime

from loguru import logger

from ocarina_nexus.config import SOURCE_LICENSES
from ocarina_nexus.extraction.github_client import get_file_text, list_dir
from ocarina_nexus.extraction.landing_writer import write_jsonl

OWNER = "OoTRandomizer"
REPO = "OoT-Randomizer"
REF = "Dev"

_WORLD_DIR = "data/World"
_RAW_MODULES = ["LocationList.py", "ItemList.py", "HintList.py"]

_TRAILING_COMMA = re.compile(r",(\s*[}\]])")


def _clean_pseudo_json(text: str) -> str:
    """Strips `#` comments (whole-line or inline) outside of string
    literals, and collapses a literal newline inside a string value to a
    single space. Single pass, string-state-aware so `#`/`\\n` inside a
    quoted value is never touched."""
    out: list[str] = []
    in_string = False
    escape = False
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if in_string:
            if escape:
                out.append(c)
                escape = False
            elif c == "\\":
                out.append(c)
                escape = True
            elif c == '"':
                out.append(c)
                in_string = False
            elif c in "\n\r":
                while i + 1 < n and text[i + 1] in " \t\n\r":
                    i += 1
                out.append(" ")
            else:
                out.append(c)
        else:
            if c == '"':
                in_string = True
                out.append(c)
            elif c == "#":
                while i < n and text[i] not in "\n\r":
                    i += 1
                continue
            else:
                out.append(c)
        i += 1
    return _TRAILING_COMMA.sub(r"\1", "".join(out))


def _extract_world_json() -> int:
    entries = list_dir(OWNER, REPO, _WORLD_DIR, ref=REF)
    rows = []

    for entry in entries:
        if entry["type"] != "file" or not entry["name"].endswith(".json"):
            continue
        text = get_file_text(OWNER, REPO, entry["path"], ref=REF)
        try:
            parsed = json.loads(_clean_pseudo_json(text))
        except json.JSONDecodeError as e:
            logger.warning(f"oot_randomizer: could not parse {entry['name']} as JSON ({e}); storing raw text")
            rows.append(
                {
                    "file": entry["name"],
                    "parsed": False,
                    "raw_text": text,
                    "fetched_at": datetime.now(UTC).isoformat(),
                }
            )
            continue

        rows.append(
            {
                "file": entry["name"],
                "parsed": True,
                "entries": parsed,
                "fetched_at": datetime.now(UTC).isoformat(),
            }
        )

    write_jsonl(
        source="technical",
        entity="oot_randomizer_world",
        rows=rows,
        source_url=f"https://github.com/{OWNER}/{REPO}/tree/{REF}/{_WORLD_DIR}",
        **SOURCE_LICENSES["oot_randomizer"],
    )
    return len(rows)


def _extract_raw_modules() -> int:
    rows = []
    for filename in _RAW_MODULES:
        text = get_file_text(OWNER, REPO, filename, ref=REF)
        rows.append(
            {
                "file": filename,
                "raw_text": text,
                "fetched_at": datetime.now(UTC).isoformat(),
            }
        )

    write_jsonl(
        source="technical",
        entity="oot_randomizer_modules",
        rows=rows,
        source_url=f"https://github.com/{OWNER}/{REPO}/tree/{REF}",
        **SOURCE_LICENSES["oot_randomizer"],
    )
    return len(rows)


def extract() -> int:
    return _extract_world_json() + _extract_raw_modules()
