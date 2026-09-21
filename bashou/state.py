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
        "pets": ["cat"],
        "active": "cat",
        "achievements": [],
        "fights_won": 0,
        "challenges": [],   # challenges beaten
        "threat": None,     # {"challenge", "until"} while a threat waits for you
        "threat_day": {"date": "", "count": 0},
        "last_threat": 0,
    }


def load():
    try:
        data = json.loads(STATE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default()
    return {**default(), **data}


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
