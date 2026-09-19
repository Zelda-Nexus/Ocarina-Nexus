# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze — donnees techniques (decomp zeldaret/oot + monde logique OoT-Randomizer)
# MAGIC
# MAGIC L'extraction Python capture ces deux sources **en texte brut** (fichiers
# MAGIC `.h` du decomp, modules `.py` executables du randomizer) plutot que
# MAGIC deja decoupees en lignes `actor_table`/`rando_location`/etc. — voir les
# MAGIC docstrings de `zeldaret_oot_github.py` et `oot_randomizer_github.py`.
# MAGIC Le parsing regex/AST qui explose ces blobs en tables typees
# MAGIC (`silver.actor`, `silver.rando_region`, ...) est un travail de Silver :
# MAGIC une regle de parsing amelioree se rejoue depuis Bronze, jamais depuis
# MAGIC GitHub.

# COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
dbutils.widgets.text("landing_volume", "/Volumes/ocarina_dev/bronze/landing")

catalog = dbutils.widgets.get("catalog")
landing_volume = dbutils.widgets.get("landing_volume")

# COMMAND ----------

# MAGIC %run ./00_bronze_common

# COMMAND ----------

ingerer_bronze(
    chemin_source=f"{landing_volume}/technical/zeldaret_oot_tables",
    table_cible=f"{catalog}.bronze.decomp_tables_raw",
    chemin_schema=f"{landing_volume}/_schemas/decomp_tables_raw",
)

# COMMAND ----------

ingerer_bronze(
    chemin_source=f"{landing_volume}/technical/oot_randomizer_world",
    table_cible=f"{catalog}.bronze.rando_world_raw",
    chemin_schema=f"{landing_volume}/_schemas/rando_world_raw",
    # events/locations/exits sont des maps a cles dynamiques (nom d'evenement,
    # de lieu, de region voisine) : meme risque que l'infobox Zelda Wiki.
    schema_hints=(
        "entries.element.events MAP<STRING,STRING>, "
        "entries.element.locations MAP<STRING,STRING>, "
        "entries.element.exits MAP<STRING,STRING>"
    ),
)

# COMMAND ----------

ingerer_bronze(
    chemin_source=f"{landing_volume}/technical/oot_randomizer_modules",
    table_cible=f"{catalog}.bronze.rando_modules_raw",
    chemin_schema=f"{landing_volume}/_schemas/rando_modules_raw",
)
