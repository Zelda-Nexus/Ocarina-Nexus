// Databricks notebook source
// MAGIC %md
// MAGIC # Bronze — Wikidata / Wikipedia
// MAGIC
// MAGIC CC0 / CC BY-SA 4.0 — librement redistribuable, cf. `config.SOURCE_LICENSES`.

// COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
dbutils.widgets.text("landing_volume", "/Volumes/ocarina_dev/bronze/landing")

val catalog = dbutils.widgets.get("catalog")
val landingVolume = dbutils.widgets.get("landing_volume")

// COMMAND ----------

// MAGIC %run ./00_bronze_common

// COMMAND ----------

ingererBronze(
  cheminSource = s"$landingVolume/wikidata_wikipedia/wikidata_entities",
  tableCible = s"$catalog.bronze.wikidata_entities",
  cheminSchema = s"$landingVolume/../_schemas/wikidata_entities",
  // `entity` est le payload Wikidata complet (labels, claims par code de
  // propriete P.., sitelinks...) : cles dynamiques a plusieurs niveaux,
  // bien pire que l'infobox. On le garde en JSON texte et on extrait au cas
  // par cas en Silver (get_json_object) plutot que de laisser l'inference
  // Auto Loader figer un struct geant sur l'echantillon.
  schemaHints = "entity STRING"
)

// COMMAND ----------

ingererBronze(
  cheminSource = s"$landingVolume/wikidata_wikipedia/wikipedia_articles",
  tableCible = s"$catalog.bronze.wikipedia_articles",
  cheminSchema = s"$landingVolume/../_schemas/wikipedia_articles"
)
