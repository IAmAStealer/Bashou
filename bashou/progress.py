"""Turn analyzed commands into counters, unlocked pets and notifications."""

from . import achievements, safety
from .achievements import Ctx
from .analyze import analyze
from .behavior import ACTIONS
from . import creatures
from .creatures import FORM_NAMES, STAGES, STARTER_LEVELS, STARTERS
from .i18n import _

# Total commands run -> pet unlocked.
# The Slime grows with your command count: one form per count, as many as creatures.FORMS gives it
# (round animals and elements join as they get drawn, the King slime stays last; see doc/PLAN.md).
COMMAND_LADDER = {"slime": (10, 100, 200, 500, 1500, 5000, 10000)}
MILESTONES = [(COMMAND_LADDER["slime"][0], "slime")]

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
    "leopard": ({"gpg", "gpg2", "gpgv", "pass"}, 5),                    # keeps secrets
    "bat": ({"python", "python3", "cargo", "rustc", "gcc", "g++", "clang", "make", "cmake", "node", "npm",
             "go", "javac", "java", "ruby", "perl", "php"}, 10),              # a night coder
}
# How the unlock hint names a tool pet's tools (default: the first in alphabetical order).
# Only the installed ones are named: no `dig` in the hint when dig is missing.
TOOL_LABELS = {"bat": ("python3", "cargo", "gcc", "make", "node"), "ghost": ("ps", "kill"), "squirrel": ("tar", "gzip"), "pigeon": ("curl", "ssh", "dig"),
               "hedgehog": ("chmod", "chown"), "bee": ("systemctl",), "meerkat": ("df", "du", "top"),
               "leopard": ("gpg", "pass")}


def tool_label(pet):
    from .which import installed
    names = TOOL_LABELS.get(pet) or (min(TOOL_PETS[pet][0]),)
    return "/".join([n for n in names if installed(n)] or names[:1])


# pet: (construct, lines needed); "pipe3" = a line chaining 3+ commands with |
CONSTRUCT_PETS = {"octopus": ("pipe3", 10), "gremlin": ("risky", 5), "mushroom": ("script", 5)}
CONSTRUCT_NAMES = {"pipe3": "3-command pipes", "risky": "risky commands", "script": "scripts of your own run"}


def adventure(state):
    return state.get("adventure") or {}


# pet: (rule on the state, how to get it)
STATE_PETS = {
    "snail": (lambda s: adventure(s).get("chapters_done", 0) >= 1, "finish chapter 1 of bashou adventure"),
    "turtle": (lambda s: adventure(s).get("walked", 0) >= 500, "walk 500 m in bashou adventure"),
    "frog": (lambda s: adventure(s).get("correct", 0) >= 20, "answer 20 questions right in bashou adventure"),
    "sofa": (lambda s: s.get("fights_lost", 0) >= 1, "lose (or flee) a fight: take a seat"),
    "dragon": (lambda s: s["fights_won"] >= 1, "win a fight: bashou fight"),
    "cat": (lambda s: bool(achievements.secrets(s)), "???"),          # a secret finds you
    "duck": (lambda s: bool({a.id for a in achievements.family("duck")} & set(s["achievements"])),
             "debug like a rubber duck: bashou learn <command>, bash -x or echo $?"),
}


def stars(state, pet):
    """★ of a pet: how far along its forms it is (a pet with one form has one star)."""
    forms = len(creatures.FORMS.get(pet, ("",) * 3))
    return "★" * tier(state, pet, stage(state, pet)) + "☆" * (min(3, forms) - tier(state, pet, stage(state, pet)))


def how_to_unlock(state, pet):
    """The hint of a locked pet, with where you stand."""
    if pet in STATE_PETS:
        return _(STATE_PETS[pet][1])
    if pet in CONSTRUCT_PETS:
        construct, needed = CONSTRUCT_PETS[pet]
        return f"{state['constructs'].get(construct, 0)}/{needed} × " + _(CONSTRUCT_NAMES[construct])
    if pet in COMMAND_LADDER:
        return _("{count} commands").format(count=f"{state['commands']:,}/{COMMAND_LADDER[pet][0]:,}")
    if pet in TOOL_PETS:
        tools, needed = TOOL_PETS[pet]
        return f"{tool_uses(state, tools)}/{needed} × {tool_label(pet)}"
    return ""


def unlock(state, pet, reason):
    if pet in state["pets"]:
        return []
    state["pets"].append(pet)
    return ["🎉 " + _("New pet: {name}! ({reason}) · bashou swap").format(
        name=_(STAGES[pet][stage(state, pet) - 1]), reason=reason)]


