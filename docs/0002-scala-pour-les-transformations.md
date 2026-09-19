# ADR 0002 — Scala pour les transformations Silver/Gold

- **Statut :** remplacé par [ADR 0004](0004-pyspark-serverless-remplace-scala-et-graphframes.md) (2026-09-19) — le
  compute serverless du workspace cible ne supporte pas Scala, decouvert au
  premier deploiement reel des jobs, apres cet ADR
- **Date :** 2026-09-11
- **Décideur :** Adam Kharfi

## Contexte

L'extraction (scraping des sources externes) est nécessairement en Python
(`httpx`, I/O-bound) — voir `src/ocarina_nexus/extraction/`. Restait à choisir
le langage des transformations Bronze → Silver → Gold, qui elles sont du
calcul Spark pur (typage, dédoublonnage, SCD2, modélisation dimensionnelle,
fusion du graphe de connaissances). Deux options : PySpark, cohérent avec le
reste du projet, ou Scala, natif à Spark.

## Décision

Les transformations Silver, Gold et la construction du graphe de
connaissances sont écrites en **Scala**, sous forme de notebooks Databricks
(`.scala`, format source, commités dans `notebooks/`) déployés via
`notebook_task` — la même convention que `00_smoke_test.py` à la racine, pas
de build sbt/JAR.

## Justification

**Pas de build compilé.** sbt n'est pas présent dans l'environnement de
développement de ce tour, et aucun autre fichier du projet n'a d'étape de
build (`00_bootstrap.sql` et `00_smoke_test.py` sont des fichiers plats
déployés tels quels). Introduire un pipeline JAR (compilation, publication
d'artefact, `libraries: - jar:`) aurait doublé la surface de CI pour un
bénéfice qui ne se matérialise pas tant qu'il n'y a pas de tests Scala
unitaires à faire tourner hors Databricks.

**Auto Loader, Delta et Spark SQL n'ont besoin d'aucune bibliothèque
externe** en Scala — seul GraphFrames (phase graphe) a une dépendance Maven,
volontairement isolée à `graph_build.job.yml` plutôt que généralisée à tout
le projet.

**Big Data / Spark natif.** C'est explicitement un projet d'apprentissage
(voir README) ; écrire les transformations dans le langage natif de Spark,
plutôt que sa liaison Python, est le choix qui a le plus de valeur
pédagogique pour cette partie du pipeline.

## Conséquences

- Deux écosystèmes de dépendances coexistent : `pyproject.toml` (extraction)
  et rien de spécifique pour Scala pour l'instant (pas de `build.sbt`).
- Un bug de compilation Scala ne se découvre qu'au déploiement/exécution
  réelle du notebook sur le workspace, pas en CI locale — aucun compilateur
  Scala n'est invoqué avant `databricks bundle deploy`.
- Le typage des colonnes à clés dynamiques (infobox Zelda Wiki, claims
  Wikidata, maps randomizer) est géré via `cloudFiles.schemaHints` côté
  Bronze plutôt que par inférence automatique — un choix de conception
  indépendant du langage, mais qui aurait dû être fait de toute façon en
  PySpark.

## À réévaluer si

Des tests Scala unitaires (au-delà de ce qu'un notebook peut vérifier par
assertion en ligne) deviennent nécessaires : sbt + un JAR compilé redeviendrait
le bon choix, sans remettre en cause le choix du langage lui-même.
