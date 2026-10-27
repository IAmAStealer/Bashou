"""Question banks (questions/<lang>/<topic>.json), picked by level without repeats."""

import json
from pathlib import Path

from .. import i18n, skills

HERE = Path(__file__).resolve().parent / "questions"


MORE = {"linux": ("systemd",)}    # banks a topic also asks (owner, 2026-10-27: systemd is part of Linux)


def bank(topic, lang=None):
    """Questions of a topic in your language, or in English when there's no translation yet."""
    found = []
    for name in (topic, *MORE.get(topic, ())):
        for code in (lang or i18n.language(), "en"):
            path = HERE / code / f"{name}.json"
            if path.exists():
                found += json.loads(path.read_text())
                break
    return found


def for_os(questions, systems):
    """The questions for everyone, and those of the systems you learn about (a question may say "os")."""
    return [q for q in questions if skills.shows(q, systems)]


def max_level(topic, systems=None):
    return max((q["level"] for q in for_os(bank(topic, "en"), systems or skills.OSES["both"])), default=1)


def pick(topic, level, seen, rng, systems=None):
    """A question at `level` (the highest available if above) about the systems you learn (`systems`, all
    when None), one you haven't seen while there are any left, with its choices shuffled (so positions
    can't be memorized)."""
    systems = systems or skills.OSES["both"]
    level = min(level, max_level(topic, systems))
    pool = [q for q in for_os(bank(topic), systems) if q["level"] == level]
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
        if q.get("os") not in (None, *skills.OS_NAMES):
            found.append(f"{where}: os is linux or macos (or no os: for everyone)")
        if not q.get("q") or not q.get("explain"):
            found.append(f"{where}: needs q and explain")
        if len(q.get("q", "")) > 150 or any(len(c) > 60 for c in q.get("choices", [])) \
                or len(q.get("explain", "")) > 400:
            found.append(f"{where}: too long for the screen (question 150, choices 60, explain 400 characters)")
    return found
