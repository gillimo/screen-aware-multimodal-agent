"""
Download ALL images from OSRS Wiki for ML training dataset.
No limits - gets everything available.
Organized in Java-style package structure.

Run: python scripts/download_all_wiki.py
"""
import os
import json
import time
import urllib.request
import urllib.parse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import threading

ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = ROOT / "data" / "ml_dataset"
PROGRESS_FILE = DATASET_DIR / "_download_progress.json"

WIKI_API = "https://oldschool.runescape.wiki/api.php"
HEADERS = {"User-Agent": "AgentOSRS/1.0 (ML Dataset Builder - Educational)"}

# Lock for thread-safe progress tracking
progress_lock = threading.Lock()
download_count = 0
error_count = 0

# COMPREHENSIVE category mapping - ALL wiki categories
CATEGORIES = {
    # ==================== ITEMS ====================
    # Weapons - Melee
    "Bronze weapons": "items/weapons/melee/bronze",
    "Iron weapons": "items/weapons/melee/iron",
    "Steel weapons": "items/weapons/melee/steel",
    "Black weapons": "items/weapons/melee/black",
    "Mithril weapons": "items/weapons/melee/mithril",
    "Adamant weapons": "items/weapons/melee/adamant",
    "Rune weapons": "items/weapons/melee/rune",
    "Dragon weapons": "items/weapons/melee/dragon",
    "Barrows weapons": "items/weapons/melee/barrows",
    "Godswords": "items/weapons/melee/godswords",
    "Swords": "items/weapons/melee/swords",
    "Longswords": "items/weapons/melee/longswords",
    "Scimitars": "items/weapons/melee/scimitars",
    "Daggers": "items/weapons/melee/daggers",
    "Maces": "items/weapons/melee/maces",
    "Warhammers": "items/weapons/melee/warhammers",
    "Battleaxes": "items/weapons/melee/battleaxes",
    "Two-handed swords": "items/weapons/melee/2h_swords",
    "Halberds": "items/weapons/melee/halberds",
    "Spears": "items/weapons/melee/spears",
    "Hastae": "items/weapons/melee/hastae",
    "Claws": "items/weapons/melee/claws",
    "Whips": "items/weapons/melee/whips",

    # Weapons - Ranged
    "Bows": "items/weapons/ranged/bows",
    "Shortbows": "items/weapons/ranged/shortbows",
    "Longbows": "items/weapons/ranged/longbows",
    "Crossbows": "items/weapons/ranged/crossbows",
    "Throwing weapons": "items/weapons/ranged/throwing",
    "Darts": "items/weapons/ranged/darts",
    "Knives": "items/weapons/ranged/knives",
    "Javelins": "items/weapons/ranged/javelins",
    "Chinchompas": "items/weapons/ranged/chinchompas",
    "Arrows": "items/weapons/ranged/arrows",
    "Bolts": "items/weapons/ranged/bolts",

    # Weapons - Magic
    "Staves": "items/weapons/magic/staves",
    "Wands": "items/weapons/magic/wands",
    "Magic weapons": "items/weapons/magic/other",

    # Armor - Helmets
    "Helmets": "items/armor/helmets",
    "Full helmets": "items/armor/helmets/full",
    "Medium helmets": "items/armor/helmets/medium",
    "Coifs": "items/armor/helmets/coifs",
    "Hats": "items/armor/helmets/hats",
    "Wizard hats": "items/armor/helmets/wizard",

    # Armor - Body
    "Platebodies": "items/armor/body/platebodies",
    "Chainbodies": "items/armor/body/chainbodies",
    "Leather armour": "items/armor/body/leather",
    "Dragonhide armour": "items/armor/body/dragonhide",
    "Robes": "items/armor/body/robes",

    # Armor - Legs
    "Platelegs": "items/armor/legs/platelegs",
    "Plateskirts": "items/armor/legs/plateskirts",
    "Chaps": "items/armor/legs/chaps",
    "Robe bottoms": "items/armor/legs/robes",

    # Armor - Shields
    "Shields": "items/armor/shields",
    "Square shields": "items/armor/shields/square",
    "Kiteshields": "items/armor/shields/kite",
    "Defenders": "items/armor/shields/defenders",
    "Spirit shields": "items/armor/shields/spirit",

    # Armor - Capes
    "Capes": "items/armor/capes",
    "Skill capes": "items/armor/capes/skill",
    "God capes": "items/armor/capes/god",
    "Team capes": "items/armor/capes/team",

    # Armor - Gloves/Boots
    "Gloves": "items/armor/gloves",
    "Boots": "items/armor/boots",
    "Vambraces": "items/armor/gloves/vambraces",

    # Armor - Jewellery
    "Amulets": "items/armor/jewellery/amulets",
    "Necklaces": "items/armor/jewellery/necklaces",
    "Rings": "items/armor/jewellery/rings",
    "Bracelets": "items/armor/jewellery/bracelets",

    # Armor - Sets
    "Bronze armour": "items/armor/sets/bronze",
    "Iron armour": "items/armor/sets/iron",
    "Steel armour": "items/armor/sets/steel",
    "Black armour": "items/armor/sets/black",
    "White armour": "items/armor/sets/white",
    "Mithril armour": "items/armor/sets/mithril",
    "Adamant armour": "items/armor/sets/adamant",
    "Rune armour": "items/armor/sets/rune",
    "Dragon armour": "items/armor/sets/dragon",
    "Barrows armour": "items/armor/sets/barrows",
    "Bandos armour": "items/armor/sets/bandos",
    "Armadyl armour": "items/armor/sets/armadyl",
    "Third age equipment": "items/armor/sets/third_age",

    # Food
    "Fish": "items/food/fish",
    "Raw fish": "items/food/fish/raw",
    "Cooked fish": "items/food/fish/cooked",
    "Meat": "items/food/meat",
    "Bread": "items/food/bread",
    "Pies": "items/food/pies",
    "Cakes": "items/food/cakes",
    "Pizzas": "items/food/pizzas",
    "Stews": "items/food/stews",
    "Potatoes": "items/food/potatoes",
    "Fruits": "items/food/fruits",
    "Vegetables": "items/food/vegetables",
    "Cheese": "items/food/cheese",
    "Drinks": "items/food/drinks",
    "Wines": "items/food/wines",
    "Ales": "items/food/ales",

    # Potions
    "Potions": "items/potions",
    "Attack potions": "items/potions/attack",
    "Strength potions": "items/potions/strength",
    "Defence potions": "items/potions/defence",
    "Combat potions": "items/potions/combat",
    "Prayer potions": "items/potions/prayer",
    "Restore potions": "items/potions/restore",
    "Energy potions": "items/potions/energy",
    "Antipoison potions": "items/potions/antipoison",
    "Antifire potions": "items/potions/antifire",

    # Resources - Mining
    "Ores": "items/resources/ores",
    "Bars": "items/resources/bars",
    "Gems": "items/resources/gems",
    "Uncut gems": "items/resources/gems/uncut",

    # Resources - Woodcutting
    "Logs": "items/resources/logs",
    "Planks": "items/resources/planks",

    # Resources - Farming
    "Seeds": "items/resources/seeds",
    "Tree seeds": "items/resources/seeds/tree",
    "Herb seeds": "items/resources/seeds/herb",
    "Allotment seeds": "items/resources/seeds/allotment",
    "Herbs": "items/resources/herbs",
    "Grimy herbs": "items/resources/herbs/grimy",
    "Clean herbs": "items/resources/herbs/clean",

    # Resources - Fishing
    "Fishing bait": "items/resources/fishing",

    # Resources - Crafting
    "Hides": "items/resources/hides",
    "Leather": "items/resources/leather",
    "Thread": "items/resources/thread",
    "Cloth": "items/resources/cloth",
    "Pottery": "items/resources/pottery",
    "Glass": "items/resources/glass",
    "Silver items": "items/resources/silver",
    "Gold items": "items/resources/gold",

    # Resources - Fletching
    "Unstrung bows": "items/resources/fletching/unstrung",
    "Arrow shafts": "items/resources/fletching/shafts",
    "Feathers": "items/resources/fletching/feathers",
    "Arrowheads": "items/resources/fletching/arrowheads",
    "Bolt tips": "items/resources/fletching/bolt_tips",

    # Resources - Runecraft
    "Runes": "items/resources/runes",
    "Talismans": "items/resources/talismans",
    "Tiaras": "items/resources/tiaras",
    "Rune essence": "items/resources/essence",

    # Resources - Hunter
    "Hunter equipment": "items/resources/hunter",
    "Implings": "items/resources/implings",

    # Tools
    "Axes": "items/tools/axes",
    "Pickaxes": "items/tools/pickaxes",
    "Harpoons": "items/tools/harpoons",
    "Fishing rods": "items/tools/fishing_rods",
    "Hammers": "items/tools/hammers",
    "Chisels": "items/tools/chisels",
    "Needles": "items/tools/needles",
    "Knives": "items/tools/knives",
    "Tinderboxes": "items/tools/tinderboxes",
    "Saws": "items/tools/saws",
    "Spades": "items/tools/spades",
    "Rakes": "items/tools/rakes",
    "Seed dibbers": "items/tools/dibbers",
    "Secateurs": "items/tools/secateurs",
    "Watering cans": "items/tools/watering_cans",

    # Quest items
    "Quest items": "items/quest",

    # Teleportation
    "Teleportation items": "items/teleportation",
    "Teleport tablets": "items/teleportation/tablets",
    "Teleport jewellery": "items/teleportation/jewellery",

    # Skilling outfits
    "Skilling outfits": "items/outfits/skilling",

    # Clue scroll items
    "Treasure Trails rewards": "items/clue_scrolls",
    "Clue scrolls": "items/clue_scrolls/scrolls",

    # Miscellaneous items
    "Bones": "items/misc/bones",
    "Ashes": "items/misc/ashes",
    "Keys": "items/misc/keys",
    "Books": "items/misc/books",
    "Coins": "items/misc/coins",
    "Noted items": "items/misc/noted",
    "Ensouled heads": "items/misc/ensouled_heads",

    # ==================== NPCS ====================
    # NPCs - Services
    "Bankers": "npcs/services/bankers",
    "Shop owners": "npcs/services/shopkeepers",
    "Tutors": "npcs/services/tutors",
    "Guards": "npcs/services/guards",
    "Quest NPCs": "npcs/quest",
    "Slayer Masters": "npcs/services/slayer_masters",
    "Skill tutors": "npcs/services/skill_tutors",

    # NPCs - Monsters (Low level)
    "Goblins": "npcs/monsters/low/goblins",
    "Cows": "npcs/monsters/low/cows",
    "Chickens": "npcs/monsters/low/chickens",
    "Rats": "npcs/monsters/low/rats",
    "Spiders": "npcs/monsters/low/spiders",
    "Skeletons": "npcs/monsters/low/skeletons",
    "Zombies": "npcs/monsters/low/zombies",
    "Imps": "npcs/monsters/low/imps",
    "Scorpions": "npcs/monsters/low/scorpions",
    "Hill Giants": "npcs/monsters/low/hill_giants",
    "Moss Giants": "npcs/monsters/low/moss_giants",

    # NPCs - Monsters (Medium level)
    "Lesser demons": "npcs/monsters/medium/lesser_demons",
    "Greater demons": "npcs/monsters/medium/greater_demons",
    "Black demons": "npcs/monsters/medium/black_demons",
    "Hellhounds": "npcs/monsters/medium/hellhounds",
    "Blue dragons": "npcs/monsters/medium/blue_dragons",
    "Red dragons": "npcs/monsters/medium/red_dragons",
    "Black dragons": "npcs/monsters/medium/black_dragons",
    "Green dragons": "npcs/monsters/medium/green_dragons",
    "Fire giants": "npcs/monsters/medium/fire_giants",
    "Ice giants": "npcs/monsters/medium/ice_giants",
    "Trolls": "npcs/monsters/medium/trolls",
    "Ogres": "npcs/monsters/medium/ogres",

    # NPCs - Monsters (Slayer)
    "Slayer monsters": "npcs/monsters/slayer",
    "Aberrant spectres": "npcs/monsters/slayer/aberrant_spectres",
    "Abyssal demons": "npcs/monsters/slayer/abyssal_demons",
    "Basilisks": "npcs/monsters/slayer/basilisks",
    "Bloodvelds": "npcs/monsters/slayer/bloodvelds",
    "Cockatrice": "npcs/monsters/slayer/cockatrice",
    "Crawling Hands": "npcs/monsters/slayer/crawling_hands",
    "Dagannoths": "npcs/monsters/slayer/dagannoths",
    "Dark beasts": "npcs/monsters/slayer/dark_beasts",
    "Dust devils": "npcs/monsters/slayer/dust_devils",
    "Gargoyles": "npcs/monsters/slayer/gargoyles",
    "Kurasks": "npcs/monsters/slayer/kurasks",
    "Nechryaels": "npcs/monsters/slayer/nechryaels",
    "Pyrefiends": "npcs/monsters/slayer/pyrefiends",
    "Spiritual creatures": "npcs/monsters/slayer/spiritual",
    "Turoth": "npcs/monsters/slayer/turoth",
    "Wyrms": "npcs/monsters/slayer/wyrms",
    "Drakes": "npcs/monsters/slayer/drakes",
    "Hydras": "npcs/monsters/slayer/hydras",

    # NPCs - Bosses
    "Bosses": "npcs/bosses",
    "God Wars Dungeon bosses": "npcs/bosses/gwd",
    "Wilderness bosses": "npcs/bosses/wilderness",
    "Slayer bosses": "npcs/bosses/slayer",

    # NPCs - Other
    "Animals": "npcs/animals",
    "Birds": "npcs/animals/birds",
    "Dogs": "npcs/animals/dogs",
    "Cats": "npcs/animals/cats",
    "Pets": "npcs/pets",

    # ==================== OBJECTS ====================
    # Objects - Scenery
    "Trees": "objects/scenery/trees",
    "Oak trees": "objects/scenery/trees/oak",
    "Willow trees": "objects/scenery/trees/willow",
    "Maple trees": "objects/scenery/trees/maple",
    "Yew trees": "objects/scenery/trees/yew",
    "Magic trees": "objects/scenery/trees/magic",
    "Redwood trees": "objects/scenery/trees/redwood",
    "Rocks": "objects/scenery/rocks",
    "Mining rocks": "objects/scenery/rocks/mining",
    "Fishing spots": "objects/scenery/fishing_spots",

    # Objects - Interactive
    "Doors": "objects/interactive/doors",
    "Gates": "objects/interactive/gates",
    "Ladders": "objects/interactive/ladders",
    "Stairs": "objects/interactive/stairs",
    "Banks": "objects/interactive/banks",
    "Altars": "objects/interactive/altars",
    "Furnaces": "objects/interactive/furnaces",
    "Anvils": "objects/interactive/anvils",
    "Ranges": "objects/interactive/ranges",
    "Spinning wheels": "objects/interactive/spinning_wheels",
    "Looms": "objects/interactive/looms",
    "Pottery wheels": "objects/interactive/pottery_wheels",
    "Kilns": "objects/interactive/kilns",
    "Tanning racks": "objects/interactive/tanning",
    "Crafting tables": "objects/interactive/crafting_tables",
    "Workbenches": "objects/interactive/workbenches",
    "Sawmills": "objects/interactive/sawmills",
    "Farming patches": "objects/interactive/farming_patches",
    "Runecraft altars": "objects/interactive/rc_altars",
    "Agility obstacles": "objects/interactive/agility",
    "Thieving stalls": "objects/interactive/thieving_stalls",
    "Chests": "objects/interactive/chests",
    "Crates": "objects/interactive/crates",

    # ==================== LOCATIONS ====================
    "Tutorial Island": "locations/tutorial_island",
    "Lumbridge": "locations/lumbridge",
    "Varrock": "locations/varrock",
    "Falador": "locations/falador",
    "Edgeville": "locations/edgeville",
    "Draynor Village": "locations/draynor",
    "Al Kharid": "locations/al_kharid",
    "Port Sarim": "locations/port_sarim",
    "Rimmington": "locations/rimmington",
    "Barbarian Village": "locations/barbarian_village",
    "Catherby": "locations/catherby",
    "Camelot": "locations/camelot",
    "Seers' Village": "locations/seers_village",
    "Ardougne": "locations/ardougne",
    "Yanille": "locations/yanille",
    "Canifis": "locations/canifis",
    "Morytania": "locations/morytania",
    "Wilderness": "locations/wilderness",
    "Karamja": "locations/karamja",
    "Gnome Stronghold": "locations/gnome_stronghold",
    "Kourend": "locations/kourend",

    # ==================== SKILLS ====================
    "Attack": "skills/attack",
    "Strength": "skills/strength",
    "Defence": "skills/defence",
    "Ranged": "skills/ranged",
    "Prayer": "skills/prayer",
    "Magic": "skills/magic",
    "Runecraft": "skills/runecraft",
    "Construction": "skills/construction",
    "Hitpoints": "skills/hitpoints",
    "Agility": "skills/agility",
    "Herblore": "skills/herblore",
    "Thieving": "skills/thieving",
    "Crafting": "skills/crafting",
    "Fletching": "skills/fletching",
    "Slayer": "skills/slayer",
    "Hunter": "skills/hunter",
    "Mining": "skills/mining",
    "Smithing": "skills/smithing",
    "Fishing": "skills/fishing",
    "Cooking": "skills/cooking",
    "Firemaking": "skills/firemaking",
    "Woodcutting": "skills/woodcutting",
    "Farming": "skills/farming",

    # ==================== INTERFACES ====================
    "Interfaces": "interfaces",
    "Icons": "interfaces/icons",
    "Sprites": "interfaces/sprites",

    # ==================== MINIGAMES ====================
    "Minigames": "minigames",
    "Barbarian Assault": "minigames/barbarian_assault",
    "Castle Wars": "minigames/castle_wars",
    "Pest Control": "minigames/pest_control",
    "Fight Caves": "minigames/fight_caves",
    "Inferno": "minigames/inferno",
    "Chambers of Xeric": "minigames/chambers_of_xeric",
    "Theatre of Blood": "minigames/theatre_of_blood",
    "Tombs of Amascut": "minigames/tombs_of_amascut",
    "Wintertodt": "minigames/wintertodt",
    "Tempoross": "minigames/tempoross",
    "Guardians of the Rift": "minigames/guardians_of_rift",
}

