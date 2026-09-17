// Databricks notebook source
// MAGIC %md
// MAGIC # Silver — Wikidata / Wikipedia
// MAGIC
// MAGIC `bronze.wikidata_entities.entity` est garde en JSON texte depuis le
// MAGIC Bronze (cles dynamiques par code de propriete P.., voir
// MAGIC `notebooks/bronze/05_bronze_external.scala`). On en extrait ici un jeu de
// MAGIC proprietes connues et utiles (dates, plateformes, identifiants externes
// MAGIC croises) via `get_json_object` — chemin different selon le type de
// MAGIC valeur Wikidata (item -> `.value.id`, date -> `.value.time`,
// MAGIC identifiant externe -> `.value` brut). Extensible sans re-scraper : une
// MAGIC nouvelle propriete est une ligne de plus dans `PROPRIETES`.

// COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
val catalog = dbutils.widgets.get("catalog")
spark.sql(s"USE CATALOG $catalog")

// COMMAND ----------

import org.apache.spark.sql.functions._

// COMMAND ----------

spark.sql("""
  CREATE TABLE IF NOT EXISTS silver.wikidata_claim (
    qid STRING NOT NULL, property STRING NOT NULL, value STRING
  ) USING DELTA
""")

// (code propriete, libelle, chemin JSON vers la valeur)
val proprietes = Seq(
  ("P577", "release_date", "$.claims.P577[0].mainsnak.datavalue.value.time"),
  ("P400", "platform_qid", "$.claims.P400[0].mainsnak.datavalue.value.id"),
  ("P136", "genre_qid", "$.claims.P136[0].mainsnak.datavalue.value.id"),
  ("P179", "series_qid", "$.claims.P179[0].mainsnak.datavalue.value.id"),
  ("P5794", "igdb_slug", "$.claims.P5794[0].mainsnak.datavalue.value"),
  ("P4769", "gamefaqs_id", "$.claims.P4769[0].mainsnak.datavalue.value"),
  ("P8351", "vgchartz_id", "$.claims.P8351[0].mainsnak.datavalue.value"),
  ("P6337", "tcrf_id", "$.claims.P6337[0].mainsnak.datavalue.value")
)

val bronze = spark.table("bronze.wikidata_entities").select(col("qid"), col("entity"))

val claims = proprietes
  .map { case (code, label, path) =>
    bronze
      .withColumn("property", lit(s"$code:$label"))
      .withColumn("value", get_json_object(col("entity"), path))
      .select("qid", "property", "value")
  }
  .reduce(_ unionByName _)
  .where(col("value").isNotNull)

claims.write.mode("overwrite").saveAsTable("silver.wikidata_claim")
println(s"OK — silver.wikidata_claim : ${claims.count()} lignes")

// COMMAND ----------

spark.sql("""
  CREATE TABLE IF NOT EXISTS silver.wikipedia_article (
    qid STRING, lang STRING NOT NULL, title STRING, url STRING, extract STRING, wikitext STRING,
    license STRING
  ) USING DELTA
""")

spark.table("bronze.wikipedia_articles")
  .select(
    lit(null).cast("string").as("qid"), // jointure par titre a faire en Gold, pas de qid direct en sortie de l'extraction
    col("lang"), col("title"), col("url"), col("extract"), col("wikitext"),
    lit("CC BY-SA 4.0").as("license")
  )
  .write.mode("overwrite").saveAsTable("silver.wikipedia_article")

println(s"OK — silver.wikipedia_article : ${spark.table("silver.wikipedia_article").count()} articles")
