"""Turn analyzed commands into counters, unlocked pets and notifications."""

from . import achievements
from .achievements import Ctx
from .analyze import analyze
from .behavior import ACTIONS
from .creatures import STAGES

# Total commands run -> pet unlocked.
MILESTONES = [(50, "frog"), (200, "turtle"), (500, "mushroom"), (1000, "slime"),
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


def unlock(state, pet, reason):
    if pet in state["pets"]:
        return []
    state["pets"].append(pet)
    return [f"🎉 New pet: {STAGES[pet][stage(state, pet) - 1]}! ({reason}) · bashou swap"]


def tool_uses(state, tools):
    return sum(state["tools"].get(t, 0) for t in tools)


def stage(state, pet):
    """1, 2 or 3 depending on the achievements earned in the pet's family."""
    earned = sum(a.id in state["achievements"] for a in achievements.family(pet))
    total = len(achievements.family(pet))
    return 3 if total and earned == total else 2 if earned >= 2 else 1


def record(state, status, line, today, hour):
    """Count one command. Returns the notifications to show."""
    analysis = analyze(line)
    state["commands"] += 1
    if today not in state["days"]:
        state["days"].append(today)
    if state["today"]["date"] != today:
        state["today"] = {"date": today, "count": 0}
    state["today"]["count"] += 1
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
    earned = list(earned) + [a for a in achievements.ALL if a.state and a.state(state)]
    for a in earned:
        if a.id not in state["achievements"]:
            state["achievements"].append(a.id)
            notes.append(f"🏆 {a.name}: {a.how}")
    for count, pet in MILESTONES:
        if state["commands"] >= count:
            notes += unlock(state, pet, f"{count:,} commands")
    for pet, (tools, needed) in TOOL_PETS.items():
        if tool_uses(state, tools) >= needed:
            notes += unlock(state, pet, f"{needed} × {min(tools)}")
    for pet in STAGES:
        now = stage(state, pet)
        if now > before[pet] and pet in state["pets"]:
            notes.append(f"✨ {STAGES[pet][before[pet] - 1]} evolved into {STAGES[pet][now - 1]}! "
                         f"New: {ACTIONS[now]}")
    return notes


def next_milestone(state):
    for count, pet in MILESTONES:
        if state["commands"] < count:
            return count, pet
    return None
