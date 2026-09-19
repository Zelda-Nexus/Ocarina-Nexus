# Databricks notebook source
# MAGIC %md
# MAGIC # Silver — entites encyclopediques (Zelda Wiki)
# MAGIC
# MAGIC Depuis `bronze.zeldawiki_pages` (une ligne par page x categorie) :
# MAGIC - `silver.entity` : une ligne par page, `entity_types` fusionne, avec
# MAGIC   historisation SCD2 sur `lastrevid` (`valid_from`/`valid_to`/`is_current`) ;
# MAGIC - `silver.entity_infobox_kv`, `entity_category`, `entity_link`,
# MAGIC   `entity_image`, `entity_section` : eclatement des colonnes imbriquees,
# MAGIC   cle etrangere `pageid` + `lastrevid` vers la version courante de `entity`.
# MAGIC
# MAGIC Rejouable integralement depuis Bronze : aucune de ces tables ne lit
# MAGIC autre chose que `bronze.zeldawiki_pages`.

# COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
catalog = dbutils.widgets.get("catalog")
spark.sql(f"USE CATALOG {catalog}")
spark.sql("USE SCHEMA silver")

# COMMAND ----------

import re

from pyspark.sql.functions import (
    array_distinct,
    col,
    collect_list,
    explode_outer,
    first,
    flatten,
    lit,
    posexplode_outer,
    udf,
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Creation des tables (une seule fois — DDL explicite, pas d'inference au vol)

# COMMAND ----------

spark.sql("""
  CREATE TABLE IF NOT EXISTS silver.entity (
    pageid           BIGINT NOT NULL,
    entity_id        STRING NOT NULL COMMENT 'slug stable derive du titre',
    entity_types     ARRAY<STRING>,
    title            STRING NOT NULL,
    displaytitle     STRING,
    lastrevid        BIGINT,
    touched          STRING,
    summary          STRING,
    plaintext        STRING,
    wikitext         STRING,
    source_url       STRING NOT NULL,
    license          STRING,
    valid_from       TIMESTAMP NOT NULL,
    valid_to         TIMESTAMP,
    is_current       BOOLEAN NOT NULL
  )
  USING DELTA
  COMMENT 'Une ligne par page Zelda Wiki, historisee SCD2 sur lastrevid'
""")

spark.sql("""
  CREATE TABLE IF NOT EXISTS silver.entity_infobox_kv (
    pageid STRING, key STRING, value STRING
  ) USING DELTA
""")
spark.sql("CREATE TABLE IF NOT EXISTS silver.entity_category (pageid STRING, category STRING, hidden BOOLEAN) USING DELTA")
spark.sql("CREATE TABLE IF NOT EXISTS silver.entity_link (from_pageid STRING, to_title STRING) USING DELTA")
spark.sql("CREATE TABLE IF NOT EXISTS silver.entity_image (pageid STRING, file_title STRING) USING DELTA")
spark.sql("""
  CREATE TABLE IF NOT EXISTS silver.entity_section (
    pageid STRING, section_index INT, level STRING, heading STRING, anchor STRING
  ) USING DELTA
""")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Collapse des doublons de categorie + fusion `entity_types`

# COMMAND ----------

bronze = spark.table("bronze.zeldawiki_pages")


@udf("string")
def slugify(titre):
    if titre is None:
        return None
    s = titre.lower()
    s = re.sub(r"[’']", "", s)
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return re.sub(r"^_|_$", "", s)


nouvelles = (
    bronze.groupBy("pageid", "lastrevid")
    .agg(
        array_distinct(flatten(collect_list("entity_types"))).alias("entity_types"),
        first("title", ignorenulls=True).alias("title"),
        first("displaytitle", ignorenulls=True).alias("displaytitle"),
        first("touched", ignorenulls=True).alias("touched"),
        first("description", ignorenulls=True).alias("summary"),
        first("plaintext", ignorenulls=True).alias("plaintext"),
        first("wikitext", ignorenulls=True).alias("wikitext"),
        first("url", ignorenulls=True).alias("source_url"),
        first("infobox", ignorenulls=True).alias("infobox"),
        first("categories", ignorenulls=True).alias("categories"),
        first("hidden_categories", ignorenulls=True).alias("hidden_categories"),
        first("links", ignorenulls=True).alias("links"),
        first("images", ignorenulls=True).alias("images"),
        first("sections", ignorenulls=True).alias("sections"),
    )
    .withColumn("entity_id", slugify(col("title")))
    .withColumn("license", lit("CC BY-NC-SA 3.0"))
)

nouvelles.createOrReplaceTempView("nouvelles_entites")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. SCD2 : cloture des versions perimees, insertion des nouvelles

# COMMAND ----------

spark.sql("""
  MERGE INTO entity AS cible
  USING nouvelles_entites AS source
  ON cible.pageid = source.pageid AND cible.is_current = true AND cible.lastrevid <> source.lastrevid
  WHEN MATCHED THEN UPDATE SET cible.valid_to = current_timestamp(), cible.is_current = false
""")

spark.sql("""
  MERGE INTO entity AS cible
  USING nouvelles_entites AS source
  ON cible.pageid = source.pageid AND cible.lastrevid = source.lastrevid
  WHEN NOT MATCHED THEN INSERT (
    pageid, entity_id, entity_types, title, displaytitle, lastrevid, touched,
    summary, plaintext, wikitext, source_url, license, valid_from, valid_to, is_current
  ) VALUES (
    source.pageid, source.entity_id, source.entity_types, source.title, source.displaytitle,
    source.lastrevid, source.touched, source.summary, source.plaintext, source.wikitext,
    source.source_url, source.license, current_timestamp(), NULL, true
  )
""")

print(f"OK — silver.entity : {spark.table('entity').where('is_current').count()} entites courantes")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Tables satellites (rejouees en entier a chaque run depuis `nouvelles`)

# COMMAND ----------

(
    nouvelles.select(col("pageid").cast("string"), explode_outer(col("infobox")).alias("key", "value"))
    .write.mode("overwrite")
    .saveAsTable("entity_infobox_kv")
)

(
    nouvelles.select(
        col("pageid").cast("string"),
        explode_outer(col("categories")).alias("category"),
        lit(False).alias("hidden"),
    )
    .unionByName(
        nouvelles.select(
            col("pageid").cast("string"),
            explode_outer(col("hidden_categories")).alias("category"),
            lit(True).alias("hidden"),
        )
    )
    .where(col("category").isNotNull())
    .write.mode("overwrite")
    .saveAsTable("entity_category")
)

(
    nouvelles.select(col("pageid").cast("string").alias("from_pageid"), explode_outer(col("links")).alias("to_title"))
    .where(col("to_title").isNotNull())
    .write.mode("overwrite")
    .saveAsTable("entity_link")
)

(
    nouvelles.select(col("pageid").cast("string"), explode_outer(col("images")).alias("file_title"))
    .where(col("file_title").isNotNull())
    .write.mode("overwrite")
    .saveAsTable("entity_image")
)

(
    nouvelles.select(col("pageid").cast("string"), posexplode_outer(col("sections")).alias("section_index", "section"))
    .select(
        col("pageid"),
        col("section_index"),
        col("section.level").alias("level"),
        col("section.line").alias("heading"),
        col("section.anchor").alias("anchor"),
    )
    .where(col("heading").isNotNull())
    .write.mode("overwrite")
    .saveAsTable("entity_section")
)

print("OK — tables satellites (infobox_kv, category, link, image, section) rafraichies")
