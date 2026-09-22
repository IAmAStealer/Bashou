"""Turn analyzed commands into counters, unlocked pets and notifications."""

from . import achievements, safety
from .achievements import Ctx
from .analyze import analyze
from .behavior import ACTIONS
from . import creatures
from .creatures import FORM_NAMES, STAGES, STARTERS
from .i18n import _

# Total commands run -> pet unlocked.
MILESTONES = [(10, "bat"), (50, "frog"), (200, "turtle"), (500, "mushroom"), (1000, "slime"),
              (2500, "sofa"), (5000, "octopus"), (10000, "dragon")]

# Pet -> (tools that count, successful uses needed).
TOOL_PETS = {
    "fox": ({"find"}, 10),
    "owl": ({"awk", "gawk", "mawk"}, 10),
    "mole": ({"grep", "egrep", "fgrep", "rg"}, 10),
    "snake": ({"sed"}, 10),
    "ghost": ({"ps", "pgrep", "pkill", "kill", "killall"}, 10),
    "spider": ({"strace"}, 3),
    "ant": ({"xargs"}, 10),
    "axolotl": ({"jq"}, 10),
    "beaver": ({"git"}, 10),
    "squirrel": ({"tar", "gzip", "gunzip", "zip", "unzip", "xz", "zstd"}, 10),
    "pigeon": ({"curl", "wget", "ssh", "scp", "rsync", "dig", "host", "nslookup"}, 10),
    "hedgehog": ({"chmod", "chown", "chgrp", "umask"}, 10),
    "bee": ({"systemctl", "journalctl"}, 10),
    "whale": ({"kubectl"}, 10),
    "meerkat": ({"top", "htop", "btop", "free", "df", "du", "watch", "vmstat"}, 10),
}
# How the unlock hint names a tool pet's tools (default: the first in alphabetical order).
# Only the installed ones are named: no `dig` in the hint when dig is missing.
TOOL_LABELS = {"ghost": ("ps", "kill"), "squirrel": ("tar", "gzip"), "pigeon": ("curl", "ssh", "dig"),
               "hedgehog": ("chmod", "chown"), "bee": ("systemctl",), "meerkat": ("df", "du", "top")}


def tool_label(pet):
    from .which import installed
    names = TOOL_LABELS.get(pet) or (min(TOOL_PETS[pet][0]),)
    return "/".join([n for n in names if installed(n)] or names[:1])


# pet: (construct, lines needed); "pipe3" = a line chaining 3+ commands with |
CONSTRUCT_PETS = {"octopus": ("pipe3", 10), "gremlin": ("risky", 5)}
CONSTRUCT_NAMES = {"pipe3": "3-command pipes", "risky": "risky commands"}


def adventure(state):
    return state.get("adventure") or {}


# pet: (rule on the state, how to get it)
STATE_PETS = {"snail": (lambda s: adventure(s).get("chapters_done", 0) >= 1, "finish chapter 1 of bashou adventure")}


def unlock(state, pet, reason):
    if pet in state["pets"]:
        return []
    state["pets"].append(pet)
    return ["🎉 " + _("New pet: {name}! ({reason}) · bashou swap").format(
        name=_(STAGES[pet][stage(state, pet) - 1]), reason=reason)]


def tool_uses(state, tools):
    return sum(state["tools"].get(t, 0) for t in tools)


def stage(state, pet):
    """1, 2 or 3 depending on the achievements earned in the pet's family."""
    earned = sum(a.id in state["achievements"] for a in achievements.family(pet))
    total = len(achievements.family(pet))
    return 3 if total and earned == total else 2 if earned >= 2 else 1


ACHIEVEMENTS_PER_LEVEL = 5
MAX_LEVEL = 9


