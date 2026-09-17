// Databricks notebook source
// MAGIC %md
// MAGIC # Silver — monde logique (OoT-Randomizer)
// MAGIC
// MAGIC `bronze.rando_world_raw` (fichiers `data/World/*.json`, deja du JSON
// MAGIC valide une fois les commentaires retires a l'extraction) donne
// MAGIC directement `rando_region`, `rando_region_exit`, `rando_region_location`.
// MAGIC
// MAGIC `rando_location` / `rando_item` restent des **stubs vides** : leur
// MAGIC source (`LocationList.py`/`ItemList.py`, captures en texte brut dans
// MAGIC `bronze.rando_modules_raw`) sont des modules Python executables, pas des
// MAGIC donnees — les structurer demande un parseur AST dedie (Risque 3 du plan),
// MAGIC pas encore ecrit. Rejouable depuis Bronze des qu'il existe.

// COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
val catalog = dbutils.widgets.get("catalog")
spark.sql(s"USE CATALOG $catalog")

// COMMAND ----------

import org.apache.spark.sql.functions._

// COMMAND ----------

val entries = spark.table("bronze.rando_world_raw")
  .where(col("parsed") === true)
  .select(col("file"), explode(col("entries")).as("region"))

entries.cache()

// COMMAND ----------

spark.sql("CREATE TABLE IF NOT EXISTS silver.rando_region " +
  "(region_name STRING, dungeon STRING, hint_area STRING, scene STRING, " +
  "time_passes BOOLEAN, savewarp STRING, is_boss_room BOOLEAN, source_file STRING) USING DELTA")

entries
  .select(
    col("region.region_name").as("region_name"),
    col("region.dungeon").as("dungeon"),
    col("region.hint").as("hint_area"),
    col("region.scene").as("scene"),
    col("region.time_passes").as("time_passes"),
    col("region.savewarp").as("savewarp"),
    coalesce(col("region.is_boss_room"), lit(false)).as("is_boss_room"),
    col("file").as("source_file")
  )
  .where(col("region_name").isNotNull)
  .write.mode("overwrite").saveAsTable("silver.rando_region")

// COMMAND ----------

spark.sql("CREATE TABLE IF NOT EXISTS silver.rando_region_exit " +
  "(from_region STRING, to_region STRING, rule_expr STRING) USING DELTA")

entries
  .select(col("region.region_name").as("from_region"), explode_outer(col("region.exits")).as(Seq("to_region", "rule_expr")))
  .where(col("from_region").isNotNull && col("to_region").isNotNull)
  .write.mode("overwrite").saveAsTable("silver.rando_region_exit")

// COMMAND ----------

spark.sql("CREATE TABLE IF NOT EXISTS silver.rando_region_location " +
  "(region_name STRING, location_name STRING, rule_expr STRING) USING DELTA")

entries
  .select(col("region.region_name").as("region_name"), explode_outer(col("region.locations")).as(Seq("location_name", "rule_expr")))
  .where(col("region_name").isNotNull && col("location_name").isNotNull)
  .write.mode("overwrite").saveAsTable("silver.rando_region_location")

println(s"OK — silver.rando_region : ${spark.table("silver.rando_region").count()} regions, " +
  s"${spark.table("silver.rando_region_exit").count()} sorties, " +
  s"${spark.table("silver.rando_region_location").count()} liens emplacement")

// COMMAND ----------

// MAGIC %md
// MAGIC ## Stubs — a completer par un parseur AST de `LocationList.py`/`ItemList.py`

// COMMAND ----------

spark.sql("CREATE TABLE IF NOT EXISTS silver.rando_location " +
  "(location_name STRING, type STRING, scene STRING, vanilla_item STRING) USING DELTA " +
  "COMMENT 'Stub — voir commentaire en tete de notebook'")

spark.sql("CREATE TABLE IF NOT EXISTS silver.rando_item " +
  "(item_name STRING, advancement BOOLEAN, priority STRING, type STRING) USING DELTA " +
  "COMMENT 'Stub — voir commentaire en tete de notebook'")
