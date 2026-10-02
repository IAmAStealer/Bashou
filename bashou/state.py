"""Persistent state shared by every terminal, guarded by a file lock."""

import copy
import datetime
import fcntl
import json
import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from . import achievements, creatures, i18n

DATA = Path(os.environ.get("BASHOU_DATA", Path.home() / ".local/share/bashou"))
CACHE = Path(os.environ.get("BASHOU_CACHE", Path.home() / ".cache/bashou"))
STATE = DATA / "state.json"
SAVE_VERSION = 4        # bump with a step in migrate() whenever the save's shape changes


@dataclass(frozen=True)
class Setting:
    """A `bashou config` setting: one of `choices`, or else a range of numbers ("5-10", or "3")."""
    default: object
    help: str
    choices: tuple = ()
    off: bool = False           # a range that also takes "off"

    def parse(self, text):
        """The value to save for what you typed; ValueError if it doesn't fit."""
        if self.choices:
            if text not in self.choices:
                raise ValueError(text)
            return text
        return "off" if self.off and text == "off" else list(parse_range(text))

    def fits(self, value):
        """A saved value this setting could have written (a damaged one doesn't)."""
        if self.choices:
            return value in self.choices
        return (self.off and value == "off") or (
            isinstance(value, list) and len(value) == 2 and all(type(n) is int for n in value) and 1 <= value[0] <= value[1])


SETTINGS = {
    "bubble": Setting((5, 10), "commands a speech bubble stays on screen (e.g. 5-10, or 3)"),
    "updates": Setting("on", "look for a new version once a day (on/off)", choices=("on", "off")),
    "size": Setting("small", "pet size: small, or large for pets that have big pixel art (small/large)",
                    choices=("small", "large")),
    "talk": Setting((10, 20), "minutes between the things your pet says on its own (e.g. 10-20, 30, or off)", off=True),
    "quiet": Setting((60, 60), "seconds without typing before it says one (it waits for a pause in your work)"),
    "editor": Setting("nano", "the text editor your hints and lessons show (nano/vi)", choices=("nano", "vi")),
}


def setting(state, name):
    value = state.get("settings", {}).get(name, SETTINGS[name].default)
    return tuple(value) if isinstance(value, (list, tuple)) else value


def show(value):
    if not isinstance(value, tuple):
        return value
    return str(value[0]) if value[0] == value[1] else f"{value[0]}-{value[1]}"


def parse(name, text):
    """Check a new value against the setting's kind; ValueError if it doesn't fit."""
    return SETTINGS[name].parse(text)


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


# --- what a save holds ---------------------------------------------------------------------------
# Each field: its default, and a check that returns the value cleaned or raises ValueError (the field
# then gets its default). Inside a list or a dict, a damaged entry is dropped and the rest kept: one
# wrong byte on disk (or a hand edit) used to make the pet crash at every frame. (Found by fuzzing.)

NUMBER = (int, float)


def kind(*types):
    def check(value):
        if not isinstance(value, types):
            raise ValueError(value)
        return value
    return check


def optional(check):
    return lambda value: None if value is None else check(value)


def fits(check, value):
    try:
        check(value)
        return True
    except (ValueError, TypeError, KeyError, AttributeError):
        return False


def list_of(check):
    return lambda value: [v for v in kind(list)(value) if fits(check, v)]


def dict_of(check):
    return lambda value: {k: v for k, v in kind(dict)(value).items() if fits(check, v)}


def record(**fields):
    """A dict holding each field with its type (more keys are kept)."""
    def check(value):
        if not (isinstance(value, dict) and all(isinstance(value.get(k), t) for k, t in fields.items())):
            raise ValueError(value)
        return value
    return check


def skills_choice(value):
    ok = value == "all" or isinstance(value, list) and all(isinstance(s, str) for s in value)
    return value if ok else "all"


def lessons_progress(value):
    value = {**LESSONS, **kind(dict)(value)}
    return {**value, **{k: list_of(kind(str))(value[k]) if isinstance(value[k], list) else [] for k in ("read", "opened", "met")},
            "page": value["page"] if isinstance(value["page"], dict) else {}}


