"""`bashou` command line."""

import argparse

from . import achievements, creatures, progress, state
from .creatures import owned, roster
from .i18n import _

BOLD, DIM, RESET, CYAN = "\033[1m", "\033[2m", "\033[0m", "\033[38;2;120;200;230m"


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
    from . import lesson
    new = lesson.new(s, lesson.load())
    if new:
        rows.append((_("Lessons"), _("🦉 new: {title} · bashou lesson").format(title=new[0]["title"])))
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
            name = progress.sprite_of(s, pet, progress.reached(s, pet))[1]
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
        title = progress.sprite_of(s, pet, progress.reached(s, pet))[1] if pet in s["pets"] else "???"
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


def ask_settings(ask=input):
    """`bashou config` in a terminal: one question per setting (Enter keeps it), saved together at the end.
    Then your skills and the language, which have their own screens. Ctrl+C leaves without saving."""
    from . import update
    s = state.load()
    print(f"  {BOLD}" + _("Configure Bashou") + f"{RESET}  {DIM}" +
          _("Enter keeps the value in [brackets], `default` resets it, Ctrl+C leaves without saving.") + RESET)
    answers = {}
    try:
        for key, (default, text) in state.SETTINGS.items():
            if key == "updates" and update.packaged():
                continue                                 # apt or dnf update it
            print(f"\n  {_(text)}")
            while True:
                value = ask(f"  {key} [{state.show(state.setting(s, key))}]: ").strip()
                if not value:
                    break
                try:
                    answers[key] = None if value == "default" else state.parse(key, value)
                    break
                except ValueError:
                    print("  " + _("Not a valid value for {name}: {value}").format(name=key, value=value))
        current = s.get("skills", "all")
        change = ask("\n  " + _("Change what you learn? (y/N) ")).strip().lower()
        language = ask("  " + _("Change the language? (y/N) ")).strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\n  " + _("Nothing changed."))
        return 1
    with state.locked() as s:
        for key, new in answers.items():
            s.setdefault("settings", {}).pop(key, None)
            if new is not None:
                s["settings"][key] = new
    if change in ("y", "yes", "o", "oui"):
        from . import skills
        skills.show(skills.ask(current))
    if language in ("y", "yes", "o", "oui"):
        from . import starter
        starter.language_main()
    print("  " + _("Saved. Every terminal uses it right away."))
    return 0


def language(value):
    """`bashou config language`: the screen; `bashou config language fr`: straight away."""
    from . import i18n, starter
    if value is None:
        return starter.language_main()
    if value not in i18n.LANGUAGES:
        print("  " + _("Not a valid value for {name}: {value}").format(name="language", value=value)
              + f" ({', '.join(i18n.LANGUAGES)})")
        return 1
    with state.locked() as s:
        s["language"] = value
    i18n.use(value)
    print("  " + _("Language: {name}").format(name=i18n.LANGUAGES[value]))
    return 0


def config(name, value):
    """`bashou config`: questions (or the list, outside a terminal); `bashou config list`;
    `bashou config NAME VALUE` sets one ("default" resets it). Language and skills, once commands of
    their own, live here too: `bashou config language [fr]`, `bashou config skills`."""
    import sys
    if not name and sys.stdin.isatty():
        return ask_settings()
    if not name or name == "list":
        from . import i18n, skills
        s = state.load()
        for key, (default, text) in state.SETTINGS.items():
            print(f"  {BOLD}{key}{RESET} {state.show(state.setting(s, key))}  "
                  f"{DIM}{_(text)} · " + _("default") + f" {state.show(default)}{RESET}")
        chosen = s.get("skills", "all")
        print(f"  {BOLD}language{RESET} {s.get('language') or 'en'}  {DIM}"
              + _("the language Bashou speaks: bashou config language [{codes}]").format(
                  codes="|".join(i18n.LANGUAGES)) + RESET)
        print(f"  {BOLD}skills{RESET} {chosen if chosen == 'all' else ','.join(chosen)}  {DIM}"
              + _("what you want to learn: bashou config skills") + RESET)
        return 0
    if name == "language":
        return language(value)
    if name == "skills":
        from . import skills
        if value is not None:
            print("  " + _("Skills are picked on a screen: bashou config skills"))
            return 1
        return skills.main()
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
            print(f"  {creatures.names(args.pet)[args.stage - 1]} (stage {args.stage}).")
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
            form_before = progress.reached(s, "starter")
            s["achievements"] = [a.id for a in achievements.ALL][:(n - 1) * progress.ACHIEVEMENTS_PER_LEVEL]
            s["starter_best"] = 1
            s["starter_best"] = progress.reached(s, "starter")
            s.get("looks", {}).pop("starter", None)
            s["evolving"] = [e for e in s.get("evolving", []) if e["who"] != "starter"]
            print(f"  Starter at level {n}: {progress.current(s, 'starter')[2]}.")
            if s["starter_best"] > form_before:
                print("  " + progress.evolve(s, "starter", form_before, s["starter_best"]))
        elif args.action == "threat":
            ch = challenges.BY_ID.get(args.pet) or challenges.ALL[0]
            s["threat"] = {"challenge": ch.id, "until": time.time() + 600}
            print(f"  A {ch.threat} is waiting: bashou fight")


