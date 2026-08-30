# ADR 0001 — Delta Lake comme format de table

- **Statut :** accepté
- **Date :** 2026-08-30
- **Décideur :** Adam Kharfi

## Contexte

Le projet a besoin d'un format de table capable de supporter des écritures
incrémentales répétées, des corrections rétroactives, et l'évolution du schéma
des sources — le wiki ajoute des champs d'infobox, l'API speedrun.com change
le statut de vérification d'une run après coup.

Trois options ont été considérées : Parquet nu (l'état actuel du projet),
Apache Iceberg, et Delta Lake.

## Décision

Le projet utilise **Delta Lake**, sur Unity Catalog.

## Justification

**Parquet nu est écarté.** C'est ce qu'utilise la version actuelle du projet et
la limite est déjà atteinte : pas de transaction, donc un job interrompu laisse
des fichiers partiels que rien ne distingue des fichiers valides. Pas de `MERGE`,
donc toute mise à jour impose de réécrire l'ensemble de la partition. Pas
d'historique, donc aucun moyen de revenir en arrière après un chargement fautif.

**Iceberg est écarté pour ce projet, pas sur le fond.** Le format est solide et
plus neutre vis-à-vis des moteurs. Mais l'intégration native avec Unity Catalog,
Auto Loader, `OPTIMIZE` et le liquid clustering est nettement plus directe côté
Delta sur Databricks. L'objectif étant d'apprendre les mécanismes — compaction,
statistiques de fichiers, data skipping — le chemin le moins friction gagne.

**Delta apporte précisément ce qui manque :** transactions ACID, `MERGE INTO`
pour l'incrémental et le SCD2, time travel pour le débogage et les tests de
non-régression, contraintes `CHECK` pour la qualité, et évolution de schéma
contrôlée.

## Conséquences

- Toutes les tables des couches bronze, silver et gold sont en Delta.
- Le projet est de fait couplé à l'écosystème Databricks. C'est assumé pour un
  projet d'apprentissage ; ce serait un point à discuter dans un contexte
  d'entreprise soucieux de portabilité.
- `OPTIMIZE` et `VACUUM` deviennent des opérations de maintenance à planifier —
  elles feront l'objet d'un job dédié en phase 2.
- Le format Parquet ne disparaît pas : Delta l'utilise comme format de stockage
  sous-jacent. Ce qui s'ajoute, c'est le journal de transactions.

## À réévaluer si

Le projet devait être lu par un moteur externe à Databricks (Trino, Snowflake,
Flink), auquel cas la question Iceberg se reposerait sérieusement.
