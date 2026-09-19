# Databricks notebook source
# MAGIC %md
# MAGIC # Silver — speedrun.com
# MAGIC
# MAGIC `bronze.speedrun_leaderboards` a une ligne par (categorie, niveau) avec
# MAGIC un tableau `runs` imbrique ; on l'eclate en une ligne par run classee.

# COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
catalog = dbutils.widgets.get("catalog")
spark.sql(f"USE CATALOG {catalog}")
spark.sql("USE SCHEMA silver")

# COMMAND ----------

from pyspark.sql.functions import col, explode

# COMMAND ----------

spark.sql("""
  CREATE TABLE IF NOT EXISTS silver.speedrun_category (
    category_id STRING NOT NULL, name STRING, type STRING
  ) USING DELTA
""")

(
    spark.table("bronze.speedrun_categories")
    .select(col("id").alias("category_id"), col("name"), col("type"))
    .distinct()
    .write.mode("overwrite")
    .saveAsTable("speedrun_category")
)

# COMMAND ----------

spark.sql("""
  CREATE TABLE IF NOT EXISTS silver.speedrun_run (
    run_id STRING NOT NULL,
    category_id STRING,
    category_name STRING,
    level_id STRING,
    level_name STRING,
    place INT,
    time_seconds DOUBLE,
    platform STRING,
    video_url STRING,
    comment STRING
  ) USING DELTA
""")

runs_eclates = spark.table("bronze.speedrun_leaderboards").select(
    col("category_id"), col("category_name"), col("level_id"), col("level_name"),
    explode(col("runs")).alias("entry"),
)

(
    runs_eclates.select(
        col("entry.run.id").alias("run_id"),
        col("category_id"), col("category_name"), col("level_id"), col("level_name"),
        col("entry.place").cast("int").alias("place"),
        col("entry.run.times.primary_t").alias("time_seconds"),
        col("entry.run.system.platform").alias("platform"),
        col("entry.run.videos.links")[0]["uri"].alias("video_url"),
        col("entry.run.comment").alias("comment"),
    )
    .where(col("run_id").isNotNull())
    .write.mode("overwrite")
    .saveAsTable("speedrun_run")
)

print(f"OK — silver.speedrun_run : {spark.table('speedrun_run').count()} runs")
