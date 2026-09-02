# 01 — Architecture

## Reproductibilité : l'infrastructure, pas les données

LeLe dépôt Git est la source de vérité de l'infrastructure, pas les données. Cette distinction structure plusiurs décisions l'architecture, elle mérite d'être explicite.

### Ce qu'un déploiment reconstruit

Tout ce qui est écrit dans `databricks.yml` et `resources/` est recréé à l'identique par `databricks bundle deploy` : les jobs, leurs tâches, leurs paramètres, leurs planifications, leurs permissions...

**Ainsi :** Tout ce qui est créé dans le workspace databricks est jetable, la source est le git donc aucun élément ne doit être créé à la main.

### Ce qu'un déploiement ne reconstruit pas

Les tables et les fichiers survivent au déploiement, et ne sont pas recréés s'ils disparaissent. Par exemple la table `ops.deployment_check` n'aurait pas été reconstruit si on l'avait supprimé.

> Pour qu'une donnée soit reporductible, il faut que sa source l'est encore, or les sources de projet ne le garantissent pas :
> - une page de wiki peut être modifié sans historique.
> - une run speedrun peut voir son statut de vérification changé.
> - une API impose un quota de requête qui rend un rechargement complet très coûteux.


### Le rôle de la couche bronze comme point de rejeu

Le critère qui définit son contenu : elle conserve la donnée **telle qu'elle a été reçu**, sans aucune règle métier, pour qu'une transformation fautive puisse être corrigée être jouée sans retourner interroger la source.

Trois règles en découlent :

1. Bronze est en apprend-only. On n'y met jamais à jour ni ne supprime une ligne.
2. Aucun traitement n'écrit dans bronze en dehors de l'ingestion Auto Loader.
3. Les fichiers bruts déposés dans le Volume de landing sont conservés, pas supprimés après chargement - ils constituent le dernier recours si le chargement lui-même s'avère défaillant.