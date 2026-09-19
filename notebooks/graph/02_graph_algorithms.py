# Databricks notebook source
# MAGIC %md
# MAGIC # Graph — algorithmes (PySpark, sans GraphFrames)
# MAGIC
# MAGIC PageRank (centralite — alimente le classement "entites liees" du site)
# MAGIC et composantes connexes (detecte les entites isolees du reste du graphe,
# MAGIC utile pour reperer les lacunes de liaison infobox/liens wiki). Resultats
# MAGIC dans `gold.graph_metrics`. Point de depart pour la recherche GNN evoquee
# MAGIC dans le README — pas plus que le calcul de ces deux metriques ce tour.
# MAGIC
# MAGIC **Pourquoi pas GraphFrames (cf. ADR 0003, amende) :** la librairie a
# MAGIC besoin d'un JAR Maven attache a un cluster classique. Le workspace Free
# MAGIC Edition ne provisionne que du compute serverless, qui n'accepte ni
# MAGIC bibliotheque Maven ni, plus largement, Scala (cf. ADR 0004). Les deux
# MAGIC algorithmes sont donc reimplementes ici en PySpark pur — jointures
# MAGIC iterees, pas de dependance externe.
# MAGIC
# MAGIC - **PageRank** : iteration a nombre fixe (10, comme le `maxIter` original),
# MAGIC   sans redistribution de la masse des noeuds sans arete sortante (choix
# MAGIC   pedagogique simplifie, documente ici plutot que cache).
# MAGIC - **Composantes connexes** : propagation iterative du plus petit id de
# MAGIC   noeud a travers les aretes (rendues bidirectionnelles), jusqu'a
# MAGIC   convergence ou `MAX_ITER_CC` — suffisant pour un graphe de la taille de
# MAGIC   celui-ci (des milliers de noeuds/aretes, pas des millions).

# COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
catalog = dbutils.widgets.get("catalog")
spark.sql(f"USE CATALOG {catalog}")

# COMMAND ----------

from pyspark.sql import functions as F

nodes = spark.table("gold.graph_nodes")
edges = spark.table("gold.graph_edges")

# COMMAND ----------

# MAGIC %md
# MAGIC ## PageRank

# COMMAND ----------

RESET_PROBABILITY = 0.15
MAX_ITER_PAGERANK = 10

n_nodes = nodes.count()

out_degree = edges.groupBy(F.col("src").alias("id")).agg(F.count("*").alias("out_degree"))

ranks = nodes.select("id").withColumn("pagerank", F.lit(1.0 / n_nodes) if n_nodes else F.lit(0.0))

for i in range(MAX_ITER_PAGERANK):
    contribs = (
        edges.join(out_degree, edges.src == out_degree.id)
        .join(ranks, edges.src == ranks.id)
        .select(
            F.col("dst").alias("id"),
            (F.col("pagerank") / F.col("out_degree")).alias("contrib"),
        )
    )
    aggregated = contribs.groupBy("id").agg(F.sum("contrib").alias("contrib_sum"))
    ranks = (
        nodes.select("id")
        .join(aggregated, "id", "left")
        .withColumn(
            "pagerank",
            RESET_PROBABILITY / n_nodes + (1 - RESET_PROBABILITY) * F.coalesce(F.col("contrib_sum"), F.lit(0.0)),
        )
        .select("id", "pagerank")
    )
    if i % 3 == 2:  # truncate lineage periodically, cheaper than a full checkpoint dir
        ranks = ranks.localCheckpoint(eager=True)

pagerank_result = ranks

# COMMAND ----------

# MAGIC %md
# MAGIC ## Composantes connexes (propagation du plus petit id)

# COMMAND ----------

MAX_ITER_CC = 30

edges_bidir = (
    edges.select(F.col("src").alias("a"), F.col("dst").alias("b"))
    .unionByName(edges.select(F.col("dst").alias("a"), F.col("src").alias("b")))
    .distinct()
)

labels = nodes.select(F.col("id").alias("a"), F.col("id").alias("label"))

for i in range(MAX_ITER_CC):
    candidats = (
        edges_bidir.join(labels, "a")
        .select(F.col("b").alias("a"), F.col("label").alias("candidate_label"))
        .groupBy("a")
        .agg(F.min("candidate_label").alias("candidate_label"))
    )
    nouveaux_labels = (
        labels.join(candidats, "a", "left")
        .withColumn("label", F.least(F.col("label"), F.coalesce(F.col("candidate_label"), F.col("label"))))
        .select("a", "label")
    )
    if i % 4 == 3:
        nouveaux_labels = nouveaux_labels.localCheckpoint(eager=True)

    nb_changes = (
        nouveaux_labels.alias("n")
        .join(labels.alias("l"), "a")
        .where(F.col("n.label") != F.col("l.label"))
        .count()
    )
    labels = nouveaux_labels
    if nb_changes == 0:
        break

composantes = labels.select(F.col("a").alias("id"), F.col("label").alias("component_id"))

# COMMAND ----------

spark.sql("""
  CREATE TABLE IF NOT EXISTS gold.graph_metrics (
    id STRING NOT NULL, pagerank DOUBLE, component_id STRING
  ) USING DELTA
""")

(
    pagerank_result.select(F.col("id"), F.col("pagerank"))
    .join(composantes, "id", "left")
    .write.mode("overwrite")
    .saveAsTable("gold.graph_metrics")
)

print(f"OK — gold.graph_metrics : {spark.table('gold.graph_metrics').count()} noeuds notes")
display(spark.table("gold.graph_metrics").orderBy(F.col("pagerank").desc()).limit(20))