def adventure_progress(adv):
    """What the pet reads of the adventure (its achievements, at every frame). The rest is only read by
    `bashou adventure`."""
    adv = kind(dict)(adv)
    for key in ("walked", "chapters_done"):
        if key in adv and not isinstance(adv[key], NUMBER):
            del adv[key]
    if "bosses" in adv:
        adv["bosses"] = list_of(record(topic=str))(adv["bosses"]) if isinstance(adv["bosses"], list) else []
    if "trials" in adv and not isinstance(adv["trials"], list):
        adv["trials"] = []
    if "levels" in adv:
        adv["levels"] = dict_of(kind(*NUMBER))(adv["levels"]) if isinstance(adv["levels"], dict) else {}
    return adv


def settings_of(value):
    """Only settings that exist, with a value `bashou config` would accept."""
    return {k: v for k, v in kind(dict)(value).items() if k in SETTINGS and SETTINGS[k].fits(v)}


LESSONS = {"read": [], "opened": [], "page": {}, "met": []}
PROJECTS = {"current": "", "done": {}, "days": []}


def projects_progress(value):
    """`bashou project`: the current project, steps done per project, days with a step done."""
    value = {**PROJECTS, **kind(dict)(value)}
    return {"current": value["current"] if isinstance(value["current"], str) else "",
            "done": dict_of(kind(int))(value["done"]) if isinstance(value["done"], dict) else {},
            "days": list_of(kind(str))(value["days"]) if isinstance(value["days"], list) else []}
COUNT = {"date": "", "count": 0}
FIELDS = {
    "version": (SAVE_VERSION, kind(int)),
    "commands": (0, kind(*NUMBER)),
    "tools": ({}, dict_of(kind(*NUMBER))),            # tool -> successful uses
    "constructs": ({}, dict_of(kind(*NUMBER))),       # construct -> uses
    "days": ([], list_of(kind(str))),                 # ISO dates with at least one command
    "today": (COUNT, record(date=str, count=NUMBER)),
    "language": (None, optional(kind(str))),          # "en", "fr"…, asked once at first launch (`bashou config language`)
    "starter": (None, optional(kind(str))),           # "star", "sprout" or "pebble", chosen once (`bashou start`)
    "pets": ([], list_of(kind(str))),                 # collection pets unlocked
    "active": ("starter", kind(str)),
    "achievements": ([], list_of(kind(str))),
    "fights_won": (0, kind(*NUMBER)),
    "fights_lost": (0, kind(*NUMBER)),                # knocked out or fled (the Living sofa comforts you)
    "ladder_best": ({}, dict_of(kind(str, int))),     # pet -> highest form (sprite id) reached on a command ladder
    "challenges": ([], list_of(kind(str))),           # challenges beaten
    "skills": ("all", skills_choice),                 # "all" or the skills you ticked (`bashou config skills`)
    "reviews": ({}, dict_of(record(step=int, due=str))),   # beaten fight -> {"step", "due"}: it comes back (fight.py)
    "security": ([], list_of(kind(str))),             # security challenges solved (`bashou arena security`)
    "arena_closed_until": (0, kind(*NUMBER)),         # `bashou arena` after a defeat: closed until then (epoch seconds)
    "adventure": (None, optional(adventure_progress)),     # `bashou adventure` progress (see bashou/adventure)
    "threat": (None, optional(record(challenge=str, until=NUMBER))),   # while a threat waits for you
    "threat_day": (COUNT, record(date=str, count=NUMBER)),
    "last_threat": (0, kind(*NUMBER)),
    "update_checked": (0, kind(*NUMBER)),             # last time a terminal looked for a new version
    "update_available": ("", kind(str)),              # newest release tag not installed yet, at that check
    "settings": ({}, settings_of),                    # `bashou config`, only what differs from SETTINGS
    "looks": ({}, dict_of(kind(str, int))),           # pet or "starter" -> form (sprite id) shown when not the latest
    "starter_best": (None, optional(kind(str, int))), # the starter's highest form (sprite id) reached: never goes back
    "evolving": ([], list_of(record(who=str, **{"from": (str, int), "to": (str, int)}))),   # for `bashou evolve`
    "lessons": (LESSONS, lessons_progress),           # `bashou lesson`: read, opened, page to resume, fights met
    "share_name": ("", kind(str)),                    # the nickname on `bashou share` cards
    "projects": (PROJECTS, projects_progress),        # `bashou project`: current one, steps done, days
}


