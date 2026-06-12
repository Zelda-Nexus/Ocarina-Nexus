import duckdb


def load_characters(con: duckdb.DuckDBPyConnection):
    con.execute("""
        CREATE OR REPLACE TABLE characters AS
        SELECT * FROM read_parquet('./data/silver/characters/characters.parquet')
    """)


def create_views(con: duckdb.DuckDBPyConnection):
    con.execute("""
        CREATE OR REPLACE VIEW characters_by_race AS
        SELECT race, COUNT(*) as count
        FROM characters
        GROUP BY race
        ORDER BY count DESC
    """)

    con.execute("""
        CREATE OR REPLACE VIEW bosses AS
        SELECT id, name, race, primary_location
        FROM characters
        WHERE is_boss = true
    """)


def run():
    con = duckdb.connect("./data/gold/ocarina_nexus.duckdb")
    load_characters(con)
    create_views(con)
    con.close()
