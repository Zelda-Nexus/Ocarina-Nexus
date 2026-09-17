// Databricks notebook source
// MAGIC %md
// MAGIC # Graph — algorithmes (GraphFrames)
// MAGIC
// MAGIC PageRank (centralite — alimente le classement "entites liees" du site)
// MAGIC et composantes connexes (detecte les entites isolees du reste du graphe,
// MAGIC utile pour reperer les lacunes de liaison infobox/liens wiki). Resultats
// MAGIC dans `gold.graph_metrics`. Point de depart pour la recherche GNN evoquee
// MAGIC dans le README — pas plus que le calcul de ces deux metriques ce tour.

// COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
val catalog = dbutils.widgets.get("catalog")
spark.sql(s"USE CATALOG $catalog")

// COMMAND ----------

import org.graphframes.GraphFrame
import org.apache.spark.sql.functions._

val nodes = spark.table("gold.graph_nodes")
val edges = spark.table("gold.graph_edges")

val g = GraphFrame(nodes, edges)

// COMMAND ----------

val pageRankResult = g.pageRank.resetProbability(0.15).maxIter(10).run()
val composantes = g.connectedComponents.run()

// COMMAND ----------

spark.sql("""
  CREATE TABLE IF NOT EXISTS gold.graph_metrics (
    id STRING NOT NULL, pagerank DOUBLE, component_id BIGINT
  ) USING DELTA
""")

pageRankResult.vertices.select(col("id"), col("pagerank"))
  .join(composantes.select(col("id"), col("component").as("component_id")), Seq("id"), "left")
  .write.mode("overwrite").saveAsTable("gold.graph_metrics")

println(s"OK — gold.graph_metrics : ${spark.table("gold.graph_metrics").count()} noeuds notes")
display(spark.table("gold.graph_metrics").orderBy(col("pagerank").desc).limit(20))
