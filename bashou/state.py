"""Persistent state shared by every terminal, guarded by a file lock."""

import fcntl
import json
import os
from contextlib import contextmanager
from pathlib import Path

DATA = Path(os.environ.get("BASHOU_DATA", Path.home() / ".local/share/bashou"))
CACHE = Path(os.environ.get("BASHOU_CACHE", Path.home() / ".cache/bashou"))
STATE = DATA / "state.json"


def default():
    return {
        "version": 1,
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
        "challenges": [],   # challenges beaten
        "security": [],     # security challenges solved (`bashou security`)
        "adventure": None,  # `bashou adventure` progress (see bashou/adventure)
        "threat": None,     # {"challenge", "until"} while a threat waits for you
        "threat_day": {"date": "", "count": 0},
        "last_threat": 0,
        "update_checked": 0,   # last time a terminal looked for a new version
        "update_available": "",  # newest release tag not installed yet, at that check
        "settings": {},     # `bashou config`, only what differs from SETTINGS
        "looks": {},        # pet or "starter" -> form shown (1-3) when not the latest (`f` in `bashou swap`)
        "evolving": [],     # evolutions waiting to be watched: {"who", "from", "to"} (`bashou evolve`)
    }


# name: (default (low, high), help)
SETTINGS = {
    "bubble": ((5, 10), "commands a speech bubble stays on screen (e.g. 5-10, or 3)"),
    "updates": ("on", "look for a new version once a day (on/off)"),
}


def setting(state, name):
    value = state.get("settings", {}).get(name, SETTINGS[name][0])
    return tuple(value) if isinstance(value, (list, tuple)) else value


def show(value):
    return f"{value[0]}-{value[1]}" if isinstance(value, tuple) else value


def parse(name, text):
    """Check a new value against the setting's kind; ValueError if it doesn't fit."""
    if isinstance(SETTINGS[name][0], tuple):
        return list(parse_range(text))
    if text not in ("on", "off"):
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
        data = json.loads(STATE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default()
    return migrate({**default(), **data})


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
    return state


def save(state):
    DATA.mkdir(parents=True, exist_ok=True)
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=1))
    os.replace(tmp, STATE)


@contextmanager
def locked():
    """Load the state under an exclusive lock and save it on exit."""
    DATA.mkdir(parents=True, exist_ok=True)
    with open(DATA / ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = load()
        yield state
        save(state)
