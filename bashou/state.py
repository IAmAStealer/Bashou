"""Persistent state shared by every terminal, guarded by a file lock."""

import fcntl
import json
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

DATA = Path(os.environ.get("BASHOU_DATA", Path.home() / ".local/share/bashou"))
CACHE = Path(os.environ.get("BASHOU_CACHE", Path.home() / ".cache/bashou"))
STATE = DATA / "state.json"
SAVE_VERSION = 2        # bump with a step in migrate() whenever the save's shape changes


def default():
    return {
        "version": SAVE_VERSION,
        "commands": 0,
        "tools": {},        # tool -> successful uses
        "constructs": {},   # construct -> uses
        "days": [],         # ISO dates with at least one command
        "today": {"date": "", "count": 0},
        "language": None,   # "en", "fr"…, asked once at first launch (`bashou language`)
        "starter": None,    # "star", "sprout" or "pebble", chosen once (`bashou start`)
        "pets": [],         # collection pets unlocked
        "active": "starter",
        "achievements": [],
        "fights_won": 0,
        "fights_lost": 0,   # knocked out or fled (the Living sofa comforts you)
        "ladder_best": {},  # pet -> highest form reached on a command ladder (the Slime): never goes back
        "challenges": [],   # challenges beaten
        "skills": "all",    # "all" or the skills you ticked (`bashou skills`, asked before the starter)
        "reviews": {},      # beaten fight -> {"step": reviews won, "due": ISO date}: it comes back (fight.py)
        "security": [],     # security challenges solved (`bashou security`)
        "adventure": None,  # `bashou adventure` progress (see bashou/adventure)
        "threat": None,     # {"challenge", "until"} while a threat waits for you
        "threat_day": {"date": "", "count": 0},
        "last_threat": 0,
        "update_checked": 0,   # last time a terminal looked for a new version
        "update_available": "",  # newest release tag not installed yet, at that check
        "settings": {},     # `bashou config`, only what differs from SETTINGS
        "looks": {},        # pet or "starter" -> form shown when not the latest (`f` in `bashou swap`)
        "starter_best": 1,  # the starter's highest form reached: it never goes back
        "evolving": [],     # evolutions waiting to be watched: {"who", "from", "to"} (`bashou evolve`)
    }


# name: (default (low, high), help)
SETTINGS = {
    "bubble": ((5, 10), "commands a speech bubble stays on screen (e.g. 5-10, or 3)"),
    "updates": ("on", "look for a new version once a day (on/off)"),
    "size": ("small", "pet size: small, or large for pets that have big pixel art (small/large)"),
    "talk": ((10, 20), "minutes between the things your pet says on its own (e.g. 10-20, 30, or off)"),
    "quiet": ((60, 60), "seconds without typing before it says one (it waits for a pause in your work)"),
}
CHOICES = {"updates": ("on", "off"), "size": ("small", "large")}
OFFABLE = {"talk"}                  # ranges that also accept "off"


def setting(state, name):
    value = state.get("settings", {}).get(name, SETTINGS[name][0])
    return tuple(value) if isinstance(value, (list, tuple)) else value


def show(value):
    if not isinstance(value, tuple):
        return value
    return str(value[0]) if value[0] == value[1] else f"{value[0]}-{value[1]}"


def parse(name, text):
    """Check a new value against the setting's kind; ValueError if it doesn't fit."""
    if isinstance(SETTINGS[name][0], tuple):
        if name in OFFABLE and text == "off":
            return "off"
        return list(parse_range(text))
    if text not in CHOICES[name]:
        raise ValueError(text)
    return text


def parse_range(text):
    """"5-10" or "3" -> (low, high); ValueError if not 1 <= low <= high."""
    low, _, high = text.partition("-")
    low, high = int(low), int(high or low)
    if not 1 <= low <= high:
        raise ValueError(text)
    return low, high


def load():
    try:
        text = STATE.read_text()
    except FileNotFoundError:
        return default()
    try:
        return read(text)
    except Exception:           # a damaged file or a save we can't migrate: never lose it silently
        return recover(text)


def read(text):
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("not a save")
    state = {**default(), **data}
    for key, value in default().items():                  # a field of the wrong type: its default
        if value is None or key == "skills":
            continue
        kind = (int, float) if isinstance(value, (int, float)) else type(value)
        if not isinstance(state[key], kind):
            state[key] = value
    for key in ("starter_best", "ladder_best", "reviews"):
        if key not in data:
            del state[key]                                 # an old save: migrate() sets it
    return migrate(state)


def prev():
    """A copy of a good save, at most a day old."""
    return STATE.with_name("state.json.prev")


