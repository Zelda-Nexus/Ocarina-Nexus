"""
Catalog explorer for /lakehouse's sidebar — tables, columns, and declared
PRIMARY KEY / FOREIGN KEY constraints, read from information_schema. Scoped
to gold/silver: the only schemas this App's service principal can reach (see
README's GRANT step) and the only ones worth browsing from the site — bronze
is raw landing copies, ops is internal quality-check history.
"""

from db import run_internal_query

SCHEMAS = ("gold", "silver")


def list_tables() -> dict[str, list[dict]]:
    result = run_internal_query(f"""
        SELECT table_schema, table_name, comment
        FROM information_schema.tables
        WHERE table_catalog = current_catalog()
          AND table_schema IN ({", ".join(f"'{s}'" for s in SCHEMAS)})
        ORDER BY table_schema, table_name
    """)
    by_schema: dict[str, list[dict]] = {s: [] for s in SCHEMAS}
    for schema, name, comment in result["rows"]:
        by_schema[schema].append({"name": name, "comment": comment})
    return by_schema


def table_detail(schema: str, table: str) -> dict:
    if schema not in SCHEMAS:
        raise ValueError(f"schema non expose : {schema}")

    columns = run_internal_query(f"""
        SELECT column_name, data_type, is_nullable, comment
        FROM information_schema.columns
        WHERE table_catalog = current_catalog() AND table_schema = '{schema}' AND table_name = '{table}'
        ORDER BY ordinal_position
    """)

    pk_and_fk = run_internal_query(f"""
        SELECT tc.constraint_type, kcu.column_name, ccu.table_schema, ccu.table_name, ccu.column_name
        FROM information_schema.table_constraints tc
        JOIN information_schema.key_column_usage kcu
          ON tc.constraint_catalog = kcu.constraint_catalog
         AND tc.constraint_schema = kcu.constraint_schema
         AND tc.constraint_name = kcu.constraint_name
        LEFT JOIN information_schema.referential_constraints rc
          ON tc.constraint_catalog = rc.constraint_catalog
         AND tc.constraint_schema = rc.constraint_schema
         AND tc.constraint_name = rc.constraint_name
        LEFT JOIN information_schema.constraint_column_usage ccu
          ON rc.unique_constraint_catalog = ccu.constraint_catalog
         AND rc.unique_constraint_schema = ccu.constraint_schema
         AND rc.unique_constraint_name = ccu.constraint_name
        WHERE tc.table_catalog = current_catalog() AND tc.table_schema = '{schema}' AND tc.table_name = '{table}'
          AND tc.constraint_type IN ('PRIMARY KEY', 'FOREIGN KEY')
    """)

    incoming_fk = run_internal_query(f"""
        SELECT fk_tc.table_schema, fk_tc.table_name, fk_kcu.column_name, pk_ccu.column_name
        FROM information_schema.table_constraints pk_tc
        JOIN information_schema.constraint_column_usage pk_ccu
          ON pk_tc.constraint_catalog = pk_ccu.constraint_catalog
         AND pk_tc.constraint_schema = pk_ccu.constraint_schema
         AND pk_tc.constraint_name = pk_ccu.constraint_name
        JOIN information_schema.referential_constraints rc
          ON rc.unique_constraint_catalog = pk_tc.constraint_catalog
         AND rc.unique_constraint_schema = pk_tc.constraint_schema
         AND rc.unique_constraint_name = pk_tc.constraint_name
        JOIN information_schema.table_constraints fk_tc
          ON fk_tc.constraint_catalog = rc.constraint_catalog
         AND fk_tc.constraint_schema = rc.constraint_schema
         AND fk_tc.constraint_name = rc.constraint_name
        JOIN information_schema.key_column_usage fk_kcu
          ON fk_kcu.constraint_catalog = fk_tc.constraint_catalog
         AND fk_kcu.constraint_schema = fk_tc.constraint_schema
         AND fk_kcu.constraint_name = fk_tc.constraint_name
        WHERE pk_tc.table_catalog = current_catalog() AND pk_tc.table_schema = '{schema}' AND pk_tc.table_name = '{table}'
          AND pk_tc.constraint_type = 'PRIMARY KEY'
    """)

    pk_columns = {col for kind, col, *_ in pk_and_fk["rows"] if kind == "PRIMARY KEY"}
    outgoing_fk = {
        col: {"schema": ref_schema, "table": ref_table, "column": ref_col}
        for kind, col, ref_schema, ref_table, ref_col in pk_and_fk["rows"]
        if kind == "FOREIGN KEY"
    }

    return {
        "schema": schema,
        "table": table,
        "columns": [
            {
                "name": name,
                "type": dtype,
                "nullable": nullable == "YES",
                "comment": comment,
                "primary_key": name in pk_columns,
                "foreign_key": outgoing_fk.get(name),
            }
            for name, dtype, nullable, comment in columns["rows"]
        ],
        "referenced_by": [
            {"schema": s, "table": t, "column": c, "references_column": rc}
            for s, t, c, rc in incoming_fk["rows"]
        ],
    }
