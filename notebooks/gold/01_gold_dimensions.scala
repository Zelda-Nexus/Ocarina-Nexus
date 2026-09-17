// Databricks notebook source
// MAGIC %md
// MAGIC # Gold — dimensions (bibliotheque / site)
// MAGIC
// MAGIC `dim_entity` est la vue unifiee de base ; les autres dimensions filtrent
// MAGIC par `entity_types` et ajoutent les attributs specifiques disponibles via
// MAGIC `silver.entity_infobox_kv` (les cles varient par type d'entite — cf.
// MAGIC `notebooks/bronze/01_bronze_zeldawiki.scala`).

// COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
val catalog = dbutils.widgets.get("catalog")
spark.sql(s"USE CATALOG $catalog")

// COMMAND ----------

import org.apache.spark.sql.functions._

val entity = spark.table("silver.entity").where("is_current")
val infobox = spark.table("silver.entity_infobox_kv")

def pivotInfobox(cles: Seq[String]) =
  infobox.where(col("key").isInCollection(cles))
    .groupBy("pageid")
    .pivot("key", cles)
    .agg(first("value"))

// COMMAND ----------

spark.sql("""
  CREATE TABLE IF NOT EXISTS gold.dim_entity (
    entity_id STRING NOT NULL, pageid BIGINT, entity_types ARRAY<STRING>, title STRING,
    summary STRING, source_url STRING, license STRING
  ) USING DELTA
""")

entity
  .select(col("entity_id"), col("pageid"), col("entity_types"), col("title"), col("summary"), col("source_url"), col("license"))
  .write.mode("overwrite").saveAsTable("gold.dim_entity")

// COMMAND ----------

spark.sql("DROP TABLE IF EXISTS gold.dim_character")
val infoboxPersonnage = pivotInfobox(Seq("Race", "Gender", "Game", "Era(s)", "Location"))

entity.where(array_contains(col("entity_types"), "characters"))
  .join(infoboxPersonnage, Seq("pageid"), "left")
  .select(
    col("entity_id"), col("pageid"), col("title"), col("summary"),
    col("Race").as("race"), col("Gender").as("gender"), col("Location").as("location")
  )
  .write.mode("overwrite").saveAsTable("gold.dim_character")

// COMMAND ----------

spark.sql("DROP TABLE IF EXISTS gold.dim_item")
val infoboxObjet = pivotInfobox(Seq("Use", "Found in", "Comes from"))

entity.where(array_contains(col("entity_types"), "items"))
  .join(infoboxObjet, Seq("pageid"), "left")
  .select(col("entity_id"), col("pageid"), col("title"), col("summary"), col("Use").as("effect"))
  .write.mode("overwrite").saveAsTable("gold.dim_item")

// COMMAND ----------

spark.sql("DROP TABLE IF EXISTS gold.dim_location")

val randoRegionParLieu = spark.table("silver.rando_region")
  .select(lower(regexp_replace(col("region_name"), "[^A-Za-z0-9]+", " ")).as("_join_key"), col("region_name"), col("scene").as("rando_scene"))

entity.where(array_contains(col("entity_types"), "locations"))
  .withColumn("_join_key", lower(regexp_replace(col("title"), "[^A-Za-z0-9]+", " ")))
  .join(randoRegionParLieu, Seq("_join_key"), "left")
  .select(col("entity_id"), col("pageid"), col("title"), col("summary"), col("region_name").as("rando_region_name"), col("rando_scene"))
  .write.mode("overwrite").saveAsTable("gold.dim_location")

// COMMAND ----------

spark.sql("DROP TABLE IF EXISTS gold.dim_dungeon")
entity.where(array_contains(col("entity_types"), "dungeons"))
  .select(col("entity_id"), col("pageid"), col("title"), col("summary"))
  .write.mode("overwrite").saveAsTable("gold.dim_dungeon")

// COMMAND ----------

spark.sql("DROP TABLE IF EXISTS gold.dim_enemy")
entity.where(array_contains(col("entity_types"), "enemies"))
  .select(col("entity_id"), col("pageid"), col("title"), col("summary"))
  .write.mode("overwrite").saveAsTable("gold.dim_enemy")

spark.sql("DROP TABLE IF EXISTS gold.dim_boss")
entity.where(array_contains(col("entity_types"), "bosses"))
  .select(col("entity_id"), col("pageid"), col("title"), col("summary"))
  .write.mode("overwrite").saveAsTable("gold.dim_boss")

// COMMAND ----------

spark.sql("DROP TABLE IF EXISTS gold.dim_song")

spark.table("silver.sequence")
  .select(col("seq_id"), col("seq_enum"), col("name"))
  .write.mode("overwrite").saveAsTable("gold.dim_song")

println("OK — dimensions gold ecrites")