def default():
    return {name: copy.deepcopy(value) for name, (value, _check) in FIELDS.items()}


def clean(state):
    """Every field as FIELDS describes it; a field that doesn't fit gets its default."""
    for name, (value, check) in FIELDS.items():
        try:
            state[name] = check(state[name])
        except (ValueError, TypeError, KeyError, AttributeError):
            state[name] = copy.deepcopy(value)
    clean_game(state)


def clean_game(state):
    """What only the game knows: a starter and pets that exist."""
    if state["starter"] not in {*creatures.STARTERS, "cat", None}:
        state["starter"] = None                            # unreadable: `bashou start` asks again (cat: migrate())
    state["pets"] = [p for p in state["pets"] if p in creatures.FAMILIES]
    if state["active"] != "starter" and state["active"] not in state["pets"]:
        state["active"] = "starter"


def read(text):
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("not a save")
    state = {**default(), **data}
    clean(state)
    return migrate(state, data)


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


def fix_shared_ids(state):
    """Until 0.6.4 two achievements shared the id "scholar" (Snail, Spark) and two "mapper" (Axolotl, and
    the Hacker cat's secret): earning one counted as both, and `jq 'map(.)'` brought the secret cat.
    The newer ones got their own ids (lesson_scholar, net_mapper). The Snail's Scholar is a rule on the
    save: it stays only if it holds (the Spark's comes back by itself). A cat already found stays."""
    earned = state.get("achievements", [])
    if "scholar" in earned and not achievements.BY_ID["scholar"].state(state):
        earned.remove("scholar")
    if "mapper" in earned and "cat" in state.get("pets", []) and "net_mapper" not in earned:
        earned.append("net_mapper")


def migrate(state, saved=None):
    """Bring an older save up to date. `saved` is the file as it was read (the state itself if not
    given): a field it lacks tells which versions it went through (the first saves had no version)."""
    saved = state if saved is None else saved
    fix_shared_ids(state)
    # The cat in the collection became the starter, and the cat starter became the star. Since then
    # the Hacker cat is a secret pet: a save that found a secret keeps it.
    if state["starter"] is None and "cat" in state["pets"]:
        state["starter"] = "star"
    if state["starter"] == "cat":
        state["starter"] = "star"
    if "cat" in state["pets"] and not achievements.secrets(state):
        state["pets"].remove("cat")
    if state["active"] == "cat" and "cat" not in state["pets"]:
        state["active"] = "starter"
    for needed, step in MIGRATIONS:
        if needed(saved):
            step(state)
    state["version"] = SAVE_VERSION
    return state


def migrate_reviews(state):
    """Fights beaten before reviews existed come back too: one a day from tomorrow, not all at once."""
    today = datetime.date.today()
    state["reviews"] = {cid: {"step": 0, "due": (today + datetime.timedelta(days=i + 1)).isoformat()}
                        for i, cid in enumerate(state["challenges"])}


def migrate_slime_ladder(state):
    """0.4.3 put the Ice slime and the Thunder slime in the Slime's ladder: a Cat or King slime stays one."""
    best = state["ladder_best"]
    best["slime"] = {6: 7, 7: 9}.get(best.get("slime"), best.get("slime", 1))


def migrate_slime(state):
    """The Slime evolved with its achievement family before it had a command ladder: keep its form."""
    fam = ("capture", "nested", "substitute", "here")      # the family it had until 0.2.3
    earned = sum(a in state.get("achievements", []) for a in fam)
    state["ladder_best"] = {"slime": len(creatures.FORMS["slime"]) if earned == len(fam) else 2 if earned >= 2 else 1}


