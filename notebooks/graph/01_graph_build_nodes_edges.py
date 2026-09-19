# Databricks notebook source
# MAGIC %md
# MAGIC # Graph — noeuds et aretes
# MAGIC
# MAGIC Materialise `gold.fact_entity_relation` (deja la fusion a 4 signaux, cf.
# MAGIC `notebooks/gold/02_gold_facts.py`) sous la forme attendue par les
# MAGIC algorithmes du notebook suivant : une colonne `id` pour les noeuds,
# MAGIC `src`/`dst` pour les aretes. Ce notebook ne fait QUE cette
# MAGIC materialisation — les algorithmes de graphe sont dans
# MAGIC `02_graph_algorithms.py`, pour pouvoir rejouer l'un sans l'autre.

# COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
catalog = dbutils.widgets.get("catalog")
spark.sql(f"USE CATALOG {catalog}")

# COMMAND ----------

from pyspark.sql.functions import col

# COMMAND ----------

spark.sql("""
  CREATE TABLE IF NOT EXISTS gold.graph_nodes (
    id STRING NOT NULL, entity_types ARRAY<STRING>, title STRING
  ) USING DELTA
""")

(
    spark.table("silver.entity").where("is_current")
    .select(col("entity_id").alias("id"), col("entity_types"), col("title"))
    .write.mode("overwrite")
    .saveAsTable("gold.graph_nodes")
)

# COMMAND ----------

spark.sql("""
  CREATE TABLE IF NOT EXISTS gold.graph_edges (
    src STRING NOT NULL, dst STRING NOT NULL, relation_type STRING, weight INT
  ) USING DELTA
""")

(
    spark.table("gold.fact_entity_relation")
    .where(col("to_id").isNotNull())
    .select(col("from_id").alias("src"), col("to_id").alias("dst"), col("relation_type"), col("weight"))
    .write.mode("overwrite")
    .saveAsTable("gold.graph_edges")
)

print(
    f"OK — gold.graph_nodes : {spark.table('gold.graph_nodes').count()} noeuds, "
    f"gold.graph_edges : {spark.table('gold.graph_edges').count()} aretes"
)
