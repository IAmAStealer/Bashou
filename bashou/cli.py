"""`bashou` command line."""

import argparse
import os
import sys

from . import achievements, creatures, progress, state
from .creatures import owned, roster
from .i18n import _
from .render import BOLD, DIM, RESET

CYAN = "\033[38;2;120;200;230m"


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
        bar = progress_bar(s["commands"], count, 20 if os.get_terminal_size(1).columns >= 60 else 10) \
            if sys.stdout.isatty() else progress_bar(s["commands"], count)             # narrow: a short bar
        rows.append((_("Next"), f"{bar} {s['commands']:,}/{count:,} → {what}"))
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
        for key, setting in state.SETTINGS.items():
            if key == "updates" and update.packaged():
                continue                                 # apt or dnf update it
            print(f"\n  {_(setting.help)}")
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
        from . import starter
        starter.show_skills(starter.ask_skills(current))
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
    if not name and sys.stdin.isatty():
        return ask_settings()
    if not name or name == "list":
        from . import i18n, skills
        s = state.load()
        for key, setting in state.SETTINGS.items():
            print(f"  {BOLD}{key}{RESET} {state.show(state.setting(s, key))}  "
                  f"{DIM}{_(setting.help)} · " + _("default") + f" {state.show(setting.default)}{RESET}")
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
        from . import starter
        if value is not None:
            print("  " + _("Skills are picked on a screen: bashou config skills"))
            return 1
        return starter.skills_main()
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


def at_form(s, pet, form):
    """Earn the pet's achievements, in order, until it reaches `form` (or runs out). Returns the form."""
    family = [a.id for a in achievements.family(pet)]
    s["achievements"] = [a for a in s["achievements"] if a not in family]
    for a in family:
        if progress.reached(s, pet) >= form:
            break
        s["achievements"].append(a)
    return progress.reached(s, pet)


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
            s["pets"] = [pet for pet, _ in roster(s)] + sorted(p for p in creatures.NAMES if creatures.FAMILIES[p].secret)
            print(f"  All {len(s['pets'])} pets unlocked.")
        elif args.action == "stage":
            form = at_form(s, args.pet, args.stage)
            if args.pet not in s["pets"]:
                s["pets"].append(args.pet)
            print(f"  {creatures.names(args.pet)[form - 1]} (stage {form}).")
            if form > 1:                                         # as if you'd just earned it: bashou evolve
                s["evolving"] = [e for e in s.get("evolving", []) if e["who"] != args.pet]
                s.get("looks", {}).pop(args.pet, None)
                print("  " + progress.evolve(s, args.pet, form - 1, form))
        elif args.action == "stage-all":
            for pet, rule in roster(s):
                at_form(s, pet, args.stage)
            print(f"  Every pet at stage {args.stage}.")
        elif args.action == "level":
            n = max(1, min(progress.MAX_LEVEL, int(args.pet or 1)))
            form_before = progress.reached(s, "starter")
            s["achievements"] = [a.id for a in achievements.ALL][:(n - 1) * progress.ACHIEVEMENTS_PER_LEVEL]
            s["starter_best"] = None
            now = progress.reached(s, "starter")
            progress.keep_best(s, "starter", now)
            s.get("looks", {}).pop("starter", None)
            s["evolving"] = [e for e in s.get("evolving", []) if e["who"] != "starter"]
            print(f"  Starter at level {n}: {progress.current(s, 'starter')[2]}.")
            if now > form_before:
                print("  " + progress.evolve(s, "starter", form_before, now))
        elif args.action == "threat":
            ch = challenges.BY_ID.get(args.pet) or challenges.ALL[0]
            s["threat"] = {"challenge": ch.id, "until": time.time() + 600}
            print(f"  A {ch.threat} is waiting: bashou fight")


def talk(_args):
    from . import dialogue, learn
    s = state.load()
    name, voice = progress.current(s)[2:]
    said = dialogue.line(s, voice)
    learn.remember(said)
    print(f"  {BOLD}{name}{RESET}: {said}")
    if "`" in said:
        print(f"  {DIM}" + _("Not sure what it does? `bashou learn` takes it apart.") + RESET)


