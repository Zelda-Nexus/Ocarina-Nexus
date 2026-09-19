"""
Ocarina Nexus — Databricks App.

Three pages: real-time graph stats ("/"), a read-only SQL console with a
catalog sidebar ("/lakehouse"), and pipeline monitoring/triggering
("/pipelines"). See db.py for the query layer, jobs.py for the Jobs API
helper, catalog.py for the table/column/constraint browser.
"""

import json
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

import catalog
import jobs
from db import QueryError, run_internal_query, run_read_only_query

app = FastAPI(title="Ocarina Nexus — Lakehouse")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

STATS_QUERY = """
SELECT
  (SELECT count(*) FROM gold.graph_nodes) AS entities,
  (SELECT count(*) FROM gold.graph_edges) AS relations,
  (SELECT count(DISTINCT evidence_source) FROM gold.fact_entity_relation) AS sources,
  (SELECT count(DISTINCT relation_type) FROM gold.graph_edges) AS relation_types
"""

RELATION_BREAKDOWN_QUERY = """
SELECT relation_type, count(*) AS n
FROM gold.graph_edges
GROUP BY relation_type
ORDER BY n DESC
"""

TOP_ENTITIES_QUERY = """
SELECT n.title, n.entity_types, m.pagerank
FROM gold.graph_metrics m
JOIN gold.graph_nodes n ON n.id = m.id
ORDER BY m.pagerank DESC
LIMIT 15
"""


def _parse_array_cell(value):
    """The Statement Execution API returns ARRAY<STRING> as a JSON-encoded string."""
    if not value:
        return []
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return [value]


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/lakehouse", response_class=HTMLResponse)
def lakehouse(request: Request):
    return templates.TemplateResponse("lakehouse.html", {"request": request})


@app.get("/pipelines", response_class=HTMLResponse)
def pipelines_page(request: Request):
    return templates.TemplateResponse("pipelines.html", {"request": request})


@app.get("/api/stats")
def api_stats():
    stats = run_internal_query(STATS_QUERY)
    breakdown = run_internal_query(RELATION_BREAKDOWN_QUERY)
    top_entities = run_internal_query(TOP_ENTITIES_QUERY)

    row = stats["rows"][0] if stats["rows"] else [0, 0, 0, 0]
    return {
        "entities": int(row[0] or 0),
        "relations": int(row[1] or 0),
        "sources": int(row[2] or 0),
        "relation_types": int(row[3] or 0),
        "relation_breakdown": [{"relation_type": r[0], "count": int(r[1])} for r in breakdown["rows"]],
        "top_entities": [
            {"title": r[0], "entity_types": _parse_array_cell(r[1]), "pagerank": float(r[2] or 0)}
            for r in top_entities["rows"]
        ],
    }


class QueryRequest(BaseModel):
    sql: str


@app.post("/api/query")
def api_query(payload: QueryRequest):
    try:
        return run_read_only_query(payload.sql)
    except QueryError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/tables")
def api_tables():
    return catalog.list_tables()


@app.get("/api/tables/{schema}/{table}")
def api_table_detail(schema: str, table: str):
    try:
        return catalog.table_detail(schema, table)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@app.get("/api/jobs")
def api_jobs():
    return jobs.list_pipeline_jobs()


@app.get("/api/jobs/{job_id}/runs")
def api_job_runs(job_id: int):
    return jobs.list_runs(job_id)


@app.post("/api/jobs/{job_id}/run")
def api_job_run(job_id: int):
    return jobs.run_now(job_id)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("DATABRICKS_APP_PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
