"""`bashou` command line."""

import argparse

from . import achievements, progress, state
from .creatures import FORM_NAMES, NAMES, ROSTER, STAGES, STARTERS

BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"


def progress_bar(done, total, width=20):
    filled = min(width, done * width // total) if total else width
    return "█" * filled + "░" * (width - filled)


def starter_line(s):
    """"Cat · level 5 ███░ 2/5 achievements to level 6" for the chosen starter."""
    if not s["starter"]:
        return f"{DIM}no starter yet: bashou start{RESET}"
    lvl, per = progress.starter_level(s), progress.ACHIEVEMENTS_PER_LEVEL
    name = progress.current(s, "starter")[2]
    if lvl == progress.MAX_LEVEL:
        return f"{name} · level {lvl} (max)"
    done = len(s["achievements"]) % per
    return f"{name} · level {lvl} {progress_bar(done, per, 10)} {done}/{per} achievements to level {lvl + 1}"


def level():
    s = state.load()
    print(f"  {BOLD}Starter{RESET} : {starter_line(s)}")
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
    active = " ← active" if s["active"] == "starter" else ""
    print(f"  {BOLD}Starter{RESET} {starter_line(s)}{DIM}{active}{RESET}\n")
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
    print(f"  {len(earned)}/{len(achievements.ALL)} achievements · 2 evolve a pet, all of its family make it legendary")
    print(f"  {DIM}Every {progress.ACHIEVEMENTS_PER_LEVEL} achievements also level up your starter.{RESET}\n")
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
    if pet in ("starter", s["starter"]):
        pet = "starter"
    elif pet not in s["pets"]:
        print(f"  {pet}: not unlocked yet.")
        return
    with state.locked() as s:
        s["active"] = pet
    print(f"  {progress.current(s)[2]} is now your pet.")


def plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


def stats():
    s = state.load()
    days = s["days"]
    print(f"  {BOLD}Commands{RESET}     {s['commands']:,}  {DIM}({s['today']['count']} today){RESET}")
    print(f"  {BOLD}Active days{RESET}  {len(days)}  {DIM}(streak: {plural(achievements.streak(days), 'day')}){RESET}")
    print(f"  {BOLD}Pets{RESET}         {len(s['pets'])}/{len(ROSTER)}   "
          f"{BOLD}Achievements{RESET} {len(s['achievements'])}/{len(achievements.ALL)}   "
          f"{BOLD}Fights won{RESET} {s['fights_won']}")
    top = sorted(s["tools"].items(), key=lambda kv: -kv[1])[:8]
    if top:
        width = max(len(t) for t, _ in top)
        most = top[0][1]
        print(f"\n  {BOLD}Top tools{RESET}")
        for tool, n in top:
            print(f"    {tool:<{width}} {progress_bar(n, most, 16)} {n:,}")
    names = {"pipe3": "3+ stage pipes", "subst": "$( ) captures", "procsub": "<( ) substitutions",
             "loop": "loops", "heredoc": "heredocs", "stderr": "2>&1 merges", "tee": "tee"}
    used = [(names.get(k, k), v) for k, v in sorted(s["constructs"].items(), key=lambda kv: -kv[1])]
    if used:
        print(f"\n  {BOLD}Constructs{RESET}   " + "  ".join(f"{name} {DIM}{n}{RESET}" for name, n in used))


def backup():
    import shutil
    import time
    if state.STATE.exists():
        path = state.DATA / f"state.json.bak-{time.strftime('%Y%m%d-%H%M%S')}-{time.time_ns() % 1000:03d}"
        shutil.copy(state.STATE, path)
        print(f"  {DIM}backup: {path}{RESET}")


def reset():
    """Start over: new starter, empty collection. Asks first, keeps a backup."""
    import sys
    from . import starter
    print(f"  {BOLD}Reset Bashou?{RESET} Your starter, pets, achievements and counters start over.")
    try:
        answer = input("  Type `reset` to confirm: ")
    except EOFError:
        answer = ""
    if answer.strip() != "reset":
        print("  Nothing changed.")
        return 1
    backup()
    with state.locked() as s:
        s.clear()
        s.update(state.default())
    return starter.main() if sys.stdin.isatty() else 0


def dev(args):
    """Testing helpers. Every change first backs up state.json next to it."""
    import shutil
    import time
    from . import challenges

    if args.action == "restore":
        backups = sorted(state.DATA.glob("state.json.bak-*"))
        if not backups:
            print("  No backup.")
            return
        shutil.copy(backups[-1], state.STATE)
        print(f"  Restored {backups[-1].name}")
        return
    backup()
    with state.locked() as s:
        if args.action == "unlock-all":
            s["pets"] = [pet for pet, _ in ROSTER]
            print("  All 16 pets unlocked.")
        elif args.action == "stage":
            fam = [a.id for a in achievements.family(args.pet)]
            keep = fam[:{1: 0, 2: 2, 3: len(fam)}[args.stage]]
            s["achievements"] = [a for a in s["achievements"] if a not in fam] + keep
            if args.pet not in s["pets"]:
                s["pets"].append(args.pet)
            print(f"  {STAGES[args.pet][args.stage - 1]} (stage {args.stage}).")
        elif args.action == "stage-all":
            for pet, _ in ROSTER:
                fam = [a.id for a in achievements.family(pet)]
                keep = fam[:{1: 0, 2: 2, 3: len(fam)}[args.stage]]
                s["achievements"] = [a for a in s["achievements"] if a not in fam] + keep
            print(f"  Every pet at stage {args.stage}.")
        elif args.action == "level":
            n = max(1, min(progress.MAX_LEVEL, int(args.pet or 1)))
            s["achievements"] = [a.id for a in achievements.ALL][:(n - 1) * progress.ACHIEVEMENTS_PER_LEVEL]
            print(f"  Starter at level {n}: {progress.current(s, 'starter')[2]}.")
        elif args.action == "threat":
            ch = challenges.BY_ID.get(args.pet) or challenges.ALL[0]
            s["threat"] = {"challenge": ch.id, "until": time.time() + 600}
            print(f"  A {ch.threat} is waiting: bashou fight")


def main():
    parser = argparse.ArgumentParser(prog="bashou", description="A pet that grows as you learn bash.")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("level", help="commands run and next unlock")
    sub.add_parser("pets", help="your collection")
    sub.add_parser("achievements", help="what you earned and what to try next")
    sub.add_parser("fight", help="enter the arena")
    sub.add_parser("talk", help="your pet says something useful")
    sw = sub.add_parser("swap", help="change your active pet")
    sw.add_argument("pet", nargs="?")
    sub.add_parser("stats", help="your terminal stats: commands, tools, streaks")
    dv = sub.add_parser("dev", help="testing helpers (back up state first)")
    dv.add_argument("action", choices=["unlock-all", "stage", "stage-all", "level", "threat", "restore"])
    dv.add_argument("pet", nargs="?", help="pet (stage), level 1-9 (level) or challenge id (threat)")
    dv.add_argument("stage", nargs="?", type=int, choices=[1, 2, 3], default=3)
    sub.add_parser("start", help="choose your starter (once)")
    sub.add_parser("reset", help="start over with a new starter")
    sub.add_parser("on", help="show the pet (shell function)")
    sub.add_parser("off", help="hide the pet (shell function)")
    args = parser.parse_args()

    if args.cmd == "pets":
        pets()
    elif args.cmd == "achievements":
        achievements_list()
    elif args.cmd == "talk":
        from . import dialogue
        s = state.load()
        _, _, name, voice = progress.current(s)
        print(f"  {BOLD}{name}{RESET}: {dialogue.line(s, voice)}")
    elif args.cmd == "fight":
        from . import fight
        fight.run()
    elif args.cmd == "swap":
        swap(args.pet)
    elif args.cmd == "stats":
        stats()
    elif args.cmd == "start":
        from . import starter
        raise SystemExit(starter.main())
    elif args.cmd == "reset":
        raise SystemExit(reset())
    elif args.cmd == "dev":
        if args.action == "stage-all" and args.pet:
            args.stage = int(args.pet)
        dev(args)
    else:
        level()
