// Databricks notebook source
// MAGIC %md
// MAGIC # Bronze — texte du jeu
// MAGIC
// MAGIC Source principale CloudModding (deja structuree par `text_id`/`section`
// MAGIC /`message`), plus une capture brute best-effort de Zelda Legends (page
// MAGIC HTML seule pour l'instant — voir la docstring de `game_text.py`).
// MAGIC Licence non precisee en amont : usage interne uniquement, jamais de
// MAGIC republication verbatim du script complet (`redistribution_ok = false`,
// MAGIC deja porte depuis l'extraction).

// COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
dbutils.widgets.text("landing_volume", "/Volumes/ocarina_dev/bronze/landing")

val catalog = dbutils.widgets.get("catalog")
val landingVolume = dbutils.widgets.get("landing_volume")

// COMMAND ----------

// MAGIC %run ./00_bronze_common

// COMMAND ----------

ingererBronze(
  cheminSource = s"$landingVolume/game_text/messages",
  tableCible = s"$catalog.bronze.game_text_messages",
  cheminSchema = s"$landingVolume/../_schemas/game_text_messages"
)

// COMMAND ----------

ingererBronze(
  cheminSource = s"$landingVolume/game_text/zeldalegends_raw",
  tableCible = s"$catalog.bronze.game_text_zeldalegends_raw",
  cheminSchema = s"$landingVolume/../_schemas/game_text_zeldalegends_raw"
)
