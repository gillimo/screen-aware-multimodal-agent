import json
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from src.engine import (
    compute_ratings,
    generate_plan,
    detect_bottlenecks,
    build_quest_graph,
    onboarding_steps,
    beginner_quest_bundle,
    teleport_checklist,
    glossary_terms,
    boss_readiness,
    efficiency_benchmarks,
    scheduler_tasks,
    gear_food_recs,
    money_guide,
)

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "data" / "state.json"


def load_state():
    if not STATE_PATH.exists():
        return {}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _add_label_block(parent, text):
    ttk.Label(parent, text=text, justify="left").pack(anchor="w", padx=12, pady=12)


def run_app():
    state = load_state()
    root = tk.Tk()
    root.title("OSRS Coach")
    root.geometry("980x560")

    paned = ttk.Panedwindow(root, orient="horizontal")
    paned.pack(fill="both", expand=True)

    left = ttk.Frame(paned)
    right = ttk.Frame(paned)
    paned.add(left, weight=2)
    paned.add(right, weight=1)

    notebook = ttk.Notebook(left)
    notebook.pack(fill="both", expand=True)

    overview = ttk.Frame(notebook)
    plan = ttk.Frame(notebook)
    quests = ttk.Frame(notebook)
    diaries = ttk.Frame(notebook)
    gear = ttk.Frame(notebook)
    money = ttk.Frame(notebook)
    skills = ttk.Frame(notebook)
    ratings = ttk.Frame(notebook)
    onboarding = ttk.Frame(notebook)
    teleports = ttk.Frame(notebook)
    glossary = ttk.Frame(notebook)
    readiness = ttk.Frame(notebook)
    benchmarks = ttk.Frame(notebook)
    scheduler = ttk.Frame(notebook)
    notes = ttk.Frame(notebook)

    notebook.add(overview, text="Overview")
    notebook.add(plan, text="Plan")
    notebook.add(quests, text="Quests")
    notebook.add(diaries, text="Diaries")
    notebook.add(gear, text="Gear")
    notebook.add(money, text="Money")
    notebook.add(skills, text="Skills")
    notebook.add(ratings, text="Ratings")
    notebook.add(onboarding, text="Onboarding")
    notebook.add(teleports, text="Teleports")
    notebook.add(glossary, text="Glossary")
    notebook.add(readiness, text="Readiness")
    notebook.add(benchmarks, text="Benchmarks")
    notebook.add(scheduler, text="Scheduler")
    notebook.add(notes, text="Notes")

    account = state.get("account", {})
    skills = state.get("skills", {})
    goals = state.get("goals", {})

    avg_skill = sum(skills.values()) / max(1, len(skills)) if skills else 0
    overview_text = (
        f"Name: {account.get('name', 'Unknown')}\n"
        f"Mode: {account.get('mode', 'main')}\n"
        f"Combat level: {account.get('combat_level', 'n/a')}\n"
        f"GP: {account.get('gp', 0)}\n"
        f"Avg skill: {avg_skill:.1f}"
    )
    _add_label_block(overview, overview_text)

    plan_data = generate_plan(state)
    plan_lines = []
    for horizon in ["short", "mid", "long"]:
        plan_lines.append(f"{horizon.title()} horizon:")
        items = plan_data.get(horizon, [])
        if not items:
            plan_lines.append("- none")
        for item in items:
            plan_lines.append(f"- {item.get('task')} ({item.get('time')})")
            plan_lines.append(f"  why: {item.get('why')}")
    _add_label_block(plan, "\n".join(plan_lines))
    bundle_lines = ["Beginner quest bundle:"]
    for q in beginner_quest_bundle(state):
        bundle_lines.append(f"- {q.get('name')}: {q.get('why')}")
    _add_label_block(plan, "\n".join(bundle_lines))

    quest_lines = [
        "Quest coach uses data/reference.json.",
    ]
    _add_label_block(quests, "\n".join(quest_lines))
    tree = ttk.Treeview(quests)
    tree.pack(fill="both", expand=True, padx=12, pady=12)
    graph = build_quest_graph(state)
    for quest, prereqs in graph.items():
        parent = tree.insert("", "end", text=quest)
        for req in prereqs:
            tree.insert(parent, "end", text=req)

    _add_label_block(diaries, "Diary coach (stub). Use CLI: python run_coach.py diaries")
    gear_data = gear_food_recs(state)
    _add_label_block(gear, f"Suggested food: {gear_data.get('food')}")
    _add_label_block(money, "Money methods:\n- " + "\n- ".join([m.get("method") for m in money_guide(state)]))
    _add_label_block(skills, "Skills coach (stub). Update data/reference.json for methods.")

    ratings_data, reasons = compute_ratings(state)
    rating_lines = []
    for k, v in ratings_data.items():
        rating_lines.append(f"{k.replace('_', ' ').title()}: {v}/100")
        for r in reasons.get(k, [])[:3]:
            rating_lines.append(f"- {r}")
    blockers = detect_bottlenecks(state)
    rating_lines.append("")
    rating_lines.append("Top blockers:")
    rating_lines.append("- " + ("\n- ".join(blockers) if blockers else "none"))
    _add_label_block(ratings, "\n".join(rating_lines))

    _add_label_block(onboarding, "\n".join([f\"{idx}) {s}\" for idx, s in enumerate(onboarding_steps(state), start=1)]))

    tele = teleport_checklist(state)
    tele_lines = []
    for phase, items in tele.get(\"checklist\", {}).items():
        tele_lines.append(f\"{phase}: {', '.join(items)}\")
    tele_lines.append(\"Current: \" + \", \".join(tele.get(\"current\", [])))
    _add_label_block(teleports, \"\\n\".join(tele_lines))

    gloss_lines = [f\"- {g.get('term')}: {g.get('def')}\" for g in glossary_terms()]
    _add_label_block(glossary, \"\\n\".join(gloss_lines))

    ready_lines = [f\"- {r.get('name')}: {'ready' if r.get('reqs_ok') and r.get('stats_ok') else 'not ready'}\" for r in boss_readiness(state)]
    _add_label_block(readiness, \"\\n\".join(ready_lines))

    bench_lines = [f\"- {b.get('skill')}: {b.get('method')} {b.get('xp_hr')} xp/hr\" for b in efficiency_benchmarks()]
    _add_label_block(benchmarks, \"\\n\".join(bench_lines))

    sched = scheduler_tasks(state)
    sched_lines = [\"Daily: \" + \", \".join(sched.get(\"daily\", [])), \"Weekly: \" + \", \".join(sched.get(\"weekly\", []))]
    _add_label_block(scheduler, \"\\n\".join(sched_lines))

    notes_box = tk.Text(notes, height=10, wrap="word")
    notes_box.insert("end", "Session notes...\n")
    notes_box.pack(fill="both", expand=True, padx=12, pady=12)

    chat_frame = ttk.Frame(right)
    chat_frame.pack(fill="both", expand=True, padx=8, pady=8)
    ttk.Label(chat_frame, text="Coach Chat").pack(anchor="w")

    chat_log = tk.Text(chat_frame, height=20, wrap="word", state="disabled")
    chat_log.pack(fill="both", expand=True, pady=(6, 6))

    entry_frame = ttk.Frame(chat_frame)
    entry_frame.pack(fill="x")
    entry = ttk.Entry(entry_frame)
    entry.pack(side="left", fill="x", expand=True)

    def append_message(sender, text):
        chat_log.configure(state="normal")
        chat_log.insert("end", f"{sender}: {text}\n")
        chat_log.configure(state="disabled")
        chat_log.see("end")

    def on_send():
        msg = entry.get().strip()
        if not msg:
            return
        entry.delete(0, "end")
        append_message("You", msg)
        append_message("Coach", "Placeholder response. Hook local model here.")

    send_btn = ttk.Button(entry_frame, text="Send", command=on_send)
    send_btn.pack(side="right", padx=(6, 0))

    entry.bind("<Return>", lambda _event: on_send())

    root.mainloop()


if __name__ == "__main__":
    run_app()