def recover(text):
    """Keep the unreadable save next to it, then start again from the newest copy that reads."""
    broken = STATE.with_name(f"state.json.broken-{time.strftime('%Y%m%d-%H%M%S')}")
    try:
        if STATE.read_text() != text:                     # another terminal saved meanwhile
            return read(STATE.read_text())
        os.replace(STATE, broken)
    except FileNotFoundError:                              # another terminal is already on it
        return load() if STATE.exists() else default()
    for copy in [prev(), *sorted(STATE.parent.glob("state.json.bak-*"), reverse=True)]:
        try:
            state = read(copy.read_text())
        except Exception:
            continue
        save(state)
        print(f"bashou: your save couldn't be read, kept as {broken}; restored {copy.name}.", file=sys.stderr)
        return state
    print(f"bashou: your save couldn't be read, kept as {broken}; starting over.", file=sys.stderr)
    return default()


def migrate(state):
    """Old saves: the cat in the collection became the starter, and the cat starter became the star."""
    if state["starter"] is None and "cat" in state["pets"]:
        state["starter"] = "star"
    if state["starter"] == "cat":
        state["starter"] = "star"
    if "cat" in state["pets"]:
        state["pets"].remove("cat")
    if state["active"] == "cat":
        state["active"] = "starter"
    if "starter_best" not in state:
        migrate_ladder(state)
    if "ladder_best" not in state:
        migrate_slime(state)
    if "reviews" not in state:
        migrate_reviews(state)
    state["version"] = SAVE_VERSION
    return state


def migrate_reviews(state):
    """Fights beaten before reviews existed come back too: one a day from tomorrow, not all at once."""
    import datetime
    today = datetime.date.today()
    state["reviews"] = {cid: {"step": 0, "due": (today + datetime.timedelta(days=i + 1)).isoformat()}
                        for i, cid in enumerate(state["challenges"])}


def migrate_slime(state):
    """The Slime evolved with its achievement family before it had a command ladder: keep its form."""
    from .creatures import FORMS
    fam = ("capture", "nested", "substitute", "here")      # the family it had until 0.2.3
    earned = sum(a in state.get("achievements", []) for a in fam)
    state["ladder_best"] = {"slime": len(FORMS["slime"]) if earned == len(fam) else 2 if earned >= 2 else 1}


# Before starters had long ladders (0.2.3 and older): 3 forms, at levels 4 and 7 (level max 9).
OLD_LADDERS = {"star": ("stardust", "planet", "star"), "sprout": ("seedling", "sprout", "tree"),
               "pebble": ("pebble", "golem", "crystal")}


def migrate_ladder(state):
    """Form numbers of an old save are places on the old 3-form ladder: turn them into places on the
    new one, and keep the form reached (a Planet stays a Planet until it becomes a Star)."""
    from .creatures import STARTERS
    line = state.get("starter")
    state["starter_best"] = 1
    if line not in OLD_LADDERS or line not in STARTERS:
        return

    def new(old_form):
        sprite = OLD_LADDERS[line][max(1, min(3, old_form)) - 1]
        return STARTERS[line].index(sprite) + 1 if sprite in STARTERS[line] else 1

    level = 1 + min(8, len(state.get("achievements", [])) // 5)
    state["starter_best"] = new((level - 1) // 3 + 1)
    if "starter" in state.get("looks", {}):
        state["looks"]["starter"] = new(state["looks"]["starter"])
    for e in state.get("evolving", []):
        if e["who"] == "starter":
            e["from"], e["to"] = new(e["from"]), new(e["to"])


def save(state):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    text = json.dumps(state, indent=1)
    tmp.write_text(text)
    os.replace(tmp, STATE)
    try:
        stale = time.time() - prev().stat().st_mtime > 24 * 3600
    except FileNotFoundError:
        stale = True
    if stale:
        tmp.write_text(text)
        os.replace(tmp, prev())


def keep_old_format():
    """A save from an older version is upgraded on disk by the next save: keep a copy of it first."""
    try:
        old = json.loads(STATE.read_text()).get("version", 1)
        if isinstance(old, int) and old < SAVE_VERSION:
            name = f"state.json.bak-{time.strftime('%Y%m%d-%H%M%S')}-v{old}"
            STATE.with_name(name).write_text(STATE.read_text())
    except (OSError, ValueError, AttributeError):
        pass


@contextmanager
def locked():
    """Load the state under an exclusive lock and save it on exit."""
    DATA.mkdir(parents=True, exist_ok=True)
    with open(DATA / ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        keep_old_format()
        state = load()
        yield state
        save(state)
