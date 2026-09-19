# Databricks notebook source
# MAGIC %md
# MAGIC # Silver — tables du moteur (decompilation zeldaret/oot)
# MAGIC
# MAGIC `bronze.decomp_tables_raw` contient le texte brut de chaque fichier `.h`
# MAGIC (`raw_text`). Ce notebook parse les macros `DEFINE_*` communes a tous ces
# MAGIC fichiers (`/* 0xNNNN */ DEFINE_XXX(arg1, arg2, ...)`) en une table
# MAGIC generique `silver.engine_table_entry`, puis expose des vues semantiques
# MAGIC (`silver.actor`, `silver.scene`, `silver.object`, `silver.sequence`) qui
# MAGIC nomment chaque position d'argument d'apres la documentation en tete de
# MAGIC chaque fichier source (recopiee ci-dessous). `entrance_table.h` et les
# MAGIC banques SFX restent dans la table generique pour l'instant (7+ arguments,
# MAGIC pas encore verifies ligne a ligne) — a specialiser plus tard sans
# MAGIC re-scraper, exactement comme prevu par le rejeu depuis Bronze.
# MAGIC
# MAGIC Semantique des arguments (docstrings originales du decomp) :
# MAGIC - `actor_table.h` : (nom de l'overlay, enum, type d'allocation, nom de debug)
# MAGIC - `scene_table.h` : (segment de la scene, segment de la title card, enum, config de rendu, ?, ?)
# MAGIC - `object_table.h` : (segment de l'objet, enum)
# MAGIC - `sequence_table.h` : (nom de sequence, enum, support de stockage, politique de cache, flags)

# COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
catalog = dbutils.widgets.get("catalog")
spark.sql(f"USE CATALOG {catalog}")

# COMMAND ----------

import re

from pyspark.sql.functions import col, explode, udf
from pyspark.sql.types import ArrayType, StringType, StructField, StructType

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Parsing generique des macros `DEFINE_*`

# COMMAND ----------

_MACRO_LINE_RE = re.compile(r"(?:/\*\s*(0x[0-9A-Fa-f]+)\s*\*/\s*)?DEFINE_(\w+)\(([^)]*)\)")

_ENTREE_SCHEMA = ArrayType(
    StructType([
        StructField("hexIndex", StringType()),
        StructField("macro", StringType()),
        StructField("args", ArrayType(StringType())),
        StructField("rawLine", StringType()),
    ])
)


@udf(_ENTREE_SCHEMA)
def parse_fichier(raw_text):
    if not raw_text:
        return []
    entrees = []
    for ligne in raw_text.split("\n"):
        m = _MACRO_LINE_RE.search(ligne)
        if m:
            hex_index = m.group(1) or ""
            macro = m.group(2)
            args = [a.strip() for a in m.group(3).split(",")]
            entrees.append((hex_index, macro, args, ligne.strip()))
    return entrees


entries = (
    spark.table("bronze.decomp_tables_raw")
    .select("file", "raw_text")
    .withColumn("entree", explode(parse_fichier(col("raw_text"))))
    .select(
        col("file"),
        col("entree.hexIndex").alias("hexIndex"),
        col("entree.macro").alias("macro"),
        col("entree.args").alias("args"),
        col("entree.rawLine").alias("rawLine"),
    )
)

entries.write.mode("overwrite").saveAsTable("silver.engine_table_entry")
print(f"OK — silver.engine_table_entry : {entries.count()} entrees")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Vues semantiques

# COMMAND ----------

spark.sql("""
  CREATE OR REPLACE VIEW silver.actor AS
  SELECT
    hexIndex AS actor_id,
    macro AS macro,
    args[1] AS actor_enum,
    args[0] AS overlay_name,
    args[2] AS alloc_type,
    regexp_replace(args[3], '"', '') AS debug_name,
    file AS source_file
  FROM silver.engine_table_entry
  WHERE file = 'actor_table.h'
""")

spark.sql("""
  CREATE OR REPLACE VIEW silver.scene AS
  SELECT
    hexIndex AS scene_id,
    args[2] AS scene_enum,
    args[0] AS segment_name,
    args[1] AS title_card,
    args[3] AS draw_config,
    file AS source_file
  FROM silver.engine_table_entry
  WHERE file = 'scene_table.h'
""")

spark.sql("""
  CREATE OR REPLACE VIEW silver.object AS
  SELECT
    hexIndex AS object_id,
    args[1] AS object_enum,
    args[0] AS object_name,
    file AS source_file
  FROM silver.engine_table_entry
  WHERE file = 'object_table.h'
""")

spark.sql("""
  CREATE OR REPLACE VIEW silver.sequence AS
  SELECT
    hexIndex AS seq_id,
    args[1] AS seq_enum,
    args[0] AS name,
    file AS source_file
  FROM silver.engine_table_entry
  WHERE file = 'sequence_table.h' AND macro = 'SEQUENCE'
""")

spark.sql("""
  CREATE OR REPLACE VIEW silver.sfx AS
  SELECT
    hexIndex AS sfx_id,
    regexp_extract(file, '([a-z]+)bank_table.h', 1) AS bank,
    args[1] AS enum,
    args[0] AS channel,
    file AS source_file
  FROM silver.engine_table_entry
  WHERE file LIKE '%bank_table.h'
""")

print("OK — vues actor / scene / object / sequence / sfx creees")
