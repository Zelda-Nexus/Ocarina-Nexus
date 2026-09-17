// Databricks notebook source
// MAGIC %md
// MAGIC # Bronze — utilitaires communs
// MAGIC
// MAGIC Inclus via `%run` par chaque notebook `NN_bronze_*.scala`. Une seule
// MAGIC fonction : `ingererBronze`, qui applique la meme discipline partout —
// MAGIC lecture Auto Loader, colonnes `_ingest_ts` / `_source_file` / `_raw`,
// MAGIC ecriture **append-only** (jamais de merge/overwrite/delete en bronze,
// MAGIC voir `docs/architecture.md`).
// MAGIC
// MAGIC `_raw` est une reconstruction JSON du contenu recu (`to_json` sur les
// MAGIC colonnes metier, avant l'ajout des colonnes techniques) : le contenu
// MAGIC est fidele a ce que l'extraction Python a ecrit, mais la mise en forme
// MAGIC texte (ordre des cles, espaces) peut differer de l'octet-pres du fichier
// MAGIC JSONL d'origine, qui lui reste disponible indefiniment sur le volume de
// MAGIC landing (point de rejeu ultime, jamais purge).

// COMMAND ----------

import org.apache.spark.sql.functions.{col, current_timestamp, input_file_name, struct, to_json}
import org.apache.spark.sql.streaming.Trigger

/** Ingere un sous-repertoire du volume de landing dans une table Delta Bronze.
  *
  * @param cheminSource   ex. s"$$landingVolume/zeldawiki/characters"
  * @param tableCible     ex. s"$$catalog.bronze.zeldawiki_pages"
  * @param cheminSchema   emplacement de suivi de schema Auto Loader (un par table)
  * @param schemaHints    force le type de certaines colonnes plutot que de
  *                       laisser l'inference JSON deviner (ex. `"infobox MAP<STRING,STRING>"`).
  *                       Necessaire pour tout champ objet a cles dynamiques
  *                       (l'infobox change de champs selon le type d'entite) :
  *                       sans ca, l'inference cree un struct fige sur
  *                       l'echantillon et casse a la premiere cle nouvelle.
  */
def ingererBronze(
    cheminSource: String,
    tableCible: String,
    cheminSchema: String,
    schemaHints: String = ""
): Unit = {
  var lecteur = spark.readStream
    .format("cloudFiles")
    .option("cloudFiles.format", "json")
    .option("cloudFiles.schemaLocation", cheminSchema)
    .option("cloudFiles.inferColumnTypes", "true")
    .option("multiLine", "false") // JSONL : un objet JSON par ligne

  if (schemaHints.nonEmpty) {
    lecteur = lecteur.option("cloudFiles.schemaHints", schemaHints)
  }

  val brut = lecteur.load(cheminSource)

  val colonnesMetier = brut.columns.filterNot(_.startsWith("_"))

  val enveloppe = brut
    .withColumn("_raw", to_json(struct(colonnesMetier.map(col): _*)))
    .withColumn("_ingest_ts", current_timestamp())
    .withColumn("_source_file", input_file_name())

  enveloppe.writeStream
    .format("delta")
    .option("checkpointLocation", s"$cheminSchema/_checkpoint")
    .trigger(Trigger.AvailableNow())
    .toTable(tableCible)
    .awaitTermination()

  println(s"OK — $tableCible <- $cheminSource")
}
