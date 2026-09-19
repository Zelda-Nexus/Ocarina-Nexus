# Databricks notebook source
# MAGIC %md
# MAGIC # Bronze — utilitaires communs
# MAGIC
# MAGIC Inclus via `%run` par chaque notebook `NN_bronze_*.py`. Une seule
# MAGIC fonction : `ingerer_bronze`, qui applique la meme discipline partout —
# MAGIC lecture Auto Loader, colonnes `_ingest_ts` / `_source_file` / `_raw`,
# MAGIC ecriture **append-only** (jamais de merge/overwrite/delete en bronze,
# MAGIC voir `docs/architecture.md`).
# MAGIC
# MAGIC PySpark plutot que Scala (cf. ADR 0004) : le workspace Free Edition ne
# MAGIC provisionne que du compute serverless, qui ne supporte pas Scala.
# MAGIC
# MAGIC `_raw` est une reconstruction JSON du contenu recu (`to_json` sur les
# MAGIC colonnes metier, avant l'ajout des colonnes techniques) : le contenu
# MAGIC est fidele a ce que l'extraction Python a ecrit, mais la mise en forme
# MAGIC texte (ordre des cles, espaces) peut differer de l'octet-pres du fichier
# MAGIC JSONL d'origine, qui lui reste disponible indefiniment sur le volume de
# MAGIC landing (point de rejeu ultime, jamais purge).

# COMMAND ----------

from pyspark.sql.functions import col, current_timestamp, struct, to_json


def ingerer_bronze(
    chemin_source: str,
    table_cible: str,
    chemin_schema: str,
    schema_hints: str = "",
) -> None:
    """Ingere un sous-repertoire du volume de landing dans une table Delta Bronze.

    chemin_source: ex. f"{landing_volume}/zeldawiki/characters"
    table_cible: ex. f"{catalog}.bronze.zeldawiki_pages"
    chemin_schema: emplacement de suivi de schema Auto Loader (un par table)
    schema_hints: force le type de certaines colonnes plutot que de laisser
        l'inference JSON deviner (ex. "infobox MAP<STRING,STRING>").
        Necessaire pour tout champ objet a cles dynamiques (l'infobox change
        de champs selon le type d'entite) : sans ca, l'inference cree un
        struct fige sur l'echantillon et casse a la premiere cle nouvelle.
    """
    lecteur = (
        spark.readStream.format("cloudFiles")
        .option("cloudFiles.format", "json")
        .option("cloudFiles.schemaLocation", chemin_schema)
        .option("cloudFiles.inferColumnTypes", "true")
        .option("multiLine", "false")  # JSONL : un objet JSON par ligne
    )

    if schema_hints:
        lecteur = lecteur.option("cloudFiles.schemaHints", schema_hints)

    brut = lecteur.load(chemin_source)

    colonnes_metier = [c for c in brut.columns if not c.startswith("_")]

    enveloppe = (
        brut.withColumn("_raw", to_json(struct(*[col(c) for c in colonnes_metier])))
        .withColumn("_ingest_ts", current_timestamp())
        # input_file_name() n'est pas supporte par Unity Catalog sur serverless ;
        # la colonne cachee _metadata.file_path est l'equivalent recommande.
        .withColumn("_source_file", col("_metadata.file_path"))
    )

    (
        enveloppe.writeStream.format("delta")
        .option("checkpointLocation", f"{chemin_schema}/_checkpoint")
        .trigger(availableNow=True)
        .toTable(table_cible)
        .awaitTermination()
    )

    print(f"OK — {table_cible} <- {chemin_source}")
