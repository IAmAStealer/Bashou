"""Question banks (questions/<lang>/<topic>.json), picked by level without repeats."""

import json
from pathlib import Path

from .. import i18n
from ..which import installed

HERE = Path(__file__).resolve().parent / "questions"


def bank(topic, lang=None):
    """Questions of a topic in your language, or in English when there's no translation yet."""
    for code in (lang or i18n.language(), "en"):
        path = HERE / code / f"{topic}.json"
        if path.exists():
            return json.loads(path.read_text())
    return []


def max_level(topic):
    return max((q["level"] for q in bank(topic, "en")), default=1)


def usable(q, needs):
    """Not about a command this system is missing (`needs` comes from the English bank)."""
    return not needs.get(q["id"]) or any(map(installed, needs[q["id"]]))


def pick(topic, level, seen, rng):
    """A question at `level` (the highest available if above), one you haven't seen while there are
    any left, with its choices shuffled (so positions can't be memorized). Questions whose answer is
    a command you don't have (`"needs": ["systemctl"]`) are skipped."""
    level = min(level, max_level(topic))
    needs = {q["id"]: q.get("needs") for q in bank(topic, "en")}
    items = [q for q in bank(topic) if usable(q, needs)] or bank(topic)
    pool = [q for q in items if q["level"] == level] or items
    q = rng.choice([q for q in pool if q["id"] not in seen] or pool)
    order = list(range(len(q["choices"])))
    rng.shuffle(order)
    return {**q, "choices": [q["choices"][i] for i in order], "answer": order.index(q["answer"])}


def problems(items):
    """What's wrong in a bank (for tests and contributors)."""
    found, ids = [], set()
    for q in items:
        where = q.get("id", "?")
        if where in ids:
            found.append(f"{where}: duplicate id")
        ids.add(where)
        if not isinstance(q.get("level"), int) or q["level"] < 1:
            found.append(f"{where}: level must be 1, 2, 3…")
        if len(q.get("choices", [])) != 4 or len(set(q.get("choices", []))) != 4:
            found.append(f"{where}: 4 different choices")
        if q.get("answer") not in range(4):
            found.append(f"{where}: answer is the index (0-3) of the right choice")
        if not q.get("q") or not q.get("explain"):
            found.append(f"{where}: needs q and explain")
        if not isinstance(q.get("needs", []), list):
            found.append(f"{where}: needs is a list of commands")
        if len(q.get("q", "")) > 110 or any(len(c) > 60 for c in q.get("choices", [])):
            found.append(f"{where}: too long for the screen (question 110, choices 60 characters)")
    return found
