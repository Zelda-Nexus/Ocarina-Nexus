# Databricks notebook source
# MAGIC %md
# MAGIC # Gold — faits, dont la fusion a l'origine du graphe de connaissances
# MAGIC
# MAGIC `fact_entity_relation` fusionne les signaux disponibles aujourd'hui :
# MAGIC 1. infobox structuree (`Location` -> `located_in`, `Race` -> `is_species`) ;
# MAGIC 2. liens wiki (`silver.entity_link`), type `related_to`, ponderes par
# MAGIC    occurrence ;
# MAGIC 3. graphe de regions du randomizer (`rando_region_exit`), rapproche des
# MAGIC    entites de type `locations` par correspondance approximative de nom
# MAGIC    (mise en minuscule + ponctuation retiree) — imprecis par construction,
# MAGIC    documente comme tel plutot que cache.
# MAGIC
# MAGIC La correspondance scene/entrance/actor (4e signal du schema cible §3.3)
# MAGIC n'a pas de cle de jointure fiable identifiee pour l'instant : laissee pour
# MAGIC un futur notebook plutot que d'inventer un rapprochement hasardeux.

# COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
catalog = dbutils.widgets.get("catalog")
spark.sql(f"USE CATALOG {catalog}")

# COMMAND ----------

from pyspark.sql.functions import col, count, expr, lit, lower, regexp_replace


def slug_key(c):
    return lower(regexp_replace(c, "[^A-Za-z0-9]+", "_"))


entity = spark.table("silver.entity").where("is_current").select(col("pageid"), col("entity_id"), col("title"), col("source_url"))

# COMMAND ----------

# MAGIC %md ## fact_entity_relation

# COMMAND ----------

spark.sql("""
  CREATE TABLE IF NOT EXISTS gold.fact_entity_relation (
    from_id STRING NOT NULL, to_id STRING, to_title_raw STRING,
    relation_type STRING NOT NULL, weight INT, evidence_source STRING, evidence_url STRING
  ) USING DELTA
""")

# Signal 1 — infobox
relations_infobox = (
    spark.table("silver.entity_infobox_kv")
    .where(col("key").isin(["Location", "Race", "Dungeon", "Boss"]))
    .join(entity.withColumnRenamed("pageid", "pageid_src"), col("pageid") == col("pageid_src"))
    .withColumn(
        "relation_type",
        expr("""
          CASE key
            WHEN 'Location' THEN 'located_in'
            WHEN 'Race' THEN 'is_species'
            WHEN 'Dungeon' THEN 'located_in'
            WHEN 'Boss' THEN 'boss_of'
          END
        """),
    )
    .join(
        entity.select(col("entity_id").alias("to_id"), slug_key(col("title")).alias("_join_key")),
        slug_key(col("value")) == col("_join_key"),
        "left",
    )
    .select(
        col("entity_id").alias("from_id"), col("to_id"), col("value").alias("to_title_raw"),
        col("relation_type"), lit(1).alias("weight"),
        lit("zeldawiki_infobox").alias("evidence_source"), col("source_url").alias("evidence_url"),
    )
)

# Signal 2 — liens wiki, pondere par occurrence
entity_link = (
    spark.table("silver.entity_link")
    .join(entity.withColumnRenamed("pageid", "from_pageid_join"), col("from_pageid") == col("from_pageid_join"))
    .groupBy(col("entity_id").alias("from_id"), col("to_title"))
    .agg(count("*").cast("int").alias("weight"))
)

relations_liens = (
    entity_link.join(
        entity.select(col("entity_id").alias("to_id"), col("title").alias("_to_title_exact")),
        col("to_title") == col("_to_title_exact"),
        "left",
    ).select(
        col("from_id"), col("to_id"), col("to_title").alias("to_title_raw"),
        lit("related_to").alias("relation_type"), col("weight"),
        lit("zeldawiki_links").alias("evidence_source"), lit(None).cast("string").alias("evidence_url"),
    )
)

# Signal 3 — graphe de regions du randomizer, rapproche par nom approximatif
entites_lieux = entity.withColumn("_join_key", slug_key(col("title")))

relations_rando = (
    spark.table("silver.rando_region_exit")
    .withColumn("_from_key", slug_key(col("from_region")))
    .withColumn("_to_key", slug_key(col("to_region")))
    .join(entites_lieux.select(col("entity_id").alias("from_id"), col("_join_key").alias("_from_key")), "_from_key")
    .join(entites_lieux.select(col("entity_id").alias("to_id"), col("_join_key").alias("_to_key")), "_to_key")
    .select(
        col("from_id"), col("to_id"), col("to_region").alias("to_title_raw"),
        lit("adjacent_to").alias("relation_type"), lit(1).alias("weight"),
        lit("oot_randomizer_region_graph").alias("evidence_source"),
        lit("https://github.com/OoTRandomizer/OoT-Randomizer/tree/Dev/data/World").alias("evidence_url"),
    )
)

toutes_relations = relations_infobox.unionByName(relations_liens).unionByName(relations_rando)
toutes_relations.write.mode("overwrite").saveAsTable("gold.fact_entity_relation")

print(
    f"OK — gold.fact_entity_relation : {toutes_relations.count()} relations "
    f"(infobox={relations_infobox.count()}, liens={relations_liens.count()}, rando={relations_rando.count()})"
)

# COMMAND ----------

# MAGIC %md ## fact_speedrun_record, bridge_entity_message, fact_item_location (stub)

# COMMAND ----------

spark.sql("DROP TABLE IF EXISTS gold.fact_speedrun_record")
(
    spark.table("silver.speedrun_run")
    .join(spark.table("silver.speedrun_category"), "category_id", "left")
    .select(col("run_id"), col("category_id"), col("name").alias("category_name"), col("level_name"), col("place"), col("time_seconds"), col("platform"), col("video_url"))
    .write.mode("overwrite")
    .saveAsTable("gold.fact_speedrun_record")
)

# COMMAND ----------

spark.sql("DROP TABLE IF EXISTS gold.bridge_entity_message")
# Rapprochement par occurrence du titre de l'entite dans le texte du message —
# heuristique simple (nom exact, sensible a la casse) ; a affiner (NER,
# alias multilingues via entity_name_i18n une fois peuple) sans re-scraper.
(
    spark.table("silver.game_message")
    .crossJoin(entity)
    .where(col("text").contains(col("title")))
    .select(col("entity_id"), col("message_key"), col("text_id"), col("lang"))
    .write.mode("overwrite")
    .saveAsTable("gold.bridge_entity_message")
)

# COMMAND ----------

spark.sql("""
  CREATE TABLE IF NOT EXISTS gold.fact_item_location (
    item_entity_id STRING, location_name STRING, rule_expr STRING
  ) USING DELTA
  COMMENT 'Stub — depend de silver.rando_location, non peuple tant que le parseur AST de LocationList.py nexiste pas'
""")

print("OK — fact_speedrun_record, bridge_entity_message ecrits ; fact_item_location reste un stub")
