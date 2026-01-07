from __future__ import annotations

from typing import Iterable


RANDOM_EVENT_KEYWORDS = (
    "random event",
    "mysterious old man",
    "genie",
    "drunken dwarf",
    "quiz master",
    "river troll",
    "surprise exam",
    "frog",
    "bee keeper",
    "certer",
    "evil bob",
    "sandwich lady",
)


def is_random_event_message(lines: Iterable[str]) -> bool:
    for line in lines:
        lowered = line.lower()
        if any(keyword in lowered for keyword in RANDOM_EVENT_KEYWORDS):
            return True
    return False


def should_respond_to_chat(lines: Iterable[str]) -> bool:
    return not is_random_event_message(lines)
