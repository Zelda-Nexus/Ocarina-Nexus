// Databricks notebook source
// MAGIC %md
// MAGIC # Ops — controles de qualite
// MAGIC
// MAGIC Rejoue apres chaque run Silver. N'echoue pas le job sur un controle
// MAGIC individuel (les resultats sont ecrits dans `ops.quality_checks` pour
// MAGIC inspection), sauf la contrainte NOT NULL sur `silver.entity`, qui casse
// MAGIC tout le reste en aval si elle est violee.

// COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
val catalog = dbutils.widgets.get("catalog")
spark.sql(s"USE CATALOG $catalog")

// COMMAND ----------

import org.apache.spark.sql.functions._
import spark.implicits._

spark.sql("""
  CREATE TABLE IF NOT EXISTS ops.quality_checks (
    checked_at TIMESTAMP,
    check_name STRING,
    table_name STRING,
    passed     BOOLEAN,
    detail     STRING
  ) USING DELTA
  COMMENT 'Historique des controles de qualite Silver/Gold'
""")

case class Controle(nom: String, table: String, ok: Boolean, detail: String)
val resultats = scala.collection.mutable.ArrayBuffer.empty[Controle]

// COMMAND ----------

// MAGIC %md ## 1. NOT NULL / unicite sur `silver.entity`

// COMMAND ----------

val entity = spark.table("silver.entity")

val nulEntityId = entity.where(col("entity_id").isNull || col("title").isNull || col("source_url").isNull).count()
resultats += Controle("not_null_entity_core_fields", "silver.entity", nulEntityId == 0, s"$nulEntityId ligne(s) avec entity_id/title/source_url NULL")

val doublonsCourants = entity.where("is_current")
  .groupBy("pageid").count().where(col("count") > 1).count()
resultats += Controle("unicite_entity_courant", "silver.entity", doublonsCourants == 0, s"$doublonsCourants pageid avec plus d'une version courante")

assert(nulEntityId == 0, "silver.entity viole une contrainte NOT NULL — arret avant Gold")

// COMMAND ----------

// MAGIC %md ## 2. Couverture — chaque categorie source a au moins une entite courante

// COMMAND ----------

val categoriesAttendues = Seq(
  "characters", "playable_characters", "bosses", "sub_bosses", "enemies", "species", "groups",
  "items", "items_3d", "objects", "locations", "dungeons", "abilities", "mechanics",
  "minigames", "interface", "plot_events", "services", "symbols"
)

val categoriesPresentes = entity.where("is_current")
  .select(explode(col("entity_types")).as("entity_type"))
  .distinct().as[String].collect().toSet

val categoriesManquantes = categoriesAttendues.filterNot(categoriesPresentes.contains)
resultats += Controle(
  "couverture_categories",
  "silver.entity",
  categoriesManquantes.isEmpty,
  if (categoriesManquantes.isEmpty) "19/19 categories representees"
  else s"categories sans entite : ${categoriesManquantes.mkString(", ")}"
)

// COMMAND ----------

// MAGIC %md ## 3. Fraicheur — age de la derniere ingestion par table Bronze

// COMMAND ----------

val tablesBronze = spark.sql("SHOW TABLES IN bronze").select("tableName").as[String].collect()

tablesBronze.foreach { table =>
  val dernierIngestRow = spark.table(s"bronze.$table").agg(max("_ingest_ts").as("m")).head()
  val dernierIngest = Option(dernierIngestRow.getAs[java.sql.Timestamp]("m"))
  val ageJours = dernierIngest.map(ts => (System.currentTimeMillis() - ts.getTime) / 86400000).getOrElse(-1L)
  resultats += Controle("fraicheur_bronze", s"bronze.$table", ageJours >= 0, s"derniere ingestion il y a $ageJours jour(s)")
}

// COMMAND ----------

// MAGIC %md ## Ecriture des resultats

// COMMAND ----------

val maintenant = current_timestamp()
val df = resultats.toSeq.toDF("check_name", "table_name", "passed", "detail")
  .withColumn("checked_at", maintenant)
  .select("checked_at", "check_name", "table_name", "passed", "detail")

df.write.mode("append").saveAsTable("ops.quality_checks")

val echecs = resultats.count(!_.ok)
println(s"OK — ${resultats.size} controle(s), $echecs en echec")
display(df)
