"""`bashou` command line."""

import argparse

from . import achievements, breathe, progress, state
from .creatures import NAMES, ROSTER, STAGES

BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"


def progress_bar(done, total, width=20):
    filled = min(width, done * width // total) if total else width
    return "█" * filled + "░" * (width - filled)


def level():
    s = state.load()
    print(f"  {BOLD}Commands{RESET}: {s['commands']:,}")
    print(f"  {BOLD}Pets{RESET}    : {len(s['pets'])}/{len(ROSTER)}")
    nxt = progress.next_milestone(s)
    if nxt:
        count, pet = nxt
        print(f"  {BOLD}Next{RESET}    : {progress_bar(s['commands'], count)} "
              f"{s['commands']:,}/{count:,} → {NAMES[pet]}")


def hint(s, pet):
    for count, p in progress.MILESTONES:
        if p == pet:
            return f"{count:,} commands"
    if pet in progress.TOOL_PETS:
        tools, needed = progress.TOOL_PETS[pet]
        return f"{progress.tool_uses(s, tools)}/{needed} × {min(tools)}"
    return ""


def stars(s, pet):
    return "★" * progress.stage(s, pet) + "☆" * (3 - progress.stage(s, pet))


def pets():
    s = state.load()
    for pet, _ in ROSTER:
        if pet in s["pets"]:
            active = " ← active" if pet == s["active"] else ""
            name = STAGES[pet][progress.stage(s, pet) - 1]
            print(f"  {stars(s, pet)} {name}{DIM}{active}{RESET}")
        else:
            print(f"  {DIM}☆☆☆ ???  ({hint(s, pet)}){RESET}")


def achievements_list():
    s = state.load()
    earned = set(s["achievements"])
    print(f"  {len(earned)}/{len(achievements.ALL)} achievements · 2 evolve a pet, all of its family make it legendary\n")
    for pet, _ in ROSTER:
        fam = achievements.family(pet)
        got = sum(a.id in earned for a in fam)
        title = STAGES[pet][progress.stage(s, pet) - 1] if pet in s["pets"] else "???"
        print(f"  {BOLD}{title}{RESET} {DIM}{got}/{len(fam)}{RESET}")
        for a in fam:
            if a.id in earned:
                print(f"    🏆 {a.name} {DIM}· {a.how}{RESET}")
            else:
                print(f"    {DIM}·  {a.name} · {a.how}{RESET}")


def swap(pet):
    s = state.load()
    if not pet:
        from . import board
        board.main()
        return
    pet = pet.lower()
    if pet not in s["pets"]:
        print(f"  {pet}: not unlocked yet.")
        return
    with state.locked() as s:
        s["active"] = pet
    print(f"  {STAGES[pet][progress.stage(s, pet) - 1]} is now your pet.")


def main():
    parser = argparse.ArgumentParser(prog="bashou", description="A pet that grows as you learn bash.")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("level", help="commands run and next unlock")
    sub.add_parser("pets", help="your collection")
    sub.add_parser("achievements", help="what you earned and what to try next")
    sub.add_parser("fight", help="enter the arena")
    sw = sub.add_parser("swap", help="change your active pet")
    sw.add_argument("pet", nargs="?")
    br = sub.add_parser("breathe", help="guided breathing")
    br.add_argument("pattern", nargs="?", default="box", choices=list(breathe.PATTERNS))
    br.add_argument("-n", "--cycles", type=int, default=4)
    sub.add_parser("stats", help="breathing stats")
    sub.add_parser("on", help="show the pet (shell function)")
    sub.add_parser("off", help="hide the pet (shell function)")
    args = parser.parse_args()

    if args.cmd == "pets":
        pets()
    elif args.cmd == "achievements":
        achievements_list()
    elif args.cmd == "fight":
        from . import fight
        fight.run()
    elif args.cmd == "swap":
        swap(args.pet)
    elif args.cmd == "breathe":
        breathe.breathe(args.pattern, args.cycles)
    elif args.cmd == "stats":
        breathe.stats()
    else:
        level()
