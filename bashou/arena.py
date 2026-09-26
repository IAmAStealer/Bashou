"""`bashou arena` (owner, 2026-09-26): come and fight when you want, instead of waiting for your pet
to announce a threat. Two choices:

- a timed fight: a fight you're ready for (the announced threat first, then a review that is due,
  then a new one), with hearts like any fight and a clock (LIMITS, by level);
- a security investigation, picked from the list, with no clock.

Lose (no hearts left, time up, or flee) and the arena closes for an hour (CLOSED_FOR). `bashou fight`
isn't affected: a threat your pet announces can always be fought.
"""

import random
import sys
import time

from . import fight, security, state
from .i18n import _

BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"
BAD = "\033[38;2;240;110;110m"
CLOSED_FOR = 3600                   # seconds
LIMITS = {1: 5, 2: 8, 3: 12}        # minutes, by fight level


def closed_for(s, now=None):
    """Seconds before the arena opens again (0: open)."""
    return max(0, int(s.get("arena_closed_until", 0) - (now or time.time())))


def pick_fight(s, rng=random):
    """The announced threat, else a review that is due, else a new fight you're ready for, else None."""
    ch = fight.pick(s)
    if ch:
        return ch
    back = fight.due(s)
    if back:
        return rng.choice(back)
    new = [c for c in fight.remaining(s) if fight.ready(s, c)]
    return rng.choice(new) if new else None


def menu(ask=input):
    """"fight", "security" or None."""
    print(f"\n  {BOLD}" + _("The arena") + f"{RESET}  {DIM}" + _("Win and it's like any fight. Lose, and the "
          "gates close for an hour.") + RESET + "\n")
    print("  1. ⚔  " + _("A timed fight: a fight you're ready for, against the clock (hearts too)."))
    print("  2. 🔍 " + _("A security investigation: you pick it from a list, and there's no clock."))
    try:
        answer = ask("\n  " + _("Your choice (1 or 2, Enter leaves): ")).strip()
    except (KeyboardInterrupt, EOFError):
        print()
        return None
    return {"1": "fight", "2": "security"}.get(answer)


def main(mode=None, which=None):
    s = state.load()
    wait = closed_for(s)
    if wait:
        print("  " + _("The arena's gates are closed after your last defeat. They open again in {n} min.").format(
            n=(wait + 59) // 60))
        print(f"  {DIM}" + _("Meanwhile, a threat your pet announces can still be fought: bashou fight") + RESET)
        return 1
    if mode is None:
        if not sys.stdin.isatty():
            print("  bashou arena fight · bashou arena security [<number>]")
            return 0
        mode = menu()
        if mode is None:
            return 0
    if mode == "security":
        if not which:
            security.listing()
            if not sys.stdin.isatty():
                return 0
            try:
                which = input("\n  " + _("Which one? (number, Enter leaves): ")).strip()
            except (KeyboardInterrupt, EOFError):
                which = ""
            if not which:
                return 0
        ch = security.choose(which)
        if not ch:
            return 1
        won = security.play(ch)
    elif mode == "fight":
        ch = pick_fight(s)
        if not ch:
            print("  " + _("No fight is ready for you right now: the ones you know are beaten and none is due "
                           "for a review. Try a security investigation: bashou arena security"))
            return 0
        won = fight.run(ch, limit=LIMITS[ch.level] * 60) == fight.WIN
    else:
        print("  " + _("Unknown choice: {mode}. Try: bashou arena fight, or bashou arena security").format(mode=mode))
        return 1
    if not won:
        with state.locked() as s:
            s["arena_closed_until"] = time.time() + CLOSED_FOR
        print(f"  {BAD}🚪 " + _("The arena closes its gates for an hour. Rest, read a lesson, and come back "
                               "stronger.") + RESET + "\n")
    return 0
