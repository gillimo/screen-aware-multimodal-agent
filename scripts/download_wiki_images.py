"""
Download images from OSRS Wiki for ML training dataset.
Organized like Java packages:
  - trees/oak/
  - trees/yew/
  - npcs/guards/
  - items/weapons/swords/
"""
import os
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "data" / "ml_dataset"

WIKI_API = "https://oldschool.runescape.wiki/api.php"
HEADERS = {"User-Agent": "AgentOSRS/1.0 (ML Dataset Builder)"}

# Category structure - maps wiki categories to folder paths
CATEGORIES = {
    # Trees
    "Trees": "trees/generic",
    "Oak trees": "trees/oak",
    "Willow trees": "trees/willow",
    "Maple trees": "trees/maple",
    "Yew trees": "trees/yew",
    "Magic trees": "trees/magic",

    # NPCs by type
    "Guards": "npcs/guards",
    "Bankers": "npcs/bankers",
    "Shop owners": "npcs/shopkeepers",
    "Quest NPCs": "npcs/quest",
    "Tutors": "npcs/tutors",

    # Monsters
    "Goblins": "npcs/monsters/goblins",
    "Cows": "npcs/monsters/cows",
    "Chickens": "npcs/monsters/chickens",
    "Rats": "npcs/monsters/rats",

    # Items - Weapons
    "Bronze weapons": "items/weapons/bronze",
    "Iron weapons": "items/weapons/iron",
    "Steel weapons": "items/weapons/steel",
    "Swords": "items/weapons/swords",
    "Axes": "items/weapons/axes",

    # Items - Armor
    "Bronze armour": "items/armor/bronze",
    "Iron armour": "items/armor/iron",
    "Helmets": "items/armor/helmets",
    "Shields": "items/armor/shields",

    # Items - Food
    "Fish": "items/food/fish",
    "Meat": "items/food/meat",
    "Bread": "items/food/bread",

    # Items - Resources
    "Logs": "items/resources/logs",
    "Ores": "items/resources/ores",
    "Bars": "items/resources/bars",

    # Objects/Scenery
    "Doors": "objects/doors",
    "Gates": "objects/gates",
    "Banks": "objects/banks",
    "Furnaces": "objects/furnaces",
    "Anvils": "objects/anvils",

    # Tutorial Island specific
    "Tutorial Island": "locations/tutorial_island",
}

def api_request(params):
    """Make a request to the OSRS Wiki API"""
    url = f"{WIKI_API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"  API error: {e}")
        return {}

def get_category_members(category, limit=100):
    """Get all pages in a category"""
    members = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": min(limit, 500),
        "format": "json"
    }

    data = api_request(params)
    members.extend(data.get("query", {}).get("categorymembers", []))

    # Handle continuation if needed
    while "continue" in data and len(members) < limit:
        params["cmcontinue"] = data["continue"]["cmcontinue"]
        data = api_request(params)
        members.extend(data.get("query", {}).get("categorymembers", []))

    return members[:limit]

def get_page_image(title):
    """Get the main image URL for a wiki page"""
    params = {
        "action": "query",
        "titles": title,
        "prop": "pageimages",
        "piprop": "original",
        "format": "json"
    }

    data = api_request(params)
    pages = data.get("query", {}).get("pages", {})

    for page_id, page_data in pages.items():
        if "original" in page_data:
            return page_data["original"]["source"]
    return None

def download_image(url, save_path):
    """Download an image to local path"""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            with open(save_path, 'wb') as f:
                f.write(resp.read())
        return True
    except Exception as e:
        return False

def sanitize_filename(name):
    """Make a filename safe"""
    invalid = '<>:"/\\|?*'
    for char in invalid:
        name = name.replace(char, '_')
    return name[:80]

def download_category(wiki_category, folder_path, limit=50):
    """Download images from a wiki category to a folder"""
    save_dir = DATASET_DIR / folder_path
    save_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[{wiki_category}] -> {folder_path}/")

    members = get_category_members(wiki_category, limit=limit)
    if not members:
        print(f"  No pages found")
        return 0

    print(f"  Found {len(members)} pages")

    downloaded = 0
    for member in members:
        title = member["title"]

        # Skip category pages
        if title.startswith("Category:"):
            continue

        safe_name = sanitize_filename(title)
        save_path = save_dir / f"{safe_name}.png"

        if save_path.exists():
            continue

        img_url = get_page_image(title)
        if not img_url:
            continue

        if download_image(img_url, save_path):
            downloaded += 1
            print(f"    {downloaded}: {title}")

        time.sleep(0.15)  # Rate limit

    print(f"  Downloaded {downloaded} images")
    return downloaded

def main():
    print("=" * 50)
    print("OSRS Wiki Image Downloader")
    print("Organized by category (Java-style)")
    print("=" * 50)

    total = 0
    for wiki_cat, folder in CATEGORIES.items():
        count = download_category(wiki_cat, folder, limit=30)
        total += count

    print("\n" + "=" * 50)
    print(f"Total images downloaded: {total}")
    print(f"Dataset location: {DATASET_DIR}")

    # List folder structure
    print("\nFolder structure:")
    for folder in sorted(DATASET_DIR.rglob("*")):
        if folder.is_dir():
            count = len(list(folder.glob("*.png")))
            if count > 0:
                rel = folder.relative_to(DATASET_DIR)
                print(f"  {rel}/ ({count} images)")

if __name__ == "__main__":
    main()
