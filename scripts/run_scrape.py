import sys
sys.path.insert(0, "src")
from ocarina_nexus.ingestion.scraper_characters import run

run(resume=True)