def version(_args):
    from . import update
    print("  Bashou " + (update.version() or _("(unknown version: not a git clone)")))
    newer = state.load()["update_available"]
    if newer:
        print("  🆕 " + _("Bashou {version} is out: bashou update").format(version=newer))


def run_dev(args):
    if args.action == "stage-all" and args.pet:
        args.stage = int(args.pet)
    dev(args)


def run(module, function="main", *arguments):
    """A command living in its own module, imported only when it runs (`bashou` starts fast)."""
    def go(args):
        import importlib
        return getattr(importlib.import_module(f".{module}", __package__), function)(
            *(getattr(args, a) if isinstance(a, str) else a(args) for a in arguments))
    return go


class Command:
    """A `bashou` command: what runs, its arguments, and its line in `bashou help` (`row`: how it's
    written, what it's for, under which title). No row: it still works and completes (`help`, `off`),
    unless `hidden`: old names that still work, and dev. tests/test_completion.py checks bashou.bash
    offers exactly the commands that aren't hidden. `size`: the smallest terminal (columns, rows) its
    screen fits in; in a smaller one it says so and stops (tests/test_screens.py checks each size)."""

    def __init__(self, name, handler, row=None, args=(), hidden=False, size=None):
        self.name, self.handler, self.row, self.args, self.hidden = name, handler, row, args, hidden
        self.size = size


PET, LEARN, PLAY, SETTINGS = "Your pet", "Learn", "Play", "Settings"      # `bashou help`, in this order
COMMANDS = [
    Command("level", lambda a: level(), ("bashou", "your starter's level and what comes next", PET)),
    Command("pets", lambda a: pets(), ("bashou pets", "your collection", PET)),
    Command("achievements", lambda a: achievements_list(), ("bashou achievements", "what you earned, and what to try next", PET)),
    Command("evolve", run("evolve"), ("bashou evolve", "watch your pets evolve", PET), size=(40, 14)),
    Command("swap", lambda a: swap(a.pet), ("bashou swap [pet]", "change your active pet", PET), [("pet", dict(nargs="?"))],
            size=(40, 16)),
    Command("stats", lambda a: stats(), ("bashou stats", "your terminal stats: commands, tools, streaks", PET)),
    Command("share", run("share", "main", lambda a: a),
            ("bashou share", "a QR code: your phone turns your progress into an image to share", PET),
            [("--name", dict(help="the nickname on the image: 1-12 letters, digits, - or _ (asked the first time)"))],
            size=(60, 30)),                                                     # the whole QR code, to scan it
    Command("lesson", run("lesson.reader", "main", lambda a: [a.which] if a.which else []),
            ("bashou lesson [name]", "the Sage Owl's library: lessons with drawings, unlocked as you play", LEARN),
            [("which", dict(nargs="?", help="a lesson to open, or list"))], size=(60, 16)),
    Command("learn", run("learn", "main", "command"),
            ("bashou learn <command>", "take a command apart, piece by piece (alone: your pet's last tip)", LEARN),
            [("command", dict(nargs=argparse.REMAINDER))]),
    Command("project", run("project.command", "main", "words"),
            ("bashou project", "a real program to build, one small step at a time (Python, Shell, C, Rust)", LEARN),
            [("words", dict(nargs=argparse.REMAINDER))]),
    Command("talk", talk, ("bashou talk", "your pet gives you a tip now, with a command to try", LEARN)),
    Command("fight", lambda a: run("fight", "run")(a) and None,        # its result isn't an exit code
            ("bashou fight", "fight the threat your pet announced", PLAY)),
    Command("arena", run("arena", "main", "mode", "which"),
            ("bashou arena", "fight when you want: a timed fight, or a security investigation", PLAY),
            [("mode", dict(nargs="?", help="fight or security")), ("which", dict(nargs="?", help="security: number or id (see the list)"))]),
    Command("spot", run("spot"), ("bashou spot", "IPv6, hash, base64, regex, Rust…: say what a string is, fast", PLAY),
            size=(80, 14)),                          # a 40-character string with an answer on each side
    Command("adventure", run("adventure.game"), ("bashou adventure", "walk into the world with your starter", PLAY),
            size=(50, 20)),
    Command("on", run("setup", "run"), ("bashou on / off", "show or hide the pet (the first `on` adds Bashou to ~/.bashrc)", SETTINGS)),
    Command("off", lambda a: print("  " + _("Bashou isn't running in this terminal."))),   # bashou.bash answers first
    Command("config", lambda a: config(a.name, a.value), ("bashou config", "settings, language and skills (bashou config list shows them)", SETTINGS),
            [("name", dict(nargs="?")), ("value", dict(nargs="?"))]),
    Command("start", run("starter"), ("bashou start", "choose your starter (once)", SETTINGS), size=(60, 16)),
    Command("reset", lambda a: reset(), ("bashou reset", "start over with a new starter", SETTINGS)),
    Command("update", run("update", "run", "version", "packages"), ("bashou update", "get the new version", SETTINGS),
            [("--version", dict(help="install this release instead, even an older one (e.g. v0.2.0)")),
             ("--packages", dict(action="store_true", help="move to Bashou's apt or dnf repository (shows every command first)"))]),
    Command("version", version, ("bashou version", "which version of Bashou this is", SETTINGS)),
    Command("help", lambda a: print_help()),
    # old names, still working
    Command("language", lambda a: config("language", None), hidden=True),       # now bashou config language
    Command("skills", lambda a: config("skills", None), hidden=True),           # now bashou config skills
    Command("setup", run("setup", "run"), hidden=True),                         # now bashou on
    Command("security", run("arena", "main", lambda a: "security", "which"), args=[("which", dict(nargs="?"))],
            hidden=True),                                                       # now bashou arena security
    Command("dev", run_dev, args=[                                              # testing helpers
        ("action", dict(choices=["unlock-all", "stage", "stage-all", "level", "threat", "restore"])),
        ("pet", dict(nargs="?", help="pet (stage), level 1-9 (level) or challenge id (threat)")),
        ("stage", dict(nargs="?", type=int, default=3))], hidden=True),
]