# `bashou help`: the commands by what they're for, one per line. Every visible command is here
# (tests/test_completion.py checks it against the parser and the Tab completion).
HELP = [
    ("Your pet", [
        ("bashou", "your starter's level and what comes next"),
        ("bashou pets", "your collection"),
        ("bashou achievements", "what you earned, and what to try next"),
        ("bashou evolve", "watch your pets evolve"),
        ("bashou swap [pet]", "change your active pet"),
        ("bashou stats", "your terminal stats: commands, tools, streaks"),
        ("bashou share", "a QR code: your phone turns your progress into an image to share"),
    ]),
    ("Learn", [
        ("bashou lesson [name]", "the Sage Owl's library: lessons with drawings, unlocked as you play"),
        ("bashou learn <command>", "take a command apart, piece by piece (alone: your pet's last tip)"),
        ("bashou talk", "your pet gives you a tip now, with a command to try"),
    ]),
    ("Play", [
        ("bashou fight", "fight the threat your pet announced"),
        ("bashou arena", "fight when you want: a timed fight, or a security investigation"),
        ("bashou adventure", "walk into the world with your starter"),
    ]),
    ("Settings", [
        ("bashou on / off", "show or hide the pet (the first `on` adds Bashou to ~/.bashrc)"),
        ("bashou config", "settings, language and skills (bashou config list shows them)"),
        ("bashou start", "choose your starter (once)"),
        ("bashou reset", "start over with a new starter"),
        ("bashou update", "get the new version"),
        ("bashou version", "which version of Bashou this is"),
    ]),
]


def print_help():
    width = max(len(cmd) for _s, rows in HELP for cmd, _t in rows)
    print(f"\n  {BOLD}Bashou{RESET} · " + _("a pet that grows as you learn bash.") + "\n")
    for section, rows in HELP:
        print(f"  {BOLD}{_(section)}{RESET}")
        for cmd, text in rows:
            print(f"    {CYAN}{cmd:<{width}}{RESET}  {_(text)}")
        print()


class Parser(argparse.ArgumentParser):
    def print_help(self, file=None):
        if self.prog == "bashou":
            print_help()
        else:
            super().print_help(file)


