"""Turn analyzed commands into counters, unlocked pets and notifications."""

from . import achievements, safety
from .achievements import Ctx
from .analyze import analyze
from .behavior import ACTIONS
from . import creatures
from .creatures import STARTERS
from .i18n import _

# Total commands run -> pet unlocked. The Slime then grows with your command count (its forms' "next_at").
MILESTONES = [(10, "slime")]

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
    "packet": ({"ip", "ss", "ping", "getent", "resolvectl", "tracepath", "traceroute", "mtr", "nc", "ncat",
                "tcpdump"}, 10),
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
               "leopard": ("gpg", "pass"), "packet": ("ip", "ss", "ping")}


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
    "spark": (lambda s: "kindling" in s["achievements"], "read a lesson to the end: bashou lesson"),
    "duck": (lambda s: bool({a.id for a in achievements.family("duck")} & set(s["achievements"])),
             "debug like a rubber duck: bashou learn <command>, bash -x or echo $?"),
}


def stars(state, who):
    """One star per form, filled up to the form reached: ★★☆ for a Bat, ★★★★★★★☆☆☆ for a Packet at 7/10."""
    top = reached(state, who)
    return "★" * top + "☆" * (len(chain(state, who)) - top)


def how_to_unlock(state, pet):
    """The hint of a locked pet, with where you stand."""
    if pet in STATE_PETS:
        return _(STATE_PETS[pet][1])
    if pet in CONSTRUCT_PETS:
        construct, needed = CONSTRUCT_PETS[pet]
        return f"{state['constructs'].get(construct, 0)}/{needed} × " + _(CONSTRUCT_NAMES[construct])
    for count, milestone in MILESTONES:
        if pet == milestone:
            return _("{count} commands").format(count=f"{state['commands']:,}/{count:,}")
    if pet in TOOL_PETS:
        tools, needed = TOOL_PETS[pet]
        return f"{tool_uses(state, tools)}/{needed} × {tool_label(pet)}"
    return ""


def unlock(state, pet, reason):
    if pet in state["pets"]:
        return []
    state["pets"].append(pet)
    return ["🎉 " + _("New pet: {name}! ({reason}) · bashou swap").format(
        name=sprite_of(state, pet, reached(state, pet))[1], reason=reason)]


def tool_uses(state, tools):
    return sum(state["tools"].get(t, 0) for t in tools)


ACHIEVEMENTS_PER_LEVEL = 5
MAX_LEVEL = 20


def starter_level(state):
    return 1 + min(MAX_LEVEL - 1, len(state["achievements"]) // ACHIEVEMENTS_PER_LEVEL)


def chain(state, who):
    """The sprites of a pet's forms, or of the starter's, in order (creatures.chain follows the links)."""
    return STARTERS[state["starter"] or "star"] if who_of(state, who) == "starter" else creatures.forms(who)


def met(state, who, need):
    """Is a form's "next_at" met? {"achievements": 2} also counts as met once the whole family is done."""
    kind, n = next(iter(need.items()))
    if kind == "commands":
        return state["commands"] >= n
    if kind == "level":
        return starter_level(state) >= n
    family = achievements.family(who)
    earned = sum(a.id in state["achievements"] for a in family)
    done = bool(family) and earned == len(family)
    return done if n == "all" else earned >= n or done


def counted(state, who):
    """A pet that grows with your command count: its form is compared with the one saved (`ladder_best`),
    since the count goes up before check() runs."""
    return any("commands" in creatures.PETS[s].next_at for s in chain(state, who))


def tier(state, who, form):
    """What a form can do (1-3, see behavior.ACTIONS, and the ★ shown): the form itself, or on a long
    ladder (the starter, the Slime) which third of it the form is in."""
    n = len(chain(state, who))
    return min(3, 1 + 3 * (form - 1) // n) if n > 3 else form


def who_of(state, who=None):
    """"starter" for the starter (by any of its names), else the pet id."""
    who = who or state["active"]
    return "starter" if who == "starter" or who in STARTERS else who


def reached(state, who):
    """The latest form (1 = the first): walk the chain while each form's "next_at" is met. A form once
    reached stays (`starter_best`, `ladder_best`), even when a ladder changes."""
    who = who_of(state, who)
    forms = chain(state, who)
    form = 1
    while form < len(forms) and met(state, who, creatures.PETS[forms[form - 1]].next_at):
        form += 1
    best = state.get("starter_best", 1) if who == "starter" else state.get("ladder_best", {}).get(who, 1)
    return min(len(forms), max(form, best))


def look(state, who=None):
    """The form shown: the latest, unless you picked an earlier one or haven't watched it evolve."""
    who = who_of(state, who)
    top = reached(state, who)
    return max(1, min(state.get("looks", {}).get(who, top), top))


def sprite_of(state, who, form):
    """(sprite id, name) of a pet or the starter at a form."""
    sprite = chain(state, who)[form - 1]
    return sprite, _(creatures.PETS[sprite].name)


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
    before = {pet: reached(state, pet) for pet in creatures.NAMES}
    level_before, form_before = starter_level(state), reached(state, "starter")
    earned = list(earned) + [a for a in achievements.ALL if a.state and a.state(state)]
    for a in earned:
        if a.id not in state["achievements"]:
            state["achievements"].append(a.id)
            notes.append(f"🏆 {_(a.name)}: {_(a.how)}" if a.hidden else     # a secret doesn't name its pet
                         "🏆 " + _("{name} ({pet} family): {how}").format(
                             name=_(a.name), pet=_(creatures.NAMES[a.pet]), how=_(a.how)))
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
        now = state["starter_best"] = reached(state, "starter")
        if now > form_before:
            notes.append(evolve(state, "starter", form_before, now))
        else:
            name = sprite_of(state, "starter", now)[1]
            notes.append("⬆ " + _("{name} reached level {level}!").format(name=name, level=starter_level(state)))
    for pet in creatures.NAMES:
        if counted(state, pet):                             # its count went up before check(): compare
            before[pet] = state.setdefault("ladder_best", {}).get(pet, 1)   # with the form it had
            state["ladder_best"][pet] = reached(state, pet)
    for pet in creatures.NAMES:
        now = reached(state, pet)
        if now > before[pet] and pet in state["pets"]:
            notes.append(evolve(state, pet, before[pet], now))
    return notes


def next_milestone(state):
    """(commands, what comes): the Slime, then its next form (a surprise)."""
    for count, pet in MILESTONES:
        if state["commands"] < count:
            return count, sprite_of(state, pet, 1)[1]
        for sprite in chain(state, pet):
            need = creatures.PETS[sprite].next_at.get("commands")
            if need and state["commands"] < need:
                return need, "?"
    return None
