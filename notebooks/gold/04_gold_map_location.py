# Databricks notebook source
# MAGIC %md
# MAGIC # Gold — carte du site (`gold.map_location`)
# MAGIC
# MAGIC Produit la table qui alimente la carte interactive du site
# MAGIC (`site/data/locations.json`, régénéré depuis cette table par
# MAGIC `scripts/export_site_locations.py` — pas d'écriture directe sur un
# MAGIC Volume UC ici, `site/` est un dossier statique servi hors de Databricks).
# MAGIC
# MAGIC Deux informations ne viennent d'aucune source amont et n'ont pas vocation à
# MAGIC être devinées, elles sont donc tenues à la main dans des tables de référence
# MAGIC versionnées avec le code :
# MAGIC
# MAGIC - `gold.ref_map_pin` : la position du repère sur le dessin (x, y en % du
# MAGIC   viewBox 1000x640 de `site/assets/img/hyrule/hyrule-map.svg`) et les
# MAGIC   époques où le lieu est visitable. Une carte dessinée n'a pas de système
# MAGIC   de coordonnées dans le jeu ; ces valeurs changent si le fond de carte
# MAGIC   est redessiné.
# MAGIC - `gold.ref_noclip_scene` : la correspondance entre le nom de scène de la
# MAGIC   décompilation (`spot04`, `ydan`, ...) et les identifiants de scène des
# MAGIC   deux visionneuses noclip.website. Relevée dans `magcius/noclip.website`
# MAGIC   (`src/zelview/scenes.ts` et `src/OcarinaOfTime3D/oot3d_scenes.ts`).
# MAGIC
# MAGIC Le reste (titre, résumé, région) vient de `gold.dim_location`, donc d'un
# MAGIC rafraîchissement du wiki. Un lieu présent dans `ref_map_pin` mais absent de
# MAGIC la dimension fait échouer le notebook : c'est le signal qu'un `entity_id` a
# MAGIC bougé en amont, pas quelque chose à rattraper silencieusement.

# COMMAND ----------

dbutils.widgets.text("catalog", "ocarina_dev")
catalog = dbutils.widgets.get("catalog")
spark.sql(f"USE CATALOG {catalog}")

# COMMAND ----------

from pyspark.sql import functions as F

# COMMAND ----------

# MAGIC %md
# MAGIC ## 1. Tables de référence

# COMMAND ----------

# x, y = pourcentages du viewBox de assets/img/hyrule/hyrule-map.svg (1000 x 640).
_PINS = [
    ("hyrule_field",          60.000, 51.875, ["child", "adult"]),
    ("lon_lon_ranch",         41.600, 58.438, ["child", "adult"]),
    ("hyrule_castle",         47.000, 27.500, ["child", "adult"]),
    ("market",                48.000, 33.438, ["child", "adult"]),
    ("temple_of_time",        51.600, 34.688, ["child", "adult"]),
    ("kokiri_forest",         79.700, 71.406, ["child", "adult"]),
    ("deku_tree",             83.600, 66.875, ["child"]),
    ("lost_woods",            74.200, 81.250, ["child", "adult"]),
    ("sacred_forest_meadow",  90.800, 55.625, ["child", "adult"]),
    ("forest_temple",         95.000, 50.938, ["adult"]),
    ("kakariko_village",      68.600, 39.063, ["child", "adult"]),
    ("bottom_of_the_well",    65.600, 35.938, ["child"]),
    ("graveyard",             72.800, 33.125, ["child", "adult"]),
    ("shadow_temple",         76.200, 29.063, ["adult"]),
    ("death_mountain_trail",  79.200, 26.250, ["child", "adult"]),
    ("goron_city",            83.000, 20.000, ["child", "adult"]),
    ("dodongos_cavern",       76.000, 18.125, ["child"]),
    ("death_mountain_crater", 85.200, 11.563, ["child", "adult"]),
    ("fire_temple",           89.600, 16.875, ["adult"]),
    ("zora_river",            80.600, 35.313, ["child", "adult"]),
    ("zoras_domain",          88.400, 29.688, ["child", "adult"]),
    ("zoras_fountain",        93.000, 23.438, ["child", "adult"]),
    ("inside_jabu_jabus_belly", 94.400, 16.563, ["child"]),
    ("ice_cavern",            95.200, 29.063, ["adult"]),
    ("lake_hylia",            45.200, 80.313, ["child", "adult"]),
    ("lakeside_laboratory",   55.200, 72.813, ["child", "adult"]),
    ("water_temple",          40.800, 87.813, ["adult"]),
    ("gerudo_valley",         30.000, 50.625, ["child", "adult"]),
    ("gerudos_fortress",      21.400, 41.875, ["adult"]),
    ("haunted_wasteland",     12.200, 46.875, ["adult"]),
    ("desert_colossus",       15.200, 32.500, ["adult"]),
    ("spirit_temple",         12.600, 27.500, ["adult"]),
]

