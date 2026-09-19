# ADR 0004 — PySpark + serverless remplace Scala et GraphFrames

- **Statut :** accepté
- **Date :** 2026-09-19
- **Décideur :** Adam Kharfi
- **Remplace :** [ADR 0002](0002-scala-pour-les-transformations.md), amende [ADR 0003](0003-graphframes-pour-le-graphe-de-connaissances.md)

## Contexte

ADR 0002 et 0003 ont été écrits sans avoir jamais réellement déployé et
exécuté un notebook Scala sur le workspace cible (Databricks Free Edition).
Au premier déploiement réel des jobs `bronze_ingestion` / `silver_transform`
/ `gold_transform` / `graph_build`, deux contraintes de plateforme,
invisibles jusque-là, se sont révélées bloquantes :

1. **Le workspace Free Edition ne provisionne que du compute serverless.**
   Toute tentative de déclarer un `job_cluster` classique (`new_cluster`)
   échoue au `bundle deploy` avec `Only serverless compute is supported in
   the workspace`.
2. **Le compute serverless ne supporte pas Scala.** Toute tâche notebook
   contenant au moins une cellule Scala échoue à l'exécution avec
   `[UNAUTHORIZED_COMMAND] Scala is not yet supported by Serverless
   compute`, y compris pour du Spark SQL/DataFrame pur sans aucune
   dépendance externe.

GraphFrames (ADR 0003) est doublement concerné : au-delà d'être un notebook
Scala, il nécessite une bibliothèque Maven attachée à un cluster — un
mécanisme qui n'existe pas non plus sur serverless (pas de cluster à
configurer, donc pas de `libraries: - maven:` possible).

## Décision

- Les 17 notebooks Bronze/Silver/Gold/Graph/Ops sont réécrits en **PySpark**
  (`.py`, format notebook Databricks avec cellules `# COMMAND ----------`),
  seul langage supporté avec SQL sur le compute serverless de ce workspace.
- Le graphe de connaissances (`gold.graph_metrics` — PageRank, composantes
  connexes) est calculé par une **implémentation PySpark faite maison**
  (jointures itérées, `localCheckpoint()` pour borner le lineage), sans
  GraphFrames : PageRank à itérations fixes (10, sans redistribution de la
  masse des nœuds sans arête sortante — simplification documentée dans le
  notebook), composantes connexes par propagation itérative du plus petit id
  de nœud jusqu'à convergence ou `MAX_ITER_CC`.
- `notebooks/graph/01_graph_build_nodes_edges.py` (matérialisation
  noeuds/arêtes depuis `gold.fact_entity_relation`) ne change pas de rôle,
  seulement de langage.

## Justification

**Pas le choix.** Ce n'est pas un arbitrage de goût entre PySpark et Scala :
Scala ne s'exécute pas du tout sur ce workspace. La seule alternative aurait
été de passer sur une offre Databricks payante avec compute classique —
hors périmètre pour un projet en Free Edition.

**PySpark reste du Spark natif au niveau DataFrame/SQL** : les notebooks
réécrits sont des traductions directes (mêmes noms de colonnes, même
séquence de transformations, mêmes tables Delta en sortie), pas une
réécriture de la logique métier. La valeur pédagogique Spark visée par
l'ADR 0002 (comprendre Auto Loader, Delta, le modèle dimensionnel) est
intacte ; seule la syntaxe change.

**Deux bugs pré-existants découverts au passage, corrigés dans le même
mouvement** (jamais exécutés avant faute de pouvoir lancer quoi que ce
soit) :
- `landing_volume/../_schemas/...` tentait de sortir de la frontière du
  volume UC déclaré (`ocarina_dev.bronze.landing`) — corrigé en
  `landing_volume/_schemas/...`, un sous-répertoire du même volume.
- `input_file_name()` n'est pas supporté par Unity Catalog sur serverless
  (`UC_COMMAND_NOT_SUPPORTED`) — remplacé par la colonne cachée
  `_metadata.file_path`.

## Conséquences

- `libraries: - maven:` disparaît de `graph_build.job.yml` : plus aucun job
  ne déclare de dépendance JVM externe.
- Tous les `job_clusters` explicites disparaissent des fichiers
  `resources/jobs/*.job.yml` — chaque tâche tourne en serverless implicite,
  comme `smoke_test.job.yml` depuis le début.
- Le PageRank et les composantes connexes ne sont plus ceux d'une
  bibliothèque de graphe éprouvée : leurs limites (PageRank sans
  redistribution de masse, composantes connexes bornées à `MAX_ITER_CC`
  itérations) sont documentées en tête de
  `notebooks/graph/02_graph_algorithms.py` plutôt que cachées. Pour un
  graphe de quelques milliers de nœuds/arêtes (l'échelle actuelle du
  projet), ces limites n'affectent pas la lisibilité du classement produit.
- `.cache()` / `.persist()` ne sont pas non plus disponibles sur serverless
  (`PERSIST TABLE is not supported on serverless compute`) — supprimé du
  seul endroit qui l'utilisait (`silver/04_silver_randomizer.py`).

## À réévaluer si

Le projet migre un jour vers un workspace avec compute classique
disponible (upgrade au-delà de Free Edition) **et** qu'un besoin réel de
GraphFrames apparaît (motifs de graphe, BFS, algorithmes non couverts par
l'implémentation maison) — auquel cas ADR 0003 redevient pertinent tel
quel. Scala redevient un choix valide dans les mêmes conditions, mais rien
n'indique aujourd'hui que la valeur pédagogique justifierait de perdre la
portabilité serverless.
