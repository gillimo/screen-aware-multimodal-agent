import json
from pathlib import Path
from collections import defaultdict

from src.schema_validation import validate_state_schema

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
SCHEMA_PATH = DATA_DIR / "schema.json"
REF_PATH = DATA_DIR / "reference.json"


def load_json(path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def get_reference():
    return load_json(REF_PATH, {})


def validate_state(state):
    errors = []
    if not isinstance(state, dict):
        return ["state must be a JSON object"]
    if "version" not in state:
        errors.append("missing version")
    for key in ["account", "skills", "quests", "diaries", "gear", "unlocks", "goals"]:
        if key not in state:
            errors.append(f"missing {key}")
    errors.extend(validate_state_schema(state))
    return errors


def migrate_state(state):
    if not isinstance(state, dict):
        return state
    version = state.get("version", 0)
    if version == 0:
        state["version"] = 1
    return state


def compute_ratings(state):
    skills = state.get("skills", {})
    combat_keys = ["attack", "strength", "defence", "ranged", "magic", "prayer", "hitpoints"]
    combat_vals = [skills.get(k, 1) for k in combat_keys]
    combat_avg = sum(combat_vals) / max(1, len(combat_vals))
    skill_avg = sum(skills.values()) / max(1, len(skills)) if skills else 0
    quest_count = len(state.get("quests", {}).get("completed", []))
    ratings = {
        "combat_readiness": min(100, int(combat_avg * 1.2)),
        "quest_readiness": min(100, int(quest_count * 2)),
        "skilling_readiness": min(100, int(skill_avg * 1.1)),
        "money_pathing": min(100, int(state.get("account", {}).get("gp", 0) / 100000)),
    }
    reasons = {
        "combat_readiness": ["combat skill average", "prayer level", "hitpoints"],
        "quest_readiness": ["completed quest count", "missing prereqs", "unlock depth"],
        "skilling_readiness": ["average skill level", "tool unlocks", "diary tiers"],
        "money_pathing": ["current gp", "unlocks", "gear tier"],
    }
    return ratings, reasons


def detect_bottlenecks(state):
    skills = state.get("skills", {})
    blockers = []
    if skills.get("prayer", 1) < 43:
        blockers.append("prayer 43 for protection prayers")
    if skills.get("agility", 1) < 50:
        blockers.append("agility 50 for shortcuts and quests")
    if "fairy rings" not in state.get("unlocks", {}).get("teleports", []):
        blockers.append("fairy rings not unlocked")
    return blockers


def build_quest_graph(state):
    ref = get_reference()
    quests = ref.get("quests", [])
    graph = defaultdict(list)
    for q in quests:
        name = q.get("name")
        for req in q.get("quest_reqs", []):
            graph[name].append(req)
    return graph


def onboarding_steps(state):
    account = state.get("account", {})
    mode = account.get("mode", "main")
    steps = [
        "Complete Tutorial Island.",
        "Set a short goal (first quest bundle).",
        "Unlock early teleports (chronicle, rings).",
    ]
    if mode and "iron" in mode:
        steps.append("Plan self-sufficient supplies and avoid GE reliance.")
    return steps


def beginner_quest_bundle(state):
    ref = get_reference()
    return ref.get("beginner_quest_bundle", [])


def gear_food_recs(state):
    ref = get_reference()
    skills = state.get("skills", {})
    cmb = max(skills.get("attack", 1), skills.get("strength", 1), skills.get("defence", 1))
    food = "shrimp"
    for tier in ref.get("food_tiers", []):
        if cmb >= tier.get("min_level", 1):
            food = tier.get("food", food)
    gear = ref.get("gear_tiers", {})
    return {"food": food, "gear_tiers": gear}


def money_guide(state):
    ref = get_reference()
    skills = state.get("skills", {})
    level = max(skills.values()) if skills else 1
    options = [m for m in ref.get("money_methods", []) if level >= m.get("min_level", 1)]
    return options


def teleport_checklist(state):
    ref = get_reference()
    tele = state.get("unlocks", {}).get("teleports", [])
    return {"checklist": ref.get("teleport_checklist", {}), "current": tele}


def glossary_terms():
    ref = get_reference()
    return ref.get("glossary", [])


def boss_readiness(state):
    ref = get_reference()
    skills = state.get("skills", {})
    completed = set(state.get("quests", {}).get("completed", []))
    results = []
    for b in ref.get("boss_readiness", []):
        reqs = b.get("reqs", [])
        stats = b.get("stats", {})
        req_ok = all(r in completed for r in reqs)
        stat_ok = all(skills.get(k, 1) >= v for k, v in stats.items())
        results.append({"name": b.get("name"), "reqs_ok": req_ok, "stats_ok": stat_ok})
    return results


def efficiency_benchmarks():
    ref = get_reference()
    return ref.get("efficiency_benchmarks", [])


def gear_upgrade_optimizer(state):
    ref = get_reference()
    upgrades = ref.get("gear_upgrades", [])
    gp = state.get("account", {}).get("gp", 0)
    viable = [u for u in upgrades if gp >= u.get("gp", 0)]
    viable.sort(key=lambda x: (x.get("impact", ""), -x.get("gp", 0)))
    return viable


def time_to_goal_estimate(state):
    skills = state.get("skills", {})
    goals = state.get("goals", {})
    estimates = []
    for g in goals.get("short", []):
        if "prayer" in g:
            cur = skills.get("prayer", 1)
            target = 43
            remaining = max(0, target - cur)
            estimates.append({"goal": g, "hours": max(1, remaining // 2)})
    return estimates


def ironman_constraints(state):
    mode = state.get("account", {}).get("mode", "")
    return "iron" in (mode or "")


def scheduler_tasks(state):
    ref = get_reference()
    return ref.get("scheduler", {})


def generate_plan(state):
    plan = {"short": [], "mid": [], "long": []}
    skills = state.get("skills", {})
    goals = state.get("goals", {})

    if skills.get("prayer", 1) < 43:
        plan["short"].append({
            "task": "Train Prayer to 43",
            "why": "Unlock protection prayers",
            "time": "2-4h",
            "prereqs": [],
        })
    if "unlock fairy rings" in goals.get("short", []):
        plan["short"].append({
            "task": "Progress Fairy Tale II",
            "why": "Unlock fairy rings",
            "time": "1-2h",
            "prereqs": ["Fairy Tale I"],
        })

    if "barrows gloves" in goals.get("mid", []):
        plan["mid"].append({
            "task": "Recipe for Disaster chain",
            "why": "Best-in-slot gloves",
            "time": "6-12h",
            "prereqs": ["Multiple subquests"],
        })

    if "quest cape" in goals.get("long", []):
        plan["long"].append({
            "task": "Complete all quests",
            "why": "Quest cape unlock",
            "time": "40-100h",
            "prereqs": ["All quest prerequisites"],
        })

    return plan


def compare_paths(state):
    ref = get_reference()
    return ref.get("path_options", [])


def risk_score(state):
    gp = state.get("account", {}).get("gp", 0)
    score = 20 if gp < 100000 else 50 if gp < 1000000 else 70
    return score
