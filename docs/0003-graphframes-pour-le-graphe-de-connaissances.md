# ADR 0003 — GraphFrames sur Delta pour le graphe de connaissances

- **Statut :** accepté
- **Date :** 2026-09-11
- **Décideur :** Adam Kharfi

## Contexte

Le schéma cible (`data/Schéma cible — Bibliothèque Ocarina of Time + IA (RAG).md`,
§3.3) prévoit un graphe de connaissances fusionnant infobox, liens wiki,
graphe de régions du randomizer et tables du moteur, pour la navigation du
site, un futur RAG « graph-aware », et la recherche GNN mentionnée dans le
README. Deux options : une base de graphe dédiée (Neo4j), ou GraphFrames
au-dessus des tables Delta déjà en place.

## Décision

Le graphe est construit avec **GraphFrames sur Spark**, matérialisé en tables
Delta `gold.graph_nodes` / `gold.graph_edges` (à partir de
`gold.fact_entity_relation`), interrogé pour des algorithmes (PageRank,
composantes connexes) dont les résultats sont persistés dans
`gold.graph_metrics`. Aucune base de graphe externe n'est introduite.

## Justification

**Zéro infrastructure nouvelle.** Neo4j (ou équivalent) ajouterait un service
à héberger, sécuriser et synchroniser avec le lakehouse — un système de
vérité supplémentaire à maintenir cohérent avec Bronze/Silver/Gold, alors que
le projet entier est construit autour du principe inverse : tout vit dans
Unity Catalog, rien n'est créé à la main ailleurs.

**Cohérent avec le choix Scala (ADR 0002).** GraphFrames a une API Scala et
Python quasi identiques ; rester dans l'écosystème Spark pour cette étape
évite d'introduire un troisième langage/runtime dans le pipeline.

**Le graphe reste rejouable depuis Gold**, comme le reste du pipeline : une
mauvaise pondération dans `fact_entity_relation` se corrige et se propage en
rejouant `graph_build` sans dépendance externe à resynchroniser.

## Conséquences

- Les requêtes de type Cypher (chemins multi-sauts complexes, correspondance
  de motifs élaborée) ne sont pas aussi naturelles qu'avec une vraie base de
  graphe — GraphFrames couvre PageRank, composantes connexes, BFS et motifs
  simples, ce qui suffit à l'usage actuel (navigation « entités liées »,
  détection d'entités isolées).
- GraphFrames nécessite une bibliothèque Maven attachée au cluster
  (`graphframes:graphframes`), ce qui impose un cluster classique pour
  `graph_build.job.yml` — un point de compatibilité à valider sur la Free
  Edition avant le premier déploiement réel (voir le plan de mise en œuvre).
- La qualité du graphe dépend entièrement de celle de
  `gold.fact_entity_relation` : un signal de fusion bruité (ex. le
  rapprochement approximatif nom-de-région ↔ entité de lieu) se traduit
  directement par des arêtes de mauvaise qualité, pas par une limite propre
  à GraphFrames.

## À réévaluer si

Le graphe devait être exposé pour une exploration interactive riche côté site
(visualisation de chemins, requêtes ad hoc par les visiteurs) : un export
périodique vers une base de graphe dédiée deviendrait alors justifié, en
lecture seule, sans changer la source de vérité.
