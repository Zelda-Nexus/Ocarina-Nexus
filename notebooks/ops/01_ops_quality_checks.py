# Databricks notebook source
# MAGIC %md
# MAGIC # Ops — controles de qualite
# MAGIC
# MAGIC Rejoue apres chaque run Silver. N'echoue pas le job sur un controle
# MAGIC individuel (les resultats sont ecrits dans `ops.quality_checks` pour
# MAGIC inspection), sauf la contrainte NOT NULL sur `silver.entity`, qui casse
# MAGIC tout le reste en aval si elle est violee.

# COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
catalog = dbutils.widgets.get("catalog")
spark.sql(f"USE CATALOG {catalog}")

# COMMAND ----------

from pyspark.sql.functions import col, current_timestamp, datediff, explode, max as spark_max

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

resultats = []  # (check_name, table_name, passed, detail)

# COMMAND ----------

# MAGIC %md ## 1. NOT NULL / unicite sur `silver.entity`

# COMMAND ----------

entity = spark.table("silver.entity")

nul_entity_id = entity.where(
    col("entity_id").isNull() | col("title").isNull() | col("source_url").isNull()
).count()
resultats.append((
    "not_null_entity_core_fields", "silver.entity", nul_entity_id == 0,
    f"{nul_entity_id} ligne(s) avec entity_id/title/source_url NULL",
))

doublons_courants = (
    entity.where("is_current").groupBy("pageid").count().where(col("count") > 1).count()
)
resultats.append((
    "unicite_entity_courant", "silver.entity", doublons_courants == 0,
    f"{doublons_courants} pageid avec plus d'une version courante",
))

assert nul_entity_id == 0, "silver.entity viole une contrainte NOT NULL — arret avant Gold"

# COMMAND ----------

# MAGIC %md ## 2. Couverture — chaque categorie source a au moins une entite courante

# COMMAND ----------

categories_attendues = [
    "characters", "playable_characters", "bosses", "sub_bosses", "enemies", "species", "groups",
    "items", "items_3d", "objects", "locations", "dungeons", "abilities", "mechanics",
    "minigames", "interface", "plot_events", "services", "symbols",
]

categories_presentes = {
    r["entity_type"]
    for r in entity.where("is_current").select(explode(col("entity_types")).alias("entity_type")).distinct().collect()
}

categories_manquantes = [c for c in categories_attendues if c not in categories_presentes]
resultats.append((
    "couverture_categories", "silver.entity", len(categories_manquantes) == 0,
    "19/19 categories representees" if not categories_manquantes
    else f"categories sans entite : {', '.join(categories_manquantes)}",
))

# COMMAND ----------

# MAGIC %md ## 3. Fraicheur — age de la derniere ingestion par table Bronze

# COMMAND ----------

tables_bronze = [r["tableName"] for r in spark.sql("SHOW TABLES IN bronze").select("tableName").collect()]

for table in tables_bronze:
    age_row = (
        spark.table(f"bronze.{table}")
        .agg(spark_max("_ingest_ts").alias("m"))
        .select(datediff(current_timestamp(), col("m")).alias("age_jours"))
        .head()
    )
    age_jours = age_row["age_jours"] if age_row["age_jours"] is not None else -1
    resultats.append((
        "fraicheur_bronze", f"bronze.{table}", age_jours >= 0,
        f"derniere ingestion il y a {age_jours} jour(s)",
    ))

# COMMAND ----------

# MAGIC %md ## Ecriture des resultats

# COMMAND ----------

df = (
    spark.createDataFrame(resultats, ["check_name", "table_name", "passed", "detail"])
    .withColumn("checked_at", current_timestamp())
    .select("checked_at", "check_name", "table_name", "passed", "detail")
)

df.write.mode("append").saveAsTable("ops.quality_checks")

echecs = sum(1 for r in resultats if not r[2])
print(f"OK — {len(resultats)} controle(s), {echecs} en echec")
display(df)
