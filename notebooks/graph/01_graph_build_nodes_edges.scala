// Databricks notebook source
// MAGIC %md
// MAGIC # Graph — noeuds et aretes (GraphFrames)
// MAGIC
// MAGIC Materialise `gold.fact_entity_relation` (deja la fusion a 4 signaux, cf.
// MAGIC `notebooks/gold/02_gold_facts.scala`) sous la forme attendue par
// MAGIC GraphFrames : une colonne `id` pour les noeuds, `src`/`dst` pour les
// MAGIC aretes. Ce notebook ne fait QUE cette materialisation — les algorithmes
// MAGIC de graphe sont dans `02_graph_algorithms.scala`, pour pouvoir rejouer l'un
// MAGIC sans l'autre.
// MAGIC
// MAGIC ATTENTION (risque documente dans le plan) : GraphFrames necessite une
// MAGIC librairie Maven attachee au cluster (`graphframes:graphframes`) — a
// MAGIC valider que ce mecanisme est disponible sur le compute de la Free
// MAGIC Edition avant de compter sur ce notebook en production.

// COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
val catalog = dbutils.widgets.get("catalog")
spark.sql(s"USE CATALOG $catalog")

// COMMAND ----------

import org.apache.spark.sql.functions._

spark.sql("""
  CREATE TABLE IF NOT EXISTS gold.graph_nodes (
    id STRING NOT NULL, entity_types ARRAY<STRING>, title STRING
  ) USING DELTA
""")

spark.table("silver.entity").where("is_current")
  .select(col("entity_id").as("id"), col("entity_types"), col("title"))
  .write.mode("overwrite").saveAsTable("gold.graph_nodes")

// COMMAND ----------

spark.sql("""
  CREATE TABLE IF NOT EXISTS gold.graph_edges (
    src STRING NOT NULL, dst STRING NOT NULL, relation_type STRING, weight INT
  ) USING DELTA
""")

spark.table("gold.fact_entity_relation")
  .where(col("to_id").isNotNull)
  .select(col("from_id").as("src"), col("to_id").as("dst"), col("relation_type"), col("weight"))
  .write.mode("overwrite").saveAsTable("gold.graph_edges")

println(s"OK — gold.graph_nodes : ${spark.table("gold.graph_nodes").count()} noeuds, " +
  s"gold.graph_edges : ${spark.table("gold.graph_edges").count()} aretes")
