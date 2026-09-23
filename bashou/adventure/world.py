"""Chapters, forks, paths, events and checkpoints. No drawing here: the rules only, easy to test.

A chapter is a few legs. Each leg starts at a fork (the checkpoint) where you pick a topic, then a
path of segments ends with that topic's boss. Beat it: new checkpoint, the topic levels up. Lose (a
boss question, or all your hearts): back to the checkpoint, and you may pick another path.
"""

import random

from . import lessons

SEGMENT = 12.0          # world units between two events: a short stroll, not a trek
HEARTS = 3

# topic: (name, home biome, boss)
TOPICS = {
    "bash": ("Bash", "meadow", "Bash Beast"),
    "linux": ("Linux", "dungeon", "Kernel Warden"),
    "python": ("Python", "forest", "Coil Serpent"),
    "rust": ("Rust", "sand", "Oxide Crab"),
    "c": ("C", "dungeon", "Segfault Golem"),
    "debian": ("Debian", "hills", "Swirl Wraith"),
    "rocky": ("Rocky Linux", "hills", "Stone Titan"),
    "cicd": ("CI/CD", "water", "Pipeline Hydra"),
    "systemd": ("systemd", "dungeon", "Unit Wyrm"),
    "logic": ("Logic", "meadow", "Paradox Sphinx"),
}

CHAPTERS = [
    {"title": "The Sleepy Meadow", "home": "meadow", "legs": 2, "segments": 3,
     "intro": "Your pet stretches, looks at the road, then at you. An adventure starts."},
    {"title": "Dunes of Deprecation", "home": "sand", "legs": 3, "segments": 4,
     "intro": "Old tools lie half-buried in the sand. Some still bite."},
    {"title": "The Dungeon of Daemons", "home": "dungeon", "legs": 3, "segments": 5,
     "intro": "Deep below, processes that never die guard the way."},
]
PLACES = ["Marsh of Merge Conflicts", "Hills of Hanging Processes", "Lake of Lost Packets",
          "Forest of Forgotten Branches", "Caves of Core Dumps", "Desert of Dangling Pointers"]


NEW_ROAD = "A new road, a new quest. Your pet is ready."


def title(ch):
    """A chapter's title in your language: generated ones carry their number, "Lake of Lost Packets (5)"."""
    from ..i18n import _
    return f"{_(ch['title'])} ({ch['number']})" if "number" in ch else _(ch["title"])


def chapter(n):
    """Chapter n (1-based): the first ones are written, then they're generated."""
    if n <= len(CHAPTERS):
        return CHAPTERS[n - 1]
    rng = random.Random(f"chapter:{n}")
    return {"title": rng.choice(PLACES), "number": n, "home": rng.choice(["meadow", "hills", "forest", "sand", "water", "dungeon"]),
            "legs": 3, "segments": min(8, 4 + n // 3), "intro": NEW_ROAD}


def new():
    return {"chapter": 1, "leg": 0, "topic": None, "segment": 0, "distance": 0.0, "leg_start": 0.0,
            "hearts": HEARTS, "levels": {}, "seen": [], "bosses": [], "walked": 0.0, "correct": 0, "phase": "intro",
            "flawless": True, "chapters_done": 0, "trials": [], "lessons": []}


def level(adv, topic):
    """The level of the next path on a topic: 1 the first time, then +1 per boss beaten."""
    return adv["levels"].get(topic, 0) + 1


def fork_options(adv, topics=None):
    """The paths offered at this fork: 2 in the first chapter, 3 later. Same fork, same choice.
    Your skills first (`topics`); others only fill the fork when you picked fewer."""
    rng = random.Random(f"fork:{adv['chapter']}:{adv['leg']}")
    n = 2 if adv["chapter"] == 1 else 3
    mine = sorted(t for t in (topics or TOPICS) if t in TOPICS)
    if len(mine) >= n:
        return rng.sample(mine, n)
    return mine + rng.sample(sorted(set(TOPICS) - set(mine)), n - len(mine))


def events(adv):
    """Events along the current path (one per segment), then the boss."""
    ch = chapter(adv["chapter"])
    rng = random.Random(f"path:{adv['chapter']}:{adv['leg']}:{adv['topic']}")
    kinds = ["monster"] + [rng.choice(["monster", "monster", "chest"]) for _ in range(ch["segments"] - 1)]
    if lesson(adv) and len(kinds) >= 3:
        kinds[1:3] = ["lesson", "chest"]                  # learn it, then use it right away
    return kinds + ["boss"]


def lesson(adv):
    """The lesson waiting on this path: fixed when the path is chosen, so the road doesn't change."""
    if adv.get("path_lesson") is None and adv["topic"]:
        found = lessons.next_for(adv["topic"], adv.get("lessons", []))
        adv["path_lesson"] = found["id"] if found else ""
    return adv.get("path_lesson") or None


def next_event_at(adv):
    return adv["leg_start"] + (adv["segment"] + 1) * SEGMENT


def biome(adv, distance=None):
    """The chapter's biome for the first segment of a leg, then the path topic's own."""
    d = adv["distance"] if distance is None else distance
    if adv["topic"] is None or d - adv["leg_start"] < SEGMENT * 0.8:
        return chapter(adv["chapter"])["home"]
    return TOPICS[adv["topic"]][1]


def choose(adv, topic):
    adv.update(topic=topic, segment=0, phase="walk", flawless=True, path_lesson=None)
    lesson(adv)


def walk(adv, units):
    """Walk forward, up to the next event. Returns the event reached, or None."""
    target = next_event_at(adv)
    step = max(0.0, min(units, target - adv["distance"]))   # max: saves from when paths were longer
    adv["distance"] += step
    adv["walked"] += step
    if adv["distance"] >= target - 1e-9:
        kind = events(adv)[adv["segment"]]
        adv["phase"] = kind
        return kind
    return None


def event_done(adv):
    """After a monster, a chest or a lesson: on to the next segment."""
    adv["segment"] += 1
    adv["phase"] = "walk"


def lose_heart(adv):
    """A wrong answer (monster or boss). Returns True when that was the last heart (back to the checkpoint)."""
    adv["hearts"] -= 1
    adv["flawless"] = False
    if adv["hearts"] <= 0:
        back_to_checkpoint(adv)
        return True
    return False


def back_to_checkpoint(adv):
    adv.update(distance=adv["leg_start"], topic=None, segment=0, hearts=HEARTS, phase="fork", path_lesson=None)


def boss_won(adv):
    """A new checkpoint: the topic levels up, next leg (or the chapter is done)."""
    topic = adv["topic"]
    adv["levels"][topic] = adv["levels"].get(topic, 0) + 1
    adv["bosses"].append({"topic": topic, "level": adv["levels"][topic], "flawless": adv["flawless"]})
    adv.update(leg=adv["leg"] + 1, leg_start=adv["distance"], topic=None, segment=0, hearts=HEARTS)
    if adv["leg"] >= chapter(adv["chapter"])["legs"]:
        adv["phase"] = "chapter_end"
        adv["chapters_done"] += 1
    else:
        adv["phase"] = "fork"


def next_chapter(adv):
    adv.update(chapter=adv["chapter"] + 1, leg=0, leg_start=adv["distance"], phase="intro")


def boss_questions(adv):
    """3 questions at level 1, one more per level (the last leg of a chapter: one more still)."""
    last = adv["leg"] == chapter(adv["chapter"])["legs"] - 1
    return 2 + level(adv, adv["topic"]) + last
