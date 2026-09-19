"""
Statement Execution API helper. Two entry points:
- run_internal_query: trusted, hardcoded SQL (the stats page).
- run_read_only_query: user-supplied SQL (the /lakehouse console) — validated
  to be a single SELECT/WITH statement, then capped at ROW_LIMIT rows.

Schema-level enforcement (restricting to gold/silver) is a Unity Catalog grant
on this App's service principal, not string-matching here — see README for the
one-time GRANT. This module only blocks obviously destructive statements.
"""

import os
import re
import time

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import StatementState

CATALOG = os.environ.get("OCARINA_CATALOG", "ocarina_dev")
WAREHOUSE_ID = os.environ["OCARINA_WAREHOUSE_ID"]
ROW_LIMIT = 500

_client = WorkspaceClient()

_FORBIDDEN = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|TRUNCATE|CREATE|GRANT|REVOKE|"
    r"COPY|VACUUM|OPTIMIZE|ANALYZE|USE|SET|CALL|REFRESH|COMMENT)\b",
    re.IGNORECASE,
)
_STARTS_SELECT = re.compile(r"^\s*(SELECT|WITH)\b", re.IGNORECASE)


class QueryError(ValueError):
    """User-facing rejection — either pre-flight validation or a warehouse error."""


def _validate_read_only(statement: str) -> str:
    stripped = statement.strip()
    if not stripped:
        raise QueryError("Requete vide.")
    body = stripped.rstrip(";").strip()
    if ";" in body:
        raise QueryError("Une seule instruction SQL a la fois.")
    if not _STARTS_SELECT.match(body):
        raise QueryError("Seules les requetes SELECT / WITH sont autorisees.")
    if _FORBIDDEN.search(body):
        raise QueryError("Mot-cle non autorise en lecture seule.")
    return body


def run_read_only_query(statement: str) -> dict:
    body = _validate_read_only(statement)
    capped = f"SELECT * FROM ({body}) AS ocarina_query LIMIT {ROW_LIMIT}"
    return _execute(capped)


def run_internal_query(statement: str) -> dict:
    return _execute(statement)


def _execute(statement: str) -> dict:
    response = _client.statement_execution.execute_statement(
        warehouse_id=WAREHOUSE_ID,
        statement=statement,
        catalog=CATALOG,
        wait_timeout="30s",
    )
    statement_id = response.statement_id
    while response.status.state in (StatementState.PENDING, StatementState.RUNNING):
        time.sleep(1)
        response = _client.statement_execution.get_statement(statement_id)

    if response.status.state != StatementState.SUCCEEDED:
        detail = response.status.error.message if response.status.error else str(response.status.state)
        raise QueryError(detail)

    columns = [c.name for c in response.manifest.schema.columns]
    rows = response.result.data_array if response.result else []
    return {"columns": columns, "rows": rows or [], "row_count": len(rows or [])}
