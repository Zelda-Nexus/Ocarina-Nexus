import sys
sys.path.insert(0, "src")
from ocarina_nexus.utils.wiki_api import get_page_data
from ocarina_nexus.utils.infobox_parser import parse_infobox, get_title, get_description

for name in ["Saria", "Darunia", "Link", "Princess Zelda"]:
    print("="*60)
    print(name)
    print("="*60)

    data = get_page_data(name)
    if not data:
        print("No data found")
        continue

    infobox = parse_infobox(data["html"])
    for k, v in infobox.items():
        print(f"  {k!r:25} -> {v[:100]!r}")

    desc = get_description(data["html"])
    print()
    print("Description:", (desc[:200] + "...") if desc else None)
    print()