def api_request(params, retries=3):
    """Make a request to the OSRS Wiki API with retries"""
    url = f"{WIKI_API}?{urllib.parse.urlencode(params)}"

    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(1)
            else:
                return {}
    return {}

def get_all_category_members(category):
    """Get ALL pages in a category (no limit)"""
    members = []
    params = {
        "action": "query",
        "list": "categorymembers",
        "cmtitle": f"Category:{category}",
        "cmlimit": 500,  # Max per request
        "format": "json"
    }

    data = api_request(params)
    members.extend(data.get("query", {}).get("categorymembers", []))

    # Continue until we have everything
    while "continue" in data:
        params["cmcontinue"] = data["continue"]["cmcontinue"]
        data = api_request(params)
        new_members = data.get("query", {}).get("categorymembers", [])
        members.extend(new_members)
        print(f"    ... fetched {len(members)} pages so far")

    return members

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
    global download_count, error_count
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=30) as resp:
            with open(save_path, 'wb') as f:
                f.write(resp.read())
        with progress_lock:
            download_count += 1
        return True
    except Exception as e:
        with progress_lock:
            error_count += 1
        return False

def sanitize_filename(name):
    """Make a filename safe"""
    invalid = '<>:"/\\|?*'
    for char in invalid:
        name = name.replace(char, '_')
    return name[:100]

