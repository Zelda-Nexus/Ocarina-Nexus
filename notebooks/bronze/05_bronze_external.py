# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze — Wikidata / Wikipedia
# MAGIC
# MAGIC CC0 / CC BY-SA 4.0 — librement redistribuable, cf. `config.SOURCE_LICENSES`.

# COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
dbutils.widgets.text("landing_volume", "/Volumes/ocarina_dev/bronze/landing")

catalog = dbutils.widgets.get("catalog")
landing_volume = dbutils.widgets.get("landing_volume")

# COMMAND ----------

# MAGIC %run ./00_bronze_common

# COMMAND ----------

ingerer_bronze(
    chemin_source=f"{landing_volume}/wikidata_wikipedia/wikidata_entities",
    table_cible=f"{catalog}.bronze.wikidata_entities",
    chemin_schema=f"{landing_volume}/_schemas/wikidata_entities",
    # `entity` est le payload Wikidata complet (labels, claims par code de
    # propriete P.., sitelinks...) : cles dynamiques a plusieurs niveaux,
    # bien pire que l'infobox. On le garde en JSON texte et on extrait au cas
    # par cas en Silver (get_json_object) plutot que de laisser l'inference
    # Auto Loader figer un struct geant sur l'echantillon.
    schema_hints="entity STRING",
)

# COMMAND ----------

ingerer_bronze(
    chemin_source=f"{landing_volume}/wikidata_wikipedia/wikipedia_articles",
    table_cible=f"{catalog}.bronze.wikipedia_articles",
    chemin_schema=f"{landing_volume}/_schemas/wikipedia_articles",
)