def print_help():
    rows = [c.row for c in COMMANDS if c.row]
    width = max(len(usage) for usage, _t, _s in rows)
    print(f"\n  {BOLD}Bashou{RESET} · " + _("a pet that grows as you learn bash.") + "\n")
    for section in (PET, LEARN, PLAY, SETTINGS):
        print(f"  {BOLD}{_(section)}{RESET}")
        for usage, text, where in rows:
            if where == section:
                print(f"    {CYAN}{usage:<{width}}{RESET}  {_(text)}")
        print()


def too_small(command):
    """In a terminal smaller than the command's screen, say so instead of drawing a broken one."""
    if not command.size or not (sys.stdin.isatty() and sys.stdout.isatty()):
        return False
    try:
        cols, rows = os.get_terminal_size()
    except OSError:
        return False
    need_cols, need_rows = command.size
    if cols >= need_cols and rows >= need_rows:
        return False
    print("  " + _("Your terminal is too small: {cols}×{rows}. `bashou {name}` needs at least {need_cols}×{need_rows}, "
                   "or its screen would come out broken. Make the window bigger (or the font smaller), then "
                   "try again.").format(cols=cols, rows=rows, name=command.name, need_cols=need_cols, need_rows=need_rows))
    return True


class Parser(argparse.ArgumentParser):
    def print_help(self, file=None):
        if self.prog == "bashou":
            print_help()
        else:
            super().print_help(file)


def main():
    parser = Parser(prog="bashou", usage="bashou COMMAND  (bashou help lists them)")
    sub = parser.add_subparsers(dest="cmd", metavar="COMMAND", prog="bashou")
    for command in COMMANDS:
        options = {} if command.hidden else {"help": command.row[1] if command.row else command.name}
        cmd = sub.add_parser(command.name, **options)
        for name, kwargs in command.args:
            cmd.add_argument(name, **kwargs)
    args = parser.parse_args()
    command = next((c for c in COMMANDS if c.name == args.cmd), None)
    if command and too_small(command):
        raise SystemExit(1)
    code = command.handler(args) if command else level()
    if isinstance(code, int):
        raise SystemExit(code)