def starter_level(state):
    return 1 + min(MAX_LEVEL - 1, len(state["achievements"]) // ACHIEVEMENTS_PER_LEVEL)


def starter_form(state):
    """1, 2 or 3: the starter changes shape at levels 4 and 7."""
    return (starter_level(state) - 1) // 3 + 1


def who_of(state, who=None):
    """"starter" for the starter (by any of its names), else the pet id."""
    who = who or state["active"]
    return "starter" if who == "starter" or who in STARTERS else who


def reached(state, who):
    """The latest form (1-3): it gives the actions."""
    return starter_form(state) if who_of(state, who) == "starter" else stage(state, who)


def look(state, who=None):
    """The form shown (1-3): the latest, unless you picked an earlier one or haven't watched it evolve."""
    who = who_of(state, who)
    top = reached(state, who)
    return max(1, min(state.get("looks", {}).get(who, top), top))


def sprite_of(state, who, form):
    """(sprite id, name) of a pet or the starter at a form."""
    if who_of(state, who) == "starter":
        sprite = STARTERS[state["starter"] or "star"][form - 1]
        return sprite, _(FORM_NAMES[sprite])
    return creatures.form(who, form), _(STAGES[who][form - 1])


def current(state, who=None):
    """(sprite id, action stage, display name, voice id) of the active pet, or of `who`.
    The sprite and name follow the form shown (`look`), the actions the latest form."""
    who = who_of(state, who)
    sprite, name = sprite_of(state, who, look(state, who))
    return sprite, reached(state, who), name, (state["starter"] or "star") if who == "starter" else who


def evolve(state, who, old, new):
    """Queue an evolution for `bashou evolve`; until then the pet keeps its old look."""
    state.setdefault("looks", {}).setdefault(who, old)
    queue = state.setdefault("evolving", [])
    for e in queue:
        if e["who"] == who:
            e["to"] = new
            break
    else:
        queue.append({"who": who, "from": old, "to": new})
    return "✨ " + _("{old} is evolving! Watch it: `bashou evolve`").format(old=sprite_of(state, who, old)[1])


def watched(state, who):
    """After the animation: show the new form."""
    state["evolving"] = [e for e in state.get("evolving", []) if e["who"] != who]
    state.get("looks", {}).pop(who, None)


def record(state, status, line, today, hour):
    """Count one command. Returns the notifications to show."""
    analysis = analyze(line)
    state["commands"] += 1
    if today not in state["days"]:
        state["days"].append(today)
    if state["today"]["date"] != today:
        state["today"] = {"date": today, "count": 0}
    state["today"]["count"] += 1
    if safety.risk(line):                   # counted even when it failed: it was risky anyway
        state["constructs"]["risky"] = state["constructs"].get("risky", 0) + 1
    earned = []
    if status == 0:
        ctx = Ctx(analysis, line, hour)
        earned = [a for a in achievements.ALL if a.cmd and a.cmd(ctx)]
        for tool in analysis.tools:
            state["tools"][tool] = state["tools"].get(tool, 0) + 1
        for construct in analysis.constructs:
            state["constructs"][construct] = state["constructs"].get(construct, 0) + 1
        if analysis.pipes >= 3:
            state["constructs"]["pipe3"] = state["constructs"].get("pipe3", 0) + 1
    return check(state, earned)


def check(state, earned=()):
    """Unlock pets and achievements that are now due. Returns the notifications."""
    notes = []
    before = {pet: stage(state, pet) for pet in STAGES}
    level_before, form_before = starter_level(state), starter_form(state)
    earned = list(earned) + [a for a in achievements.ALL if a.state and a.state(state)]
    for a in earned:
        if a.id not in state["achievements"]:
            state["achievements"].append(a.id)
            notes.append(f"🏆 {_(a.name)}: {_(a.how)}")
    for count, pet in MILESTONES:
        if state["commands"] >= count:
            notes += unlock(state, pet, _("{count} commands").format(count=f"{count:,}"))
    for pet, (construct, needed) in CONSTRUCT_PETS.items():
        if state["constructs"].get(construct, 0) >= needed:
            notes += unlock(state, pet, f"{needed} × " + _(CONSTRUCT_NAMES[construct]))
    for pet, (rule, how) in STATE_PETS.items():
        if rule(state):
            notes += unlock(state, pet, _(how))
    for pet, (tools, needed) in TOOL_PETS.items():
        if tool_uses(state, tools) >= needed:
            notes += unlock(state, pet, f"{needed} × {tool_label(pet)}")
    if state["starter"] and starter_level(state) > level_before:
        line = STARTERS[state["starter"]]
        if starter_form(state) > form_before:
            notes.append(evolve(state, "starter", form_before, starter_form(state)))
        else:
            name = _(FORM_NAMES[line[starter_form(state) - 1]])
            notes.append("⬆ " + _("{name} reached level {level}!").format(name=name, level=starter_level(state)))
    for pet in STAGES:
        now = stage(state, pet)
        if now > before[pet] and pet in state["pets"]:
            notes.append(evolve(state, pet, before[pet], now))
    return notes


def next_milestone(state):
    for count, pet in MILESTONES:
        if state["commands"] < count:
            return count, pet
    return None