def tool_uses(state, tools):
    return sum(state["tools"].get(t, 0) for t in tools)


def stage(state, pet):
    """1, 2 or 3 depending on the achievements earned in the pet's family; the Slime by your command
    count. A form once reached stays (`ladder_best`). A family with more forms (the Duck) takes a new
    one with each achievement, and its last when the family is complete."""
    if pet in COMMAND_LADDER:
        by_count = sum(1 for n in COMMAND_LADDER[pet] if state["commands"] >= n)
        return max(1, by_count, state.get("ladder_best", {}).get(pet, 1))
    earned = sum(a.id in state["achievements"] for a in achievements.family(pet))
    total = len(achievements.family(pet))
    forms = len(creatures.FORMS.get(pet, ("",) * 3))
    if forms > 3:
        return forms if total and earned == total else min(forms - 1, max(1, earned))
    return min(forms, 3 if total and earned == total else 2 if earned >= 2 else 1)


ACHIEVEMENTS_PER_LEVEL = 5
MAX_LEVEL = 20


def starter_level(state):
    return 1 + min(MAX_LEVEL - 1, len(state["achievements"]) // ACHIEVEMENTS_PER_LEVEL)


def ladder(state):
    """The starter's forms, in order, and the level each one comes at."""
    line = state["starter"] or "star"
    return STARTERS[line], STARTER_LEVELS[line]


def starter_form(state):
    """The starter's form (1 = the first): the last one its level reached. Never goes back: a form once
    reached stays (`starter_best`), even when the ladder changes."""
    forms, levels = ladder(state)
    by_level = sum(1 for lvl in levels if lvl <= starter_level(state))
    return min(len(forms), max(by_level, state.get("starter_best", 1)))


def tier(state, who, form):
    """What a form can do (1-3, see behavior.ACTIONS, and the ★ shown): the form itself, or on a long
    ladder (the starter, the Slime) which third of it the form is in."""
    who = who_of(state, who)
    n = len(ladder(state)[0]) if who == "starter" else len(creatures.FORMS.get(who, ()))
    return min(3, 1 + 3 * (form - 1) // n) if n > 3 else form


def who_of(state, who=None):
    """"starter" for the starter (by any of its names), else the pet id."""
    who = who or state["active"]
    return "starter" if who == "starter" or who in STARTERS else who


def reached(state, who):
    """The latest form (a pet: 1-3; the starter: its place on the ladder)."""
    return starter_form(state) if who_of(state, who) == "starter" else stage(state, who)


def look(state, who=None):
    """The form shown: the latest, unless you picked an earlier one or haven't watched it evolve."""
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
    """(sprite id, action tier, display name, voice id) of the active pet, or of `who`.
    The sprite and name follow the form shown (`look`), the actions the latest form."""
    who = who_of(state, who)
    sprite, name = sprite_of(state, who, look(state, who))
    return (sprite, tier(state, who, reached(state, who)), name,
            (state["starter"] or "star") if who == "starter" else who)


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


def runs_a_script(analysis, line):
    """`./backup.sh`, `bash deploy.sh`, `sh x.sh`: running a script of your own."""
    import re
    if any(t.endswith(".sh") for t in analysis.tools):
        return True
    return bool(analysis.tools & {"bash", "sh", "zsh"}) and bool(re.search(r"\b(ba|z)?sh\s+\S+\.sh\b", line))


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
        if runs_a_script(analysis, line):
            state["constructs"]["script"] = state["constructs"].get("script", 0) + 1
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
        state["starter_best"] = starter_form(state)
        if starter_form(state) > form_before:
            notes.append(evolve(state, "starter", form_before, starter_form(state)))
        else:
            name = _(FORM_NAMES[line[starter_form(state) - 1]])
            notes.append("⬆ " + _("{name} reached level {level}!").format(name=name, level=starter_level(state)))
    for pet in COMMAND_LADDER:                              # its count went up before check(): compare
        before[pet] = state.setdefault("ladder_best", {}).get(pet, 1)   # with the form it had
        state["ladder_best"][pet] = stage(state, pet)
    for pet in STAGES:
        now = stage(state, pet)
        if now > before[pet] and pet in state["pets"]:
            notes.append(evolve(state, pet, before[pet], now))
    return notes


def next_milestone(state):
    """(commands, what comes): the Slime, then its next form (a surprise)."""
    for pet, counts in COMMAND_LADDER.items():
        for i, count in enumerate(counts):
            if state["commands"] < count:
                return count, _(STAGES[pet][0]) if i == 0 else "?"
    return None
