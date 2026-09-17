// Databricks notebook source
// MAGIC %md
// MAGIC # Gold — faits, dont la fusion a l'origine du graphe de connaissances
// MAGIC
// MAGIC `fact_entity_relation` fusionne les signaux disponibles aujourd'hui :
// MAGIC 1. infobox structuree (`Location` -> `located_in`, `Race` -> `is_species`) ;
// MAGIC 2. liens wiki (`silver.entity_link`), type `related_to`, ponderes par
// MAGIC    occurrence ;
// MAGIC 3. graphe de regions du randomizer (`rando_region_exit`), rapproche des
// MAGIC    entites de type `locations` par correspondance approximative de nom
// MAGIC    (mise en minuscule + ponctuation retiree) — imprecis par construction,
// MAGIC    documente comme tel plutot que cache.
// MAGIC
// MAGIC La correspondance scene/entrance/actor (4e signal du schema cible §3.3)
// MAGIC n'a pas de cle de jointure fiable identifiee pour l'instant : laissee pour
// MAGIC un futur notebook plutot que d'inventer un rapprochement hasardeux.

// COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
val catalog = dbutils.widgets.get("catalog")
spark.sql(s"USE CATALOG $catalog")

// COMMAND ----------

import org.apache.spark.sql.functions._

def slugKey(c: org.apache.spark.sql.Column) = lower(regexp_replace(c, "[^A-Za-z0-9]+", "_"))

val entity = spark.table("silver.entity").where("is_current")
  .select(col("pageid"), col("entity_id"), col("title"))

// COMMAND ----------

// MAGIC %md ## fact_entity_relation

// COMMAND ----------

spark.sql("""
  CREATE TABLE IF NOT EXISTS gold.fact_entity_relation (
    from_id STRING NOT NULL, to_id STRING, to_title_raw STRING,
    relation_type STRING NOT NULL, weight INT, evidence_source STRING, evidence_url STRING
  ) USING DELTA
""")

// Signal 1 — infobox
val relationsInfobox = spark.table("silver.entity_infobox_kv")
  .where(col("key").isInCollection(Seq("Location", "Race", "Dungeon", "Boss")))
  .join(entity.withColumnRenamed("pageid", "pageid_src"), col("pageid") === col("pageid_src"))
  .withColumn("relation_type", expr("""
    CASE key
      WHEN 'Location' THEN 'located_in'
      WHEN 'Race' THEN 'is_species'
      WHEN 'Dungeon' THEN 'located_in'
      WHEN 'Boss' THEN 'boss_of'
    END
  """))
  .join(entity.select(col("entity_id").as("to_id"), slugKey(col("title")).as("_join_key")), slugKey(col("value")) === col("_join_key"), "left")
  .select(
    col("entity_id").as("from_id"), col("to_id"), col("value").as("to_title_raw"),
    col("relation_type"), lit(1).as("weight"),
    lit("zeldawiki_infobox").as("evidence_source"), col("source_url").as("evidence_url")
  )

// Signal 2 — liens wiki, pondere par occurrence
val entityLink = spark.table("silver.entity_link")
  .join(entity.withColumnRenamed("pageid", "from_pageid_join"), col("from_pageid") === col("from_pageid_join"))
  .groupBy(col("entity_id").as("from_id"), col("to_title"))
  .agg(count("*").as("weight"))

val relationsLiens = entityLink
  .join(entity.select(col("entity_id").as("to_id"), col("title").as("_to_title_exact")), col("to_title") === col("_to_title_exact"), "left")
  .select(
    col("from_id"), col("to_id"), col("to_title").as("to_title_raw"),
    lit("related_to").as("relation_type"), col("weight"),
    lit("zeldawiki_links").as("evidence_source"), lit(null).cast("string").as("evidence_url")
  )

// Signal 3 — graphe de regions du randomizer, rapproche par nom approximatif
val entiteslieux = entity.withColumn("_join_key", slugKey(col("title")))

val relationsRando = spark.table("silver.rando_region_exit")
  .withColumn("_from_key", slugKey(col("from_region")))
  .withColumn("_to_key", slugKey(col("to_region")))
  .join(entiteslieux.select(col("entity_id").as("from_id"), col("_join_key").as("_from_key")), Seq("_from_key"))
  .join(entiteslieux.select(col("entity_id").as("to_id"), col("_join_key").as("_to_key")), Seq("_to_key"))
  .select(
    col("from_id"), col("to_id"), col("to_region").as("to_title_raw"),
    lit("adjacent_to").as("relation_type"), lit(1).as("weight"),
    lit("oot_randomizer_region_graph").as("evidence_source"),
    lit("https://github.com/OoTRandomizer/OoT-Randomizer/tree/Dev/data/World").as("evidence_url")
  )

val toutesRelations = relationsInfobox.unionByName(relationsLiens).unionByName(relationsRando)
toutesRelations.write.mode("overwrite").saveAsTable("gold.fact_entity_relation")

println(s"OK — gold.fact_entity_relation : ${toutesRelations.count()} relations " +
  s"(infobox=${relationsInfobox.count()}, liens=${relationsLiens.count()}, rando=${relationsRando.count()})")

// COMMAND ----------

// MAGIC %md ## fact_speedrun_record, bridge_entity_message, fact_item_location (stub)

// COMMAND ----------

spark.sql("DROP TABLE IF EXISTS gold.fact_speedrun_record")
spark.table("silver.speedrun_run")
  .join(spark.table("silver.speedrun_category"), Seq("category_id"), "left")
  .select(col("run_id"), col("category_id"), col("name").as("category_name"), col("level_name"), col("place"), col("time_seconds"), col("platform"), col("video_url"))
  .write.mode("overwrite").saveAsTable("gold.fact_speedrun_record")

// COMMAND ----------

spark.sql("DROP TABLE IF EXISTS gold.bridge_entity_message")
// Rapprochement par occurrence du titre de l'entite dans le texte du message —
// heuristique simple (nom exact, sensible a la casse) ; a affiner (NER,
// alias multilingues via entity_name_i18n une fois peuple) sans re-scraper.
spark.table("silver.game_message")
  .crossJoin(entity)
  .where(col("text").contains(col("title")))
  .select(col("entity_id"), col("message_key"), col("text_id"), col("lang"))
  .write.mode("overwrite").saveAsTable("gold.bridge_entity_message")

// COMMAND ----------

spark.sql("""
  CREATE TABLE IF NOT EXISTS gold.fact_item_location (
    item_entity_id STRING, location_name STRING, rule_expr STRING
  ) USING DELTA
  COMMENT 'Stub — depend de silver.rando_location, non peuple tant que le parseur AST de LocationList.py nexiste pas'
""")

println("OK — fact_speedrun_record, bridge_entity_message ecrits ; fact_item_location reste un stub")
