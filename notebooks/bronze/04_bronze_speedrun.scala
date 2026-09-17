// Databricks notebook source
// MAGIC %md
// MAGIC # Bronze — speedrun.com
// MAGIC
// MAGIC CC BY-NC 4.0 (`redistribution_ok = false`, deja porte depuis
// MAGIC l'extraction) : donnees exploitables pour l'IA/le site en interne, a
// MAGIC retirer si le projet devient jamais commercial.

// COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
dbutils.widgets.text("landing_volume", "/Volumes/ocarina_dev/bronze/landing")

val catalog = dbutils.widgets.get("catalog")
val landingVolume = dbutils.widgets.get("landing_volume")

// COMMAND ----------

// MAGIC %run ./00_bronze_common

// COMMAND ----------

Seq("categories", "levels", "variables", "leaderboards").foreach { entite =>
  ingererBronze(
    cheminSource = s"$landingVolume/speedrun_com/$entite",
    tableCible = s"$catalog.bronze.speedrun_$entite",
    cheminSchema = s"$landingVolume/../_schemas/speedrun_$entite"
  )
}
