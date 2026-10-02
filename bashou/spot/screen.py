"""`bashou spot`: the screen, the keys, and what a game leaves in the save (rules and strings: __init__)."""

import os
import re
import sys
import time

from .. import progress, state, terminal
from ..i18n import _
from ..render import BOLD, DIM, ESC, RESET
from . import ARROWS, GAP, GAME_SECONDS, KINDS, TIERS, Game, tier

GOOD, BAD, GOLD = "\033[38;2;120;200;120m", "\033[38;2;230;110;100m", "\033[38;2;240;200;90m"


def center(text, cols):
    return " " * max(0, (cols - len(text)) // 2) + text


def layout(game, cols, rows):
    """Where everything goes, as (row, column, text, style), rows and columns from 1. The clock at the
    very top; the string exactly in the middle with its 4 answers around it and room to breathe
    (owner: nothing else near it, or it bothers you)."""
    left = game.left()
    bar_w = max(10, cols - 24)
    full = round(bar_w * left / GAME_SECONDS)
    mark, color = ("✔", GOOD) if game.last and game.last[0] else ("✗", BAD) if game.last else ("", "")
    parts = [(1, 2, "█" * full, ""), (1, 2 + full, "░" * (bar_w - full), DIM), (1, bar_w + 4, f"{left:4.1f} s", BOLD),
             (1, cols - 5, f"{game.score:>3}", BOLD)]
    mid, middle = rows // 2 + 1, cols // 2 + 1
    up, lft, rgt, down = (_(KINDS[k][0]) for k in game.answers)
    text = game.text
    parts += [(mid, middle - len(text) // 2, text, BOLD),
              (mid - 5, middle, mark, color),                    # right or wrong, just above the answers
              (mid - 3, middle - (len(up) + 2) // 2, f"↑ {up}", ""),
              (mid + 3, middle - (len(down) + 2) // 2, f"↓ {down}", ""),
              (mid, middle - len(text) // 2 - GAP - len(lft) - 2, f"← {lft}", ""),     # close to the string
              (mid, middle - len(text) // 2 + len(text) + GAP, f"{rgt} →", ""),
              (rows, 2, _("r: restart · q: quit"), DIM)]
    return parts


def draw(game, cols, rows):
    """One frame: the screen cleared, then each piece where `layout` puts it."""
    return f"{ESC}[H{ESC}[2J" + "".join(f"{ESC}[{r};{c}H{style}{text}{RESET if style else ''}"
                                         for r, c, text, style in layout(game, cols, rows) if text)


def save(game):
    """Keep what the game showed (best score, games, kinds recognised, best game without a mistake), and
    earn its achievements now, to show them on the end screen. Returns (best before, notes)."""
    with state.locked() as s:
        spot = s["spot"]
        before = spot["best"]
        spot["best"] = max(before, game.score)
        spot["games"] += 1
        spot["kinds"] = sorted(set(spot["kinds"]) | game.known)
        if not game.mistakes:
            spot["clean"] = max(spot["clean"], game.score)
        notes = progress.check(s)
    return before, notes


def end_screen(game, best_before, cols, rows, notes=()):
    lines = [_("Time's up!") if game.left() <= 0 else _("The bag is empty!"), "",
             f"{BOLD}{_('Score')} {game.score}{RESET}  ·  " + _("{n} mistakes").format(n=game.mistakes)]
    if game.score > best_before:
        lines.append(GOLD + _("New best score!") + RESET)
    else:
        lines.append(DIM + _("Best: {best}").format(best=best_before) + RESET)
    name = tier(game.score)
    if name:
        lines.append(GOLD + "★ " + _(name) + RESET)
    nxt = next((need for need, _name in TIERS if game.score < need), None)
    if nxt:
        lines.append(DIM + _("{n} good answers for the next star").format(n=nxt) + RESET)
    lines += [""] + [GOLD + note[:cols - 4] + RESET for note in notes[:3]]
    lines += ["", DIM + _("Enter or r: play again · q: quit") + RESET]
    top = max(0, (rows - len(lines)) // 2)
    out = [center(line, cols + (len(line) - visible_len(line))) for line in lines]
    return f"{ESC}[H{ESC}[2J" + "\n" * top + "\n".join(out)


def visible_len(text):
    return len(re.sub(r"\x1b\[[0-9;]*m", "", text))


KEYS = {"r": "restart"}


def play(screen, cols, rows):
    """One game. Returns its Game, "restart" (r: a new game at once, this one not counted) or None (q)."""
    game = Game()
    while not game.over():
        sys.stdout.write(draw(game, cols, rows))
        sys.stdout.flush()
        for key in screen.keys(0.1):
            k = terminal.name(key, KEYS)
            if k == "quit":
                return None
            if k == "restart":
                return k
            game.answer(k)
    return game


def main():
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        print("  " + _("`bashou spot` is a game for your terminal: run it there."))
        return 1
    cols, rows = os.get_terminal_size()
    with terminal.Screen() as screen:
        while True:
            game = play(screen, cols, rows)
            if game is None:
                return 0
            if game == "restart":
                continue
            before, notes = save(game)
            sys.stdout.write(end_screen(game, before, cols, rows, notes))
            sys.stdout.flush()
            time.sleep(0.6)                    # a last arrow pressed in a hurry doesn't skip the result
            screen.keys(0)
            while True:
                keys = [terminal.name(k, KEYS) for k in screen.keys(1)]
                if "quit" in keys:
                    return 0
                if "enter" in keys or "restart" in keys:
                    break
