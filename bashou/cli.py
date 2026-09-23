"""`bashou` command line."""

import argparse

from . import achievements, creatures, progress, state
from .creatures import STAGES, owned, roster
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
            (_("Pets"), f"{len(owned(s))}/{len(roster(s))}")]
    nxt = progress.next_milestone(s)
    if nxt:
        count, what = nxt
        rows.append((_("Next"), f"{progress_bar(s['commands'], count)} {s['commands']:,}/{count:,} → {what}"))
    width = max(len(label) for label, value in rows)
    for label, value in rows:
        print(f"  {BOLD}{label:<{width}}{RESET} : {value}")
    if s["update_available"]:
        print(f"\n  🆕 {DIM}" + _("Bashou {version} is out: bashou update").format(version=s["update_available"]) + RESET)


def hint(s, pet):
    return progress.how_to_unlock(s, pet)


def stars(s, pet):
    return progress.stars(s, pet)


def pets():
    s = state.load()
    active = " ← " + _("active") if s["active"] == "starter" else ""
    print(f"  {BOLD}{_('Starter')}{RESET} {starter_line(s)}{DIM}{active}{RESET}\n")
    for pet, rule in roster(s):
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
        n=f"{len(achievements.earned(s))}/{len(achievements.usable())}"))
    print(f"  {DIM}" + _("Every {n} achievements also level up your starter.").format(
        n=progress.ACHIEVEMENTS_PER_LEVEL) + f"{RESET}\n")
    found = achievements.secrets(s)
    if found:
        print(f"  {BOLD}" + _("Secrets") + f"{RESET} {DIM}{len(found)}/{len(achievements.SECRET)}{RESET}")
        for a in found:
            print(f"    🐾 {_(a.name)} {DIM}· {_(a.how)}{RESET}")
        print()
    for pet, rule in roster(s):
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
    print(f"  {BOLD}{labels[2]:<{w}}{RESET}{len(owned(s))}/{len(roster(s))}   "
          f"{BOLD}{_('Achievements')}{RESET} {len(achievements.earned(s))}/{len(achievements.usable())}   "
          f"{BOLD}{_('Fights won')}{RESET} {s['fights_won']}   "
          f"{BOLD}{_('Security')}{RESET} {len(s['security'])}")
    adv = s.get("adventure")
    if adv and "chapter" in adv:
        print(f"  {BOLD}{_('Adventure')}{RESET}    " + _("chapter {n} · {m} m · {b} bosses · {c} chests").format(
            n=adv["chapter"], m=int(adv["walked"]), b=len(adv.get("bosses", [])), c=len(adv.get("trials", []))))
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
            s["pets"] = [pet for pet, _ in roster(s)] + sorted(creatures.SECRET)
            print(f"  All {len(s['pets'])} pets unlocked.")
        elif args.action == "stage":
            fam = [a.id for a in achievements.family(args.pet)]
            keep = fam[:{1: 0, 2: 2, 3: len(fam)}[args.stage]]
            s["achievements"] = [a for a in s["achievements"] if a not in fam] + keep
            if args.pet not in s["pets"]:
                s["pets"].append(args.pet)
            print(f"  {STAGES[args.pet][args.stage - 1]} (stage {args.stage}).")
            if args.stage > 1:                                   # as if you'd just earned it: bashou evolve
                s["evolving"] = [e for e in s.get("evolving", []) if e["who"] != args.pet]
                s.get("looks", {}).pop(args.pet, None)
                print("  " + progress.evolve(s, args.pet, args.stage - 1, args.stage))
        elif args.action == "stage-all":
            for pet, rule in roster(s):
                fam = [a.id for a in achievements.family(pet)]
                keep = fam[:{1: 0, 2: 2, 3: len(fam)}[args.stage]]
                s["achievements"] = [a for a in s["achievements"] if a not in fam] + keep
            print(f"  Every pet at stage {args.stage}.")
        elif args.action == "level":
            n = max(1, min(progress.MAX_LEVEL, int(args.pet or 1)))
            form_before = progress.starter_form(s)
            s["achievements"] = [a.id for a in achievements.ALL][:(n - 1) * progress.ACHIEVEMENTS_PER_LEVEL]
            s["starter_best"] = 1
            s["starter_best"] = progress.starter_form(s)
            s.get("looks", {}).pop("starter", None)
            s["evolving"] = [e for e in s.get("evolving", []) if e["who"] != "starter"]
            print(f"  Starter at level {n}: {progress.current(s, 'starter')[2]}.")
            if progress.starter_form(s) > form_before:
                print("  " + progress.evolve(s, "starter", form_before, progress.starter_form(s)))
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
    ln = sub.add_parser("learn", help="take the last suggested command (or yours) apart, piece by piece")
    ln.add_argument("command", nargs=argparse.REMAINDER)
    ex = sub.add_parser("explain", help="a short note on a code topic, e.g. bashou explain python list")
    ex.add_argument("topic", nargs="*")
    sub.add_parser("evolve", help="watch your pets evolve")
    sw = sub.add_parser("swap", help="change your active pet")
    sw.add_argument("pet", nargs="?")
    sub.add_parser("stats", help="your terminal stats: commands, tools, streaks")
    dv = sub.add_parser("dev", help="testing helpers (back up state first)")
    dv.add_argument("action", choices=["unlock-all", "stage", "stage-all", "level", "threat", "restore"])
    dv.add_argument("pet", nargs="?", help="pet (stage), level 1-9 (level) or challenge id (threat)")
    dv.add_argument("stage", nargs="?", type=int, choices=[1, 2, 3], default=3)
    sub.add_parser("start", help="choose your starter (once)")
    sub.add_parser("language", help="choose the language")
    sub.add_parser("setup", help="load Bashou from your ~/.bashrc (after installing the package)")
    sub.add_parser("version", help="which version of Bashou this is")
    up = sub.add_parser("update", help="get the new version from GitHub")
    up.add_argument("--version", help="install this release instead, even an older one (e.g. v0.2.0)")
    sub.add_parser("adventure", help="walk into the world with your starter")
    sc = sub.add_parser("security", help="security challenges, easy to hard")
    sc.add_argument("which", nargs="?", help="number or id (see the list)")
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
    elif args.cmd == "evolve":
        from . import evolve
        return evolve.main()
    elif args.cmd == "learn":
        from . import learn
        raise SystemExit(learn.main(args.command))
    elif args.cmd == "explain":
        from . import explain
        raise SystemExit(explain.main(args.topic))
    elif args.cmd == "talk":
        from . import dialogue, learn
        s = state.load()
        name, voice = progress.current(s)[2:]
        said = dialogue.line(s, voice)
        learn.remember(said)
        print(f"  {BOLD}{name}{RESET}: {said}")
        if "`" in said:
            print(f"  {DIM}" + _("Not sure what it does? `bashou learn` takes it apart.") + RESET)
    elif args.cmd == "adventure":
        from . import adventure
        raise SystemExit(adventure.main())
    elif args.cmd == "security":
        from . import security
        raise SystemExit(security.run(args.which))
    elif args.cmd == "version":
        from . import update
        print("  Bashou " + (update.version() or _("(unknown version: not a git clone)")))
        newer = state.load()["update_available"]
        if newer:
            print("  🆕 " + _("Bashou {version} is out: bashou update").format(version=newer))
    elif args.cmd == "update":
        from . import update
        raise SystemExit(update.run(args.version))
    elif args.cmd == "setup":
        from . import setup
        raise SystemExit(setup.run())
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
