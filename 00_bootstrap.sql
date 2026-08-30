-- =============================================================================
-- Ocarina Nexus — bootstrap Unity Catalog
--
-- A executer UNE FOIS dans l'editeur SQL Databricks, sur ton SQL Warehouse.
-- C'est la seule etape manuelle de tout le projet : Unity Catalog ne se gere
-- pas depuis un Asset Bundle sur Free Edition (pas d'acces au niveau compte).
--
-- Tout le reste — jobs, pipelines, tables — sera cree par le code.
-- =============================================================================


-- -----------------------------------------------------------------------------
-- 1. Catalogues
--    Un catalogue par environnement. Meme workspace, donnees separees.
-- -----------------------------------------------------------------------------
CREATE CATALOG IF NOT EXISTS ocarina_dev
  COMMENT 'Ocarina Nexus — environnement de developpement';

CREATE CATALOG IF NOT EXISTS ocarina_prod
  COMMENT 'Ocarina Nexus — environnement de production';


-- -----------------------------------------------------------------------------
-- 2. Schemas (une couche = un schema)
--
--    bronze : copie fidele de la source, aucune regle metier
--    silver : donnee typee, dedupliquee, fiable
--    gold   : modele en etoile, pret a consommer
--    ops    : metadonnees techniques (qualite, audit, executions)
-- -----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS ocarina_dev.bronze
  COMMENT 'Donnees brutes, telles que recues de la source';
CREATE SCHEMA IF NOT EXISTS ocarina_dev.silver
  COMMENT 'Donnees typees, dedupliquees et historisees';
CREATE SCHEMA IF NOT EXISTS ocarina_dev.gold
  COMMENT 'Modele dimensionnel expose aux consommateurs';
CREATE SCHEMA IF NOT EXISTS ocarina_dev.ops
  COMMENT 'Observabilite : qualite, audit, executions de pipelines';

CREATE SCHEMA IF NOT EXISTS ocarina_prod.bronze;
CREATE SCHEMA IF NOT EXISTS ocarina_prod.silver;
CREATE SCHEMA IF NOT EXISTS ocarina_prod.gold;
CREATE SCHEMA IF NOT EXISTS ocarina_prod.ops;


-- -----------------------------------------------------------------------------
-- 3. Volume de landing
--
--    C'est le point de contact entre l'exterieur et Databricks.
--    GitHub Actions y depose des fichiers JSONL bruts ; Auto Loader les lit.
--    Rien d'autre n'ecrit ici.
--
--    Convention de chemin imposee des la phase 1 :
--      /Volumes/<catalogue>/bronze/landing/<source>/<entite>/ingest_date=YYYY-MM-DD/
-- -----------------------------------------------------------------------------
CREATE VOLUME IF NOT EXISTS ocarina_dev.bronze.landing
  COMMENT 'Zone de depot des fichiers bruts avant ingestion Auto Loader';

CREATE VOLUME IF NOT EXISTS ocarina_prod.bronze.landing
  COMMENT 'Zone de depot des fichiers bruts avant ingestion Auto Loader';


-- -----------------------------------------------------------------------------
-- 4. Verification
-- -----------------------------------------------------------------------------
SHOW SCHEMAS IN ocarina_dev;
SHOW VOLUMES IN ocarina_dev.bronze;