def main():
    parser = Parser(prog="bashou", usage="bashou COMMAND  (bashou help lists them)")
    # Commands without help= are hidden: old names that still work, and dev. HELP lists the others.
    sub = parser.add_subparsers(dest="cmd", metavar="COMMAND", prog="bashou")
    sub.add_parser("help", help="this list")
    sub.add_parser("level", help="your starter's level")
    sub.add_parser("pets", help="your collection")
    sub.add_parser("achievements", help="what you earned")
    sub.add_parser("fight", help="the announced threat")
    sub.add_parser("talk", help="a tip now")
    ln = sub.add_parser("learn", help="take a command apart")
    ln.add_argument("command", nargs=argparse.REMAINDER)
    ls = sub.add_parser("lesson", help="the Sage Owl's library")
    ls.add_argument("which", nargs="?", help="a lesson to open, or list")
    sub.add_parser("evolve", help="watch your pets evolve")
    sw = sub.add_parser("swap", help="change your active pet")
    sw.add_argument("pet", nargs="?")
    sub.add_parser("stats", help="your terminal stats")
    sh = sub.add_parser("share", help="a QR code of your progress")
    sh.add_argument("--name", help="the nickname on the image: 1-12 letters, digits, - or _ (asked the first time)")
    dv = sub.add_parser("dev")                                          # testing helpers, hidden from players
    dv.add_argument("action", choices=["unlock-all", "stage", "stage-all", "level", "threat", "restore"])
    dv.add_argument("pet", nargs="?", help="pet (stage), level 1-9 (level) or challenge id (threat)")
    dv.add_argument("stage", nargs="?", type=int, choices=[1, 2, 3], default=3)
    sub.add_parser("start", help="choose your starter")
    sub.add_parser("language")                                          # now bashou config language
    sub.add_parser("skills")                                            # now bashou config skills
    sub.add_parser("setup")                                             # now bashou on
    sub.add_parser("version", help="which version")
    up = sub.add_parser("update", help="get the new version")
    up.add_argument("--version", help="install this release instead, even an older one (e.g. v0.2.0)")
    up.add_argument("--packages", action="store_true", help="move to Bashou's apt or dnf repository (shows every command first)")
    sub.add_parser("adventure", help="walk into the world")
    ar = sub.add_parser("arena", help="fight when you want")
    ar.add_argument("mode", nargs="?", help="fight or security")
    ar.add_argument("which", nargs="?", help="security: number or id (see the list)")
    sc = sub.add_parser("security")                                     # now bashou arena security
    sc.add_argument("which", nargs="?")
    cf = sub.add_parser("config", help="settings, language, skills")
    cf.add_argument("name", nargs="?")
    cf.add_argument("value", nargs="?")
    sub.add_parser("reset", help="start over")
    sub.add_parser("on", help="show the pet")
    sub.add_parser("off", help="hide the pet")
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
    elif args.cmd == "talk":
        from . import dialogue, learn
        s = state.load()
        name, voice = progress.current(s)[2:]
        said = dialogue.line(s, voice)
        learn.remember(said)
        print(f"  {BOLD}{name}{RESET}: {said}")
        if "`" in said:
            print(f"  {DIM}" + _("Not sure what it does? `bashou learn` takes it apart.") + RESET)
    elif args.cmd == "lesson":
        from . import lesson
        raise SystemExit(lesson.main([args.which] if args.which else []))
    elif args.cmd == "adventure":
        from . import adventure
        raise SystemExit(adventure.main())
    elif args.cmd in ("arena", "security"):
        from . import arena
        raise SystemExit(arena.main(*(("security", args.which) if args.cmd == "security" else (args.mode, args.which))))
    elif args.cmd == "help":
        print_help()
    elif args.cmd == "version":
        from . import update
        print("  Bashou " + (update.version() or _("(unknown version: not a git clone)")))
        newer = state.load()["update_available"]
        if newer:
            print("  🆕 " + _("Bashou {version} is out: bashou update").format(version=newer))
    elif args.cmd == "update":
        from . import update
        raise SystemExit(update.run(args.version, args.packages))
    elif args.cmd == "skills":
        raise SystemExit(config("skills", None))
    elif args.cmd in ("setup", "on"):       # `on` reaches Python only when bashou.bash isn't loaded yet
        from . import setup
        raise SystemExit(setup.run())
    elif args.cmd == "off":
        print("  " + _("Bashou isn't running in this terminal."))
    elif args.cmd == "config":
        raise SystemExit(config(args.name, args.value))
    elif args.cmd == "language":
        raise SystemExit(config("language", None))
    elif args.cmd == "fight":
        from . import fight
        fight.run()
    elif args.cmd == "swap":
        swap(args.pet)
    elif args.cmd == "stats":
        stats()
    elif args.cmd == "share":
        from . import share
        raise SystemExit(share.main(args))
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