pins = spark.createDataFrame(_PINS, ["entity_id", "x", "y", "eras"])
pins.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("gold.ref_map_pin")

# COMMAND ----------

# `scene_key` = nom de scène de la décompilation, celui que porte déjà
# `gold.dim_location.rando_scene`. Une chaîne vide = scène absente de cette
# visionneuse (noclip n'expose pas encore les intérieurs à fond JFIF côté N64).
_NOCLIP_SCENES = [
    ("spot00",       "zelview/spot00_scene",      "oot3d/spot00"),
    ("spot01",       "zelview/spot01_scene",      "oot3d/spot01"),
    ("spot02",       "zelview/spot02_scene",      "oot3d/spot02"),
    ("spot03",       "zelview/spot03_scene",      "oot3d/spot03"),
    ("spot04",       "zelview/spot04_scene",      "oot3d/spot04"),
    ("spot05",       "zelview/spot05_scene",      "oot3d/spot05"),
    ("spot06",       "zelview/spot06_scene",      "oot3d/spot06"),
    ("spot07",       "zelview/spot07_scene",      "oot3d/spot07"),
    ("spot08",       "zelview/spot08_scene",      "oot3d/spot08"),
    ("spot09",       "zelview/spot09_scene",      "oot3d/spot09"),
    ("spot10",       "zelview/spot10_scene",      "oot3d/spot10"),
    ("spot11",       "zelview/spot11_scene",      "oot3d/spot11"),
    ("spot12",       "zelview/spot12_scene",      "oot3d/spot12"),
    ("spot13",       "zelview/spot13_scene",      "oot3d/spot13"),
    ("spot15",       "zelview/spot15_scene",      "oot3d/spot15"),
    ("spot16",       "zelview/spot16_scene",      "oot3d/spot16"),
    ("spot17",       "zelview/spot17_scene",      "oot3d/spot17"),
    ("spot18",       "zelview/spot18_scene",      "oot3d/spot18"),
    ("spot20",       "zelview/spot20_scene",      "oot3d/spot20"),
    ("ydan",         "zelview/ydan_scene",        "oot3d/ydan"),
    ("ddan",         "zelview/ddan_scene",        "oot3d/ddan"),
    ("bdan",         "zelview/bdan_scene",        "oot3d/bdan"),
    ("Bmori1",       "zelview/Bmori1_scene",      "oot3d/bmori1"),
    ("HIDAN",        "zelview/HIDAN_scene",       "oot3d/hidan"),
    ("MIZUsin",      "zelview/MIZUsin_scene",     "oot3d/mizusin"),
    ("HAKAdan",      "zelview/HAKAdan_scene",     "oot3d/hakadan"),
    ("HAKAdanCH",    "zelview/HAKAdanCH_scene",   "oot3d/hakadan_ch"),
    ("jyasinzou",    "zelview/jyasinzou_scene",   "oot3d/jyasinzou"),
    ("ice_doukutu",  "zelview/ice_doukutu_scene", "oot3d/ice_doukutu"),
    ("tokinoma",     "zelview/tokinoma_scene",    "oot3d/tokinoma"),
    ("hylia_labo",   "zelview/hylia_labo_scene",  "oot3d/hylia_labo"),
    ("ganon_tou",    "zelview/ganon_tou_scene",   "oot3d/ganon_tou"),
    ("market_day",   "",                          "oot3d/market_day"),
    ("market_ruins", "",                          "oot3d/market_ruins"),
]

noclip_scenes = spark.createDataFrame(_NOCLIP_SCENES, ["scene_key", "n64", "oot3d"])
noclip_scenes.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("gold.ref_noclip_scene")

# COMMAND ----------

# MAGIC %md
# MAGIC ## 2. Scène par lieu et par époque
# MAGIC
# MAGIC `silver.rando_region.scene` s'est révélé être un **nom lisible** ("Temple
# MAGIC of Time", "Desert Colossus"), pas le code de scène de la décompilation
# MAGIC ("spot00", "ydan") que `gold.ref_noclip_scene.scene_key` attend — un
# MAGIC rapprochement par ce champ ne matchait que 5 lieux sur 32. La
# MAGIC correspondance lieu -> code de scène est donc tenue à la main ici, comme
# MAGIC `ref_map_pin` et `ref_noclip_scene` : c'est un fait stable de la
# MAGIC décompilation (`zeldaret/oot`), pas quelque chose qui se déduit d'une
# MAGIC source amont. La plupart des lieux gardent la même scène aux deux âges ;
# MAGIC les exceptions (château devenu tour de Ganon, bourg devenu ruines) ont
# MAGIC directement leur override par époque.