def download_category(wiki_category, folder_path, progress):
    """Download ALL images from a wiki category to a folder"""
    global download_count

    save_dir = DATASET_DIR / folder_path
    save_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"[{wiki_category}] -> {folder_path}/")
    print(f"{'='*60}")

    members = get_all_category_members(wiki_category)
    if not members:
        print(f"  No pages found in this category")
        return 0

    print(f"  Found {len(members)} total pages")

    downloaded = 0
    skipped = 0

    for i, member in enumerate(members):
        title = member["title"]

        # Skip category pages
        if title.startswith("Category:"):
            continue

        safe_name = sanitize_filename(title)
        save_path = save_dir / f"{safe_name}.png"

        if save_path.exists():
            skipped += 1
            continue

        img_url = get_page_image(title)
        if not img_url:
            continue

        if download_image(img_url, save_path):
            downloaded += 1
            if downloaded % 10 == 0:
                print(f"    [{wiki_category}] Downloaded {downloaded} images... (total: {download_count})")

        time.sleep(0.1)  # Rate limit - 10 requests/sec

    print(f"  Completed: {downloaded} new, {skipped} skipped (already exist)")

    # Update progress
    progress[wiki_category] = {
        "folder": folder_path,
        "total_pages": len(members),
        "downloaded": downloaded,
        "skipped": skipped
    }
    save_progress(progress)

    return downloaded

