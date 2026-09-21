"""`bashou` command line."""

import argparse

from . import achievements, progress, state
from .creatures import NAMES, ROSTER, STAGES
from .i18n import _

BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"


def progress_bar(done, total, width=20):
    filled = min(width, done * width // total) if total else width
    return "█" * filled + "░" * (width - filled)


def starter_line(s):
    """"Cat · level 5 ███░ 2/5 achievements to level 6" for the chosen starter."""
    if not s["starter"]:
        return DIM + _("no starter yet: bashou start") + RESET
    lvl, per = progress.starter_level(s), progress.ACHIEVEMENTS_PER_LEVEL
    name = progress.current(s, "starter")[2]
    if lvl == progress.MAX_LEVEL:
        return _("{name} · level {level} (max)").format(name=name, level=lvl)
    done = len(s["achievements"]) % per
    return _("{name} · level {level} {bar} {done}/{per} achievements to level {next}").format(
        name=name, level=lvl, bar=progress_bar(done, per, 10), done=done, per=per, next=lvl + 1)


def level():
    s = state.load()
    rows = [(_("Starter"), starter_line(s)), (_("Commands"), f"{s['commands']:,}"),
            (_("Pets"), f"{len(s['pets'])}/{len(ROSTER)}")]
    nxt = progress.next_milestone(s)
    if nxt:
        count, pet = nxt
        rows.append((_("Next"), f"{progress_bar(s['commands'], count)} {s['commands']:,}/{count:,} → {_(NAMES[pet])}"))
    width = max(len(label) for label, value in rows)
    for label, value in rows:
        print(f"  {BOLD}{label:<{width}}{RESET} : {value}")
    if s["update_available"]:
        print(f"\n  🆕 {DIM}" + _("Bashou {version} is out: bashou update").format(version=s["update_available"]) + RESET)


def hint(s, pet):
    if pet in progress.CONSTRUCT_PETS:
        construct, needed = progress.CONSTRUCT_PETS[pet]
        return f"{s['constructs'].get(construct, 0)}/{needed} × " + _(progress.CONSTRUCT_NAMES[construct])
    for count, p in progress.MILESTONES:
        if p == pet:
            return _("{count} commands").format(count=f"{count:,}")
    if pet in progress.TOOL_PETS:
        tools, needed = progress.TOOL_PETS[pet]
        return f"{progress.tool_uses(s, tools)}/{needed} × {min(tools)}"
    return ""


def stars(s, pet):
    return "★" * progress.stage(s, pet) + "☆" * (3 - progress.stage(s, pet))


def pets():
    s = state.load()
    active = " ← " + _("active") if s["active"] == "starter" else ""
    print(f"  {BOLD}{_('Starter')}{RESET} {starter_line(s)}{DIM}{active}{RESET}\n")
    for pet, rule in ROSTER:
        if pet in s["pets"]:
            active = " ← " + _("active") if pet == s["active"] else ""
            name = _(STAGES[pet][progress.stage(s, pet) - 1])
            print(f"  {stars(s, pet)} {name}{DIM}{active}{RESET}")
        else:
            print(f"  {DIM}☆☆☆ ???  ({hint(s, pet)}){RESET}")


def achievements_list():
    s = state.load()
    earned = set(s["achievements"])
    print("  " + _("{n} achievements · 2 evolve a pet, all of its family make it legendary").format(
        n=f"{len(earned)}/{len(achievements.ALL)}"))
    print(f"  {DIM}" + _("Every {n} achievements also level up your starter.").format(
        n=progress.ACHIEVEMENTS_PER_LEVEL) + f"{RESET}\n")
    for pet, rule in ROSTER:
        fam = achievements.family(pet)
        got = sum(a.id in earned for a in fam)
        title = _(STAGES[pet][progress.stage(s, pet) - 1]) if pet in s["pets"] else "???"
        print(f"  {BOLD}{title}{RESET} {DIM}{got}/{len(fam)}{RESET}")
        for a in fam:
            if a.id in earned:
                print(f"    🏆 {_(a.name)} {DIM}· {_(a.how)}{RESET}")
            else:
                print(f"    {DIM}·  {_(a.name)} · {_(a.how)}{RESET}")


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
        print("  " + _("{pet}: not unlocked yet.").format(pet=pet))
        return
    with state.locked() as s:
        s["active"] = pet
    print("  " + _("{name} is now your pet.").format(name=progress.current(s)[2]))


def stats():
    s = state.load()
    days = s["days"]
    labels = [_("Commands"), _("Active days"), _("Pets")]
    w = max(map(len, labels)) + 2
    print(f"  {BOLD}{labels[0]:<{w}}{RESET}{s['commands']:,}  {DIM}("
          + _("{n} today").format(n=s["today"]["count"]) + f"){RESET}")
    print(f"  {BOLD}{labels[1]:<{w}}{RESET}{len(days)}  {DIM}("
          + _("streak: {n} day(s)").format(n=achievements.streak(days)) + f"){RESET}")
    print(f"  {BOLD}{labels[2]:<{w}}{RESET}{len(s['pets'])}/{len(ROSTER)}   "
          f"{BOLD}{_('Achievements')}{RESET} {len(s['achievements'])}/{len(achievements.ALL)}   "
          f"{BOLD}{_('Fights won')}{RESET} {s['fights_won']}")
    top = sorted(s["tools"].items(), key=lambda kv: -kv[1])[:8]
    if top:
        width = max(len(t) for t, _ in top)
        most = top[0][1]
        print(f"\n  {BOLD}{_('Top tools')}{RESET}")
        for tool, n in top:
            print(f"    {tool:<{width}} {progress_bar(n, most, 16)} {n:,}")
    names = {"pipe3": _("3+ stage pipes"), "subst": _("$( ) captures"), "procsub": _("<( ) substitutions"),
             "loop": _("loops"), "heredoc": _("heredocs"), "stderr": _("2>&1 merges"), "tee": "tee",
             "risky": _("risky commands")}
    used = [(names.get(k, k), v) for k, v in sorted(s["constructs"].items(), key=lambda kv: -kv[1])]
    if used:
        print(f"\n  {BOLD}{_('Constructs')}{RESET}   " + "  ".join(f"{name} {DIM}{n}{RESET}" for name, n in used))


def config(name, value):
    """`bashou config`: list settings; `bashou config NAME VALUE` sets one ("default" resets it)."""
    if not name:
        s = state.load()
        for key, (default, text) in state.SETTINGS.items():
            print(f"  {BOLD}{key}{RESET} {state.show(state.setting(s, key))}  "
                  f"{DIM}{_(text)} · " + _("default") + f" {state.show(default)}{RESET}")
        return 0
    if name not in state.SETTINGS:
        print("  " + _("Unknown setting: {name}").format(name=name))
        return 1
    if value is None:
        print(f"  {name} {state.show(state.setting(state.load(), name))}")
        return 0
    try:
        new = None if value == "default" else state.parse(name, value)
    except ValueError:
        print("  " + _("Not a valid value for {name}: {value}").format(name=name, value=value))
        return 1
    with state.locked() as s:
        s.setdefault("settings", {}).pop(name, None)
        if new is not None:
            s["settings"][name] = new
        shown = state.show(state.setting(s, name))
    print(f"  {name} {shown}")
    return 0


def backup():
    import shutil
    import time
    if state.STATE.exists():
        path = state.DATA / f"state.json.bak-{time.strftime('%Y%m%d-%H%M%S')}-{time.time_ns() % 1000:03d}"
        shutil.copy(state.STATE, path)
        print(f"  {DIM}" + _("backup: {path}").format(path=path) + RESET)


def reset():
    """Start over: new starter, empty collection. Asks first, keeps a backup."""
    import sys
    from . import starter
    print(f"  {BOLD}{_('Reset Bashou?')}{RESET} " + _("Your starter, pets, achievements and counters start over."))
    try:
        answer = input("  " + _("Type `reset` to confirm: "))
    except EOFError:
        answer = ""
    if answer.strip() != "reset":
        print("  " + _("Nothing changed."))
        return 1
    backup()
    with state.locked() as s:
        s.clear()
        language = s.get("language")
        s.update(state.default(), language=language)     # keep the language
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
            print(f"  All {len(ROSTER)} pets unlocked.")
        elif args.action == "stage":
            fam = [a.id for a in achievements.family(args.pet)]
            keep = fam[:{1: 0, 2: 2, 3: len(fam)}[args.stage]]
            s["achievements"] = [a for a in s["achievements"] if a not in fam] + keep
            if args.pet not in s["pets"]:
                s["pets"].append(args.pet)
            print(f"  {STAGES[args.pet][args.stage - 1]} (stage {args.stage}).")
        elif args.action == "stage-all":
            for pet, rule in ROSTER:
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
    sub.add_parser("language", help="choose the language")
    sub.add_parser("update", help="get the new version from GitHub")
    cf = sub.add_parser("config", help="settings, e.g. bashou config bubble 5-10")
    cf.add_argument("name", nargs="?")
    cf.add_argument("value", nargs="?")
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
        name, voice = progress.current(s)[2:]
        print(f"  {BOLD}{name}{RESET}: {dialogue.line(s, voice)}")
    elif args.cmd == "update":
        from . import update
        raise SystemExit(update.run())
    elif args.cmd == "config":
        raise SystemExit(config(args.name, args.value))
    elif args.cmd == "language":
        from . import starter
        raise SystemExit(starter.language_main())
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
