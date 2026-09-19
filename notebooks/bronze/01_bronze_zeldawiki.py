# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze — Zelda Wiki (pages + tables Cargo)
# MAGIC
# MAGIC Deux familles de tables Bronze :
# MAGIC - `bronze.zeldawiki_pages` : toutes les pages, toutes categories confondues
# MAGIC   (`entity_types` en distingue le type ; une page peut y apparaitre
# MAGIC   plusieurs fois, une fois par categorie extraite — la deduplication est
# MAGIC   un travail de Silver, pas de Bronze).
# MAGIC - `bronze.zeldawiki_cargo_<table>` : une table par table Cargo source.

# COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
dbutils.widgets.text("landing_volume", "/Volumes/ocarina_dev/bronze/landing")

catalog = dbutils.widgets.get("catalog")
landing_volume = dbutils.widgets.get("landing_volume")

# COMMAND ----------

# MAGIC %run ./00_bronze_common

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pages (les 19 categories, un seul repertoire glob)

# COMMAND ----------

ingerer_bronze(
    chemin_source=f"{landing_volume}/zeldawiki/*",
    table_cible=f"{catalog}.bronze.zeldawiki_pages",
    chemin_schema=f"{landing_volume}/_schemas/zeldawiki_pages",
    # infobox a des cles differentes selon le type d'entite (race pour un
    # personnage, prix pour un objet...) : sans ce hint, l'inference JSON fige
    # un struct sur l'echantillon et casse a la premiere cle non vue.
    schema_hints="infobox MAP<STRING,STRING>",
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Tables Cargo (une table Bronze par table Cargo)

# COMMAND ----------

tables_cargo = [
    "nomenclature",
    "terminologies",
    "files",
    "locationfeatures",
    "descriptions",
    "wares",
    "gamelanguages",
]

for table in tables_cargo:
    ingerer_bronze(
        chemin_source=f"{landing_volume}/zeldawiki_cargo/{table}",
        table_cible=f"{catalog}.bronze.zeldawiki_cargo_{table}",
        chemin_schema=f"{landing_volume}/_schemas/zeldawiki_cargo_{table}",
    )
