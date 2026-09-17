// Databricks notebook source
// MAGIC %md
// MAGIC # Gold — stubs RAG
// MAGIC
// MAGIC Schema seulement, **aucun calcul** : le chunking et les embeddings sont
// MAGIC hors perimetre de ce tour (confirme avec l'utilisateur). Ces tables
// MAGIC existent pour que le schema cible soit visible/deployable des maintenant,
// MAGIC sans dependre d'un modele d'embedding ou d'une strategie de chunking pas
// MAGIC encore choisie.

// COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
val catalog = dbutils.widgets.get("catalog")
spark.sql(s"USE CATALOG $catalog")

// COMMAND ----------

spark.sql("""
  CREATE TABLE IF NOT EXISTS gold.rag_document (
    doc_id STRING NOT NULL, entity_id STRING, source STRING, source_url STRING,
    license STRING, lang STRING, title STRING, text STRING, metadata MAP<STRING, STRING>
  ) USING DELTA
  COMMENT 'Stub — chunking non implemente ce tour'
""")

spark.sql("""
  CREATE TABLE IF NOT EXISTS gold.rag_chunk (
    chunk_id STRING NOT NULL, doc_id STRING, entity_id STRING, entity_type STRING,
    chunk_index INT, text STRING, n_tokens INT, heading_path STRING, lang STRING, source_url STRING
  ) USING DELTA
  COMMENT 'Stub — chunking non implemente ce tour'
""")

spark.sql("""
  CREATE TABLE IF NOT EXISTS gold.rag_chunk_embedding (
    chunk_id STRING NOT NULL, embedding ARRAY<FLOAT>, model STRING
  ) USING DELTA
  COMMENT 'Stub — pas de modele d embedding retenu ce tour'
""")

println("OK — stubs RAG crees (schema uniquement)")