# COMMAND ----------

# entity_id -> scene_key par defaut (les deux epoques, sauf override ci-dessous)
_DEFAULT_SCENE = {
    "hyrule_field": "spot00", "lon_lon_ranch": "spot20", "hyrule_castle": "spot15",
    "temple_of_time": "tokinoma", "kokiri_forest": "spot04", "deku_tree": "ydan",
    "lost_woods": "spot10", "sacred_forest_meadow": "spot05", "forest_temple": "Bmori1",
    "kakariko_village": "spot01", "bottom_of_the_well": "HAKAdan", "graveyard": "spot02",
    "shadow_temple": "HAKAdanCH", "death_mountain_trail": "spot16", "goron_city": "spot18",
    "dodongos_cavern": "ddan", "death_mountain_crater": "spot17", "fire_temple": "HIDAN",
    "zora_river": "spot03", "zoras_domain": "spot07", "zoras_fountain": "spot08",
    "inside_jabu_jabus_belly": "bdan", "ice_cavern": "ice_doukutu", "lake_hylia": "spot06",
    "lakeside_laboratory": "hylia_labo", "water_temple": "MIZUsin", "gerudo_valley": "spot09",
    "gerudos_fortress": "spot12", "haunted_wasteland": "spot13", "desert_colossus": "spot11",
    "spirit_temple": "jyasinzou",
}

# (entity_id, era) -> scene_key, remplace le defaut pour cette epoque precise.
# `market` n'a pas de defaut : les deux epoques sont des ruines/un bourg
# distincts, jamais la meme scene.
_ERA_OVERRIDES = {
    ("hyrule_castle", "adult"): "ganon_tou",
    ("market", "child"): "market_day",
    ("market", "adult"): "market_ruins",
}

_scene_rows = [
    (entity_id, era, _ERA_OVERRIDES.get((entity_id, era), _DEFAULT_SCENE.get(entity_id)))
    for entity_id, _x, _y, eras in _PINS
    for era in eras
]
entity_scene = spark.createDataFrame(_scene_rows, ["entity_id", "era", "scene_key"])

# COMMAND ----------

# Base large (tous types d'entites) : quelques lieux du plan n'ont pas
# l'etiquette "locations" sur le wiki (Deku Tree est un "characters", Forest
# Temple et Ice Cavern des "dungeons" seuls) — gold.dim_location seul les
# raterait. region ne vit que dans dim_location.
dim_all = spark.table("gold.dim_entity").select("entity_id", "title", "summary")
dim_loc = spark.table("gold.dim_location").select("entity_id", "rando_region_name")
dim = dim_all.join(dim_loc, "entity_id", "left")

pin = spark.table("gold.ref_map_pin")

manquants = [r["entity_id"] for r in pin.join(dim, "entity_id", "left_anti").select("entity_id").collect()]
assert not manquants, f"reperes sans ligne dans gold.dim_entity : {manquants}"

# COMMAND ----------

# un lieu x une epoque = une ligne, avant regroupement
par_epoque = (
    pin.select("entity_id", "x", "y", "eras", F.explode("eras").alias("era"))
    .join(
        dim.select(
            "entity_id", "title", "summary",
            F.coalesce(F.col("rando_region_name"), F.lit("Hyrule")).alias("region"),
        ),
        "entity_id",
        "left",
    )
    .join(entity_scene, ["entity_id", "era"], "left")
    .join(spark.table("gold.ref_noclip_scene"), "scene_key", "left")
)

carte = (
    par_epoque.groupBy("entity_id", "title", "summary", "region", "x", "y", "eras")
    .agg(
        F.collect_list(
            F.struct(
                F.col("era"),
                F.when(F.col("n64") != "", F.col("n64")).alias("n64"),
                F.when(F.col("oot3d") != "", F.col("oot3d")).alias("oot3d"),
            )
        ).alias("scenes")
    )
)

carte.write.mode("overwrite").option("overwriteSchema", "true").saveAsTable("gold.map_location")

print(f"OK — gold.map_location : {spark.table('gold.map_location').count()} lieux")
display(spark.table("gold.map_location").orderBy("entity_id"))
