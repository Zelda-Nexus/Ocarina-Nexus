# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze — speedrun.com
# MAGIC
# MAGIC CC BY-NC 4.0 (`redistribution_ok = false`, deja porte depuis
# MAGIC l'extraction) : donnees exploitables pour l'IA/le site en interne, a
# MAGIC retirer si le projet devient jamais commercial.

# COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
dbutils.widgets.text("landing_volume", "/Volumes/ocarina_dev/bronze/landing")

catalog = dbutils.widgets.get("catalog")
landing_volume = dbutils.widgets.get("landing_volume")

# COMMAND ----------

# MAGIC %run ./00_bronze_common

# COMMAND ----------

for entite in ["categories", "levels", "variables", "leaderboards"]:
    ingerer_bronze(
        chemin_source=f"{landing_volume}/speedrun_com/{entite}",
        table_cible=f"{catalog}.bronze.speedrun_{entite}",
        chemin_schema=f"{landing_volume}/_schemas/speedrun_{entite}",
    )
