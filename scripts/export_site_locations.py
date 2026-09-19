"""
Regenerates site/data/locations.json from gold.map_location.

site/ is a fully static folder (no build step, no server) so this runs
locally, on demand, rather than as a Databricks job writing to a UC Volume:

    uv run python scripts/export_site_locations.py

Needs a `databricks auth login` session (uses the CLI's own credentials via
databricks-sdk's default auth, same as the Databricks CLI).
"""

import json
import sys
from pathlib import Path

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = PROJECT_ROOT / "site" / "data" / "locations.json"

CATALOG = "ocarina_dev"
WAREHOUSE_ID = "49f98d366056a749"

QUERY = """
SELECT entity_id, title, region, x, y, summary, scenes
FROM gold.map_location
ORDER BY entity_id
"""


def fetch_locations() -> list[dict]:
    client = WorkspaceClient(profile="ocarina")
    response = client.statement_execution.execute_statement(
        warehouse_id=WAREHOUSE_ID,
        statement=QUERY,
        catalog=CATALOG,
        wait_timeout="30s",
    )
    while response.status.state in (StatementState.PENDING, StatementState.RUNNING):
        response = client.statement_execution.get_statement(response.statement_id)

    if response.status.state != StatementState.SUCCEEDED:
        detail = response.status.error.message if response.status.error else str(response.status.state)
        raise RuntimeError(f"query failed: {detail}")

    rows = response.result.data_array or []
    locations = []
    for entity_id, title, region, x, y, summary, scenes_raw in rows:
        scenes_by_era = {s["era"]: s for s in json.loads(scenes_raw)} if scenes_raw else {}
        scenes = {}
        for era, s in scenes_by_era.items():
            pair = {k: v for k, v in (("n64", s.get("n64")), ("oot3d", s.get("oot3d"))) if v}
            if pair:
                scenes[era] = pair
        locations.append(
            {
                "entity_id": entity_id,
                "name": title,
                "region": region,
                "era": sorted(scenes_by_era.keys()),
                "x": float(x),
                "y": float(y),
                "summary": summary,
                "scenes": scenes,
            }
        )
    return locations


def main() -> int:
    locations = fetch_locations()
    payload = {
        "map": {"src": "assets/img/hyrule/hyrule-map.svg", "viewBox": [1000, 640]},
        "noclip": {
            "base": "https://noclip.website",
            "groups": {"n64": "Nintendo 64", "oot3d": "Nintendo 3DS"},
        },
        "locations": locations,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OK — {len(locations)} lieux ecrits dans {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