# Before starters had long ladders (0.2.3 and older): 3 forms, at levels 4 and 7 (level max 9).
OLD_LADDERS = {"star": ("stardust", "planet", "star"), "sprout": ("seedling", "sprout", "tree"),
               "pebble": ("pebble", "golem", "crystal")}


def migrate_ladder(state):
    """Form numbers of an old save are places on the old 3-form ladder: turn them into places on the
    new one, and keep the form reached (a Planet stays a Planet until it becomes a Star)."""
    line = state.get("starter")
    state["starter_best"] = 1
    if line not in OLD_LADDERS or line not in creatures.STARTERS:
        return

    def new(old_form):
        if type(old_form) is not int:                      # already a sprite id (a hand edit): migrate_form_ids
            return old_form
        sprite = OLD_LADDERS[line][max(1, min(3, old_form)) - 1]
        return creatures.STARTERS[line].index(sprite) + 1 if sprite in creatures.STARTERS[line] else 1

    level = 1 + min(8, len(state.get("achievements", [])) // 5)
    state["starter_best"] = new((level - 1) // 3 + 1)
    if "starter" in state.get("looks", {}):
        state["looks"]["starter"] = new(state["looks"]["starter"])
    for e in state.get("evolving", []):
        if e["who"] == "starter":
            e["from"], e["to"] = new(e["from"]), new(e["to"])


def migrate_form_ids(state):
    """Version 4: a form is saved as its sprite id ("planet"), not as its place in the chain, so a form
    added to a chain no longer shifts what was saved. A pet the game doesn't have is dropped."""
    def sprite(who, n):
        if who != "starter" and who not in creatures.FAMILIES:
            return None
        forms = creatures.STARTERS[state["starter"] or "star"] if who == "starter" else creatures.forms(who)
        return forms[max(1, min(n, len(forms))) - 1] if type(n) is int else n if n in forms else None

    state["starter_best"] = sprite("starter", state["starter_best"] or 1)
    state["ladder_best"] = {pet: sprite(pet, n) for pet, n in state["ladder_best"].items() if sprite(pet, n)}
    state["looks"] = {who: sprite(who, n) for who, n in state["looks"].items() if sprite(who, n)}
    state["evolving"] = [{**e, "from": sprite(e["who"], e["from"]), "to": sprite(e["who"], e["to"])}
                         for e in state["evolving"] if sprite(e["who"], e["from"]) and sprite(e["who"], e["to"])]


def version_of(saved):
    """The version a save was written with (the first ones had none; a damaged one counts as those)."""
    version = saved.get("version", 1)
    return version if type(version) is int else 1


# (does the save need it, the step), oldest first
MIGRATIONS = [
    (lambda saved: "starter_best" not in saved, migrate_ladder),
    (lambda saved: "ladder_best" not in saved, migrate_slime),
    (lambda saved: "ladder_best" in saved and version_of(saved) < 3, migrate_slime_ladder),
    (lambda saved: "reviews" not in saved, migrate_reviews),
    (lambda saved: True, migrate_form_ids),        # version 4; also a number written by hand since
]
# Numbers in looks, starter_best, ladder_best and evolving (int in FIELDS) are forms saved before
# version 4, turned into sprite ids by migrate_form_ids.


def private(folder):
    """Bashou's folders hold what you type: yours only. Older versions made them 755; tighten those
    (only folders named bashou: a BASHOU_DATA pointing elsewhere is left as it is)."""
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    if folder.name == "bashou":
        try:
            if folder.stat().st_mode & 0o077:
                folder.chmod(0o700)
        except OSError:
            pass


def save(state):
    private(STATE.parent)
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
    private(DATA)
    with open(DATA / ".lock", "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        keep_old_format()
        state = load()
        yield state
        save(state)


i18n.saved = lambda: load().get("language")        # the language you chose (see i18n.saved)