def save_progress(progress):
    """Save download progress to file"""
    DATASET_DIR.mkdir(parents=True, exist_ok=True)
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)

def load_progress():
    """Load download progress from file"""
    if PROGRESS_FILE.exists():
        try:
            with open(PROGRESS_FILE) as f:
                return json.load(f)
        except:
            pass
    return {}

def main():
    global download_count, error_count

    print("=" * 70)
    print("OSRS Wiki COMPLETE Image Downloader")
    print("Downloading ALL images - no limits")
    print(f"Categories to process: {len(CATEGORIES)}")
    print("=" * 70)

    progress = load_progress()
    start_count = download_count

    for wiki_cat, folder in CATEGORIES.items():
        # Skip if already completed
        if wiki_cat in progress and progress[wiki_cat].get("downloaded", 0) > 0:
            print(f"\n[SKIP] {wiki_cat} - already processed")
            continue

        try:
            download_category(wiki_cat, folder, progress)
        except Exception as e:
            print(f"  ERROR processing {wiki_cat}: {e}")
            continue

    total_new = download_count - start_count

    print("\n" + "=" * 70)
    print("DOWNLOAD COMPLETE")
    print(f"New images downloaded: {total_new}")
    print(f"Total images in dataset: {download_count}")
    print(f"Errors: {error_count}")
    print(f"Dataset location: {DATASET_DIR}")
    print("=" * 70)

    # Final folder count
    print("\nFolder summary:")
    for folder in sorted(DATASET_DIR.rglob("*")):
        if folder.is_dir():
            count = len(list(folder.glob("*.png"))) + len(list(folder.glob("*.jpg")))
            if count > 0:
                rel = folder.relative_to(DATASET_DIR)
                print(f"  {rel}/ ({count} images)")

if __name__ == "__main__":
    main()
