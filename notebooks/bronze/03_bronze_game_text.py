# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze — texte du jeu
# MAGIC
# MAGIC Source principale CloudModding (deja structuree par `text_id`/`section`
# MAGIC /`message`), plus une capture brute best-effort de Zelda Legends (page
# MAGIC HTML seule pour l'instant — voir la docstring de `game_text.py`).
# MAGIC Licence non precisee en amont : usage interne uniquement, jamais de
# MAGIC republication verbatim du script complet (`redistribution_ok = false`,
# MAGIC deja porte depuis l'extraction).

# COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
dbutils.widgets.text("landing_volume", "/Volumes/ocarina_dev/bronze/landing")

catalog = dbutils.widgets.get("catalog")
landing_volume = dbutils.widgets.get("landing_volume")

# COMMAND ----------

# MAGIC %run ./00_bronze_common

# COMMAND ----------

ingerer_bronze(
    chemin_source=f"{landing_volume}/game_text/messages",
    table_cible=f"{catalog}.bronze.game_text_messages",
    chemin_schema=f"{landing_volume}/_schemas/game_text_messages",
)

# COMMAND ----------

ingerer_bronze(
    chemin_source=f"{landing_volume}/game_text/zeldalegends_raw",
    table_cible=f"{catalog}.bronze.game_text_zeldalegends_raw",
    chemin_schema=f"{landing_volume}/_schemas/game_text_zeldalegends_raw",
)
