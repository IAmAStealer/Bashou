"""Turn analyzed commands into counters, unlocked pets and notifications."""

import re

from . import achievements, safety
from . import which
from .achievements import Ctx
from .analyze import analyze
from .behavior import ACTIONS
from . import creatures
from .creatures import STARTERS
from .i18n import _

CONSTRUCT_NAMES = {"pipe3": "3-command pipes", "risky": "risky commands", "script": "scripts of your own run"}


def tool_label(pet):
    """How the unlock hint names a tool pet's tools ("label" in its file, or the first in alphabetical
    order). Only the installed ones are named: no `dig` in the hint when dig is missing."""
    rule = creatures.FAMILIES[pet].unlock
    names = rule.get("label") or [min(rule["tools"])]
    return "/".join([n for n in names if which.installed(n)] or names[:1])


def counter(state, path):
    """A number in the save, by its path: "fights_won", "adventure.walked"."""
    value = state
    for key in path.split("."):
        value = (value or {}).get(key, 0) if isinstance(value, dict) else 0
    return value or 0


def unlock_rule(state, pet):
    """(met, reason, hint) of a pet's "unlock" rule: whether it comes now, what the 🎉 line says, and what
    the board shows while it's locked (with where you stand)."""
    rule = creatures.FAMILIES[pet].unlock
    if "tools" in rule:
        now, n = tool_uses(state, rule["tools"]), rule["uses"]
        return now >= n, f"{n} × {tool_label(pet)}", f"{now}/{n} × {tool_label(pet)}"
    if "construct" in rule:
        now, n, what = state["constructs"].get(rule["construct"], 0), rule["count"], _(CONSTRUCT_NAMES[rule["construct"]])
        return now >= n, f"{n} × " + what, f"{now}/{n} × " + what
    if "commands" in rule:
        n = rule["commands"]
        return (state["commands"] >= n, _("{count} commands").format(count=f"{n:,}"),
                _("{count} commands").format(count=f"{state['commands']:,}/{n:,}"))
    if "counter" in rule:
        met = counter(state, rule["counter"]) >= rule["count"]
    elif "achievement" in rule:
        met = rule["achievement"] in state["achievements"]
    elif "pony" in rule:                                   # claimed with `bashou pony <id>` (pony.py)
        met = pet in state["ponies"]
    elif "family_achievement" in rule:
        met = bool({a.id for a in achievements.family(pet)} & set(state["achievements"]))
    else:                                                  # "secret_found": one of its secrets finds you
        met = any(a.pet == pet for a in achievements.secrets(state))
    return met, _(rule["how"]), _(rule["how"])


def stars(state, who):
    """One star per form, filled up to the form reached: ★★☆ for a Bat, ★★★★★★★☆☆☆ for a Packet at 7/10."""
    top = reached(state, who)
    return "★" * top + "☆" * (len(chain(state, who)) - top)


def how_to_unlock(state, pet):
    """The hint of a locked pet, with where you stand."""
    return unlock_rule(state, pet)[2]


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


def form_of(state, who, sprite):
    """The place (1 = the first) of a saved form (a sprite id) in the chain, or None when the game no
    longer has it there. The save holds ids: a form added to a chain shifts no saved number."""
    forms = chain(state, who)
    return forms.index(sprite) + 1 if isinstance(sprite, str) and sprite in forms else None


def best(state, who):
    """The highest form reached so far, kept in the save (`starter_best`, `ladder_best`)."""
    who = who_of(state, who)
    saved = state.get("starter_best") if who == "starter" else state.get("ladder_best", {}).get(who)
    return form_of(state, who, saved) or 1


def keep_best(state, who, form):
    sprite = chain(state, who)[form - 1]
    if who_of(state, who) == "starter":
        state["starter_best"] = sprite
    else:
        state.setdefault("ladder_best", {})[who] = sprite


def reached(state, who):
    """The latest form (1 = the first): walk the chain while each form's "next_at" is met. A form once
    reached stays (`best`), even when a ladder changes."""
    who = who_of(state, who)
    forms = chain(state, who)
    form = 1
    while form < len(forms) and met(state, who, creatures.PETS[forms[form - 1]].next_at):
        form += 1
    return min(len(forms), max(form, best(state, who)))


def look(state, who=None):
    """The form shown: the latest, unless you picked an earlier one or haven't watched it evolve."""
    who = who_of(state, who)
    top = reached(state, who)
    return min(form_of(state, who, state.get("looks", {}).get(who)) or top, top)


def set_look(state, who, form):
    """Show this form (`f` in `bashou swap`); the latest one is the default and isn't saved."""
    who = who_of(state, who)
    if form == reached(state, who):
        state.get("looks", {}).pop(who, None)
    else:
        state.setdefault("looks", {})[who] = chain(state, who)[form - 1]


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
    forms = chain(state, who)
    state.setdefault("looks", {}).setdefault(who, forms[old - 1])
    queue = state.setdefault("evolving", [])
    for e in queue:
        if e["who"] == who:
            e["to"] = forms[new - 1]
            break
    else:
        queue.append({"who": who, "from": forms[old - 1], "to": forms[new - 1]})
    return "✨ " + _("{old} is evolving! Watch it: `bashou evolve`").format(old=sprite_of(state, who, old)[1])


def evolution(state, e):
    """A waiting evolution with form numbers: {"who", "from", "to"}."""
    to = form_of(state, e["who"], e["to"]) or reached(state, e["who"])
    return {"who": e["who"], "from": min(to, form_of(state, e["who"], e["from"]) or 1), "to": to}


def watched(state, who):
    """After the animation: show the new form."""
    state["evolving"] = [e for e in state.get("evolving", []) if e["who"] != who]
    state.get("looks", {}).pop(who, None)


def runs_a_script(analysis, line):
    """`./backup.sh`, `bash deploy.sh`, `sh x.sh`: running a script of your own."""
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
    for pet in creatures.NAMES:
        met, reason, _hint = unlock_rule(state, pet)
        if met:
            notes += unlock(state, pet, reason)
    if state["starter"] and starter_level(state) > level_before:
        now = reached(state, "starter")
        keep_best(state, "starter", now)
        if now > form_before:
            notes.append(evolve(state, "starter", form_before, now))
        else:
            name = sprite_of(state, "starter", now)[1]
            notes.append("⬆ " + _("{name} reached level {level}!").format(name=name, level=starter_level(state)))
    for pet in creatures.NAMES:
        if counted(state, pet):                             # its count went up before check(): compare
            before[pet] = best(state, pet)                  # with the form it had
            keep_best(state, pet, reached(state, pet))
    for pet in creatures.NAMES:
        now = reached(state, pet)
        if now > before[pet] and pet in state["pets"]:
            notes.append(evolve(state, pet, before[pet], now))
    return notes


def next_milestone(state):
    """(commands, what comes): the pet your command count brings (the Slime), then its next form (a surprise)."""
    for pet in creatures.NAMES:
        count = creatures.FAMILIES[pet].unlock.get("commands")
        if not count:
            continue
        if state["commands"] < count:
            return count, sprite_of(state, pet, 1)[1]
        for sprite in chain(state, pet):
            need = creatures.PETS[sprite].next_at.get("commands")
            if need and state["commands"] < need:
                return need, "?"
    return None
