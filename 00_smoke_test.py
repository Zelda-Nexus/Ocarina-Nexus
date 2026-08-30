# Databricks notebook source
# MAGIC %md
# MAGIC # Smoke test — Ocarina Nexus
# MAGIC
# MAGIC Ce notebook ne contient aucune logique metier. Il repond a une seule
# MAGIC question : **est-ce que la plateforme est correctement cablee ?**
# MAGIC
# MAGIC 1. Le catalogue et les schemas Unity Catalog existent
# MAGIC 2. Le Volume de landing est accessible en lecture
# MAGIC 3. Une table Delta peut etre creee, ecrite, relue
# MAGIC 4. L'historique Delta (time travel) est bien actif
# MAGIC
# MAGIC S'il passe, la phase 0 est terminee.

# COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
dbutils.widgets.text("landing_volume", "/Volumes/ocarina_dev/bronze/landing")
dbutils.widgets.text("bundle_target", "dev")

CATALOG = dbutils.widgets.get("catalog")
LANDING_VOLUME = dbutils.widgets.get("landing_volume")
BUNDLE_TARGET = dbutils.widgets.get("bundle_target")

print(f"catalogue       : {CATALOG}")
print(f"volume landing  : {LANDING_VOLUME}")
print(f"cible du bundle : {BUNDLE_TARGET}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Le catalogue et les schemas repondent

# COMMAND ----------

spark.sql(f"USE CATALOG {CATALOG}")

schemas = [r.databaseName for r in spark.sql("SHOW SCHEMAS").collect()]
attendus = {"bronze", "silver", "gold", "ops"}
manquants = attendus - set(schemas)

assert not manquants, (
    f"Schemas manquants dans {CATALOG} : {sorted(manquants)}. "
    "Lance d'abord sql/00_bootstrap.sql dans l'editeur SQL."
)
print(f"OK — schemas presents : {sorted(attendus)}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Le Volume de landing est accessible
# MAGIC
# MAGIC C'est ici que GitHub Actions deposera les fichiers bruts en phase 1.
# MAGIC A ce stade il est normalement vide : on verifie juste qu'il repond.

# COMMAND ----------

try:
    fichiers = dbutils.fs.ls(LANDING_VOLUME)
    print(f"OK — volume accessible, {len(fichiers)} entree(s) a la racine")
except Exception as e:
    raise AssertionError(
        f"Volume {LANDING_VOLUME} inaccessible. Verifie sql/00_bootstrap.sql."
    ) from e

# COMMAND ----------

# MAGIC %md
# MAGIC ## 3. Ecriture et relecture d'une table Delta

# COMMAND ----------

from datetime import datetime, timezone

TABLE = f"{CATALOG}.ops.deployment_check"

spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {TABLE} (
        checked_at    TIMESTAMP COMMENT 'Horodatage UTC du controle',
        bundle_target STRING    COMMENT 'Cible du bundle ayant declenche le run',
        spark_version STRING    COMMENT 'Version de Spark observee a l execution'
    )
    USING DELTA
    COMMENT 'Trace des smoke tests. Sert de preuve que le deploiement fonctionne.'
""")

ligne = [(datetime.now(timezone.utc), BUNDLE_TARGET, spark.version)]
colonnes = ["checked_at", "bundle_target", "spark_version"]

spark.createDataFrame(ligne, colonnes).write.mode("append").saveAsTable(TABLE)

print(f"OK — ecriture reussie dans {TABLE}")

# COMMAND ----------

display(
    spark.table(TABLE).orderBy("checked_at", ascending=False).limit(10)
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## 4. L'historique Delta est actif
# MAGIC
# MAGIC Chaque ecriture cree une version. C'est ce qui permettra plus tard de
# MAGIC relire une table telle qu'elle etait avant un chargement rate
# MAGIC (`SELECT * FROM table VERSION AS OF 12`).

# COMMAND ----------

historique = spark.sql(f"DESCRIBE HISTORY {TABLE}")
nb_versions = historique.count()

assert nb_versions >= 1, "Aucune version Delta enregistree — quelque chose cloche."
print(f"OK — {nb_versions} version(s) Delta enregistree(s)")

display(historique.select("version", "timestamp", "operation", "operationMetrics"))

# COMMAND ----------

# MAGIC %md
# MAGIC ## Resultat
# MAGIC
# MAGIC Si toutes les cellules sont vertes : la boucle
# MAGIC **Git -> GitHub Actions -> bundle -> workspace -> Delta** est operationnelle.
# MAGIC La phase 1 peut commencer.
