// Databricks notebook source
// MAGIC %md
// MAGIC # Silver — textes et noms multilingues
// MAGIC
// MAGIC `game_message` est alimentee integralement depuis `bronze.game_text_messages`
// MAGIC (CloudModding, structure deja exploitable a l'extraction).
// MAGIC
// MAGIC `entity_name_i18n` / `entity_description_i18n` restent des **stubs**
// MAGIC (colonne `page` seule, `lang`/`name`/`meaning` a NULL) : l'extraction Cargo
// MAGIC ne recupere aujourd'hui que l'index de pages par table, pas encore les
// MAGIC colonnes (voir la docstring de `zeldawiki_cargo.py` — Special:CargoTables
// MAGIC est bloque, et les noms de champs Lua ne sont pas devinables depuis l'API).
// MAGIC Cette table se remplit sans changement de forme des que les vrais noms de
// MAGIC champs sont connus et ajoutes a `TABLES` cote extraction.

// COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
val catalog = dbutils.widgets.get("catalog")
spark.sql(s"USE CATALOG $catalog")

// COMMAND ----------

import org.apache.spark.sql.functions._

// COMMAND ----------

spark.sql("""
  CREATE TABLE IF NOT EXISTS silver.game_message (
    message_key STRING NOT NULL,
    text_id     STRING,
    lang        STRING,
    version     STRING,
    section     STRING,
    text        STRING
  ) USING DELTA
""")

spark.table("bronze.game_text_messages")
  .where(col("text_id").isNotNull)
  .withColumn("message_key", concat_ws(":", col("version"), col("text_id")))
  .select(
    col("message_key"), col("text_id"), col("lang"), col("version"),
    col("section"), col("message").as("text")
  )
  .distinct()
  .write.mode("overwrite").saveAsTable("game_message")

println(s"OK — silver.game_message : ${spark.table("game_message").count()} messages")

// COMMAND ----------

spark.sql("""
  CREATE TABLE IF NOT EXISTS silver.entity_name_i18n (
    page STRING, game STRING, lang STRING, name STRING, romanization STRING, meaning STRING
  ) USING DELTA
  COMMENT 'Stub — voir commentaire en tete de notebook'
""")

spark.table("bronze.zeldawiki_cargo_nomenclature")
  .select(col("page"), lit(null).cast("string").as("game"), lit(null).cast("string").as("lang"),
          lit(null).cast("string").as("name"), lit(null).cast("string").as("romanization"),
          lit(null).cast("string").as("meaning"))
  .distinct()
  .write.mode("overwrite").saveAsTable("entity_name_i18n")

spark.sql("""
  CREATE TABLE IF NOT EXISTS silver.entity_description_i18n (
    page STRING, lang STRING, description STRING
  ) USING DELTA
  COMMENT 'Stub — voir commentaire en tete de notebook'
""")

spark.table("bronze.zeldawiki_cargo_descriptions")
  .select(col("page"), lit(null).cast("string").as("lang"), lit(null).cast("string").as("description"))
  .distinct()
  .write.mode("overwrite").saveAsTable("entity_description_i18n")

println("OK — stubs entity_name_i18n / entity_description_i18n ecrits")
