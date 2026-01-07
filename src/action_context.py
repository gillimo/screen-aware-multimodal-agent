from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass
class ActionContext:
    intent_id: str
    timing: Dict[str, float] = field(default_factory=dict)
    motion: Dict[str, float] = field(default_factory=dict)


class ActionContextLogger:
    def __init__(self, path: Optional[Path] = None):
        if path is None:
            root = Path(__file__).resolve().parents[1]
            path = root / "logs" / "action_context.jsonl"
        path.parent.mkdir(exist_ok=True)
        self.path = path

    def log(self, context: ActionContext) -> None:
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(context.__dict__) + "\n")
