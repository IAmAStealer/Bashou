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
}


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


def current(state, who=None):
    """(sprite id, action stage, display name, voice id) of the active pet, or of `who`."""
    who = who or state["active"]
    if who == "starter" or who in STARTERS:
        line = state["starter"] or "cat"
        form = starter_form(state)
        sprite = STARTERS[line][form - 1]
        return sprite, form, _(FORM_NAMES[sprite]), line
    st = stage(state, who)
    return creatures.form(who, st), st, _(STAGES[who][st - 1]), who


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
            notes += unlock(state, pet, f"{needed} × {min(tools)}")
    if state["starter"] and starter_level(state) > level_before:
        line = STARTERS[state["starter"]]
        old, new = _(FORM_NAMES[line[form_before - 1]]), _(FORM_NAMES[line[starter_form(state) - 1]])
        if starter_form(state) > form_before:
            notes.append("✨ " + _("{old} evolved into {new}! New: {actions}").format(
                old=old, new=new, actions=_(ACTIONS[starter_form(state)])))
        else:
            notes.append("⬆ " + _("{name} reached level {level}!").format(name=new, level=starter_level(state)))
    for pet in STAGES:
        now = stage(state, pet)
        if now > before[pet] and pet in state["pets"]:
            notes.append("✨ " + _("{old} evolved into {new}! New: {actions}").format(
                old=_(STAGES[pet][before[pet] - 1]), new=_(STAGES[pet][now - 1]), actions=_(ACTIONS[now])))
    return notes


def next_milestone(state):
    for count, pet in MILESTONES:
        if state["commands"] < count:
            return count, pet
    return None
