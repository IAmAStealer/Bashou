"""Achievements: each belongs to a pet family and evolves that pet.

A rule is either `cmd` (checked on each successful command, given a Ctx) or
`state` (checked against the saved counters).
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable, Optional

from . import safety
from . import which


@dataclass
class Ctx:
    analysis: object
    line: str
    hour: int

    def args(self, *tools):
        """Argument lists of every call to one of `tools`."""
        return [a for name, a in self.analysis.commands if name in tools]

    def sub(self, tool, name, *with_any):
        """True if a call to `tool` used the subcommand `name` (`git stash`, `kubectl -n x get`),
        with one of the `with_any` arguments when given."""
        return any(name in args and (not with_any or any(w in args for w in with_any))
                   for args in self.args(tool))

    def tar(self, *modes):
        """True if a `tar` call has all the mode letters (`tar -czf` and `tar czf` alike)."""
        for args in self.args("tar"):
            letters = {ch for i, a in enumerate(args) if not a.startswith("--")
                       and (a.startswith("-") or (i == 0 and a.isalpha())) for ch in a.lstrip("-")}
            if set(modes) <= letters:
                return True
        return False

    def flag(self, tools, short="", long=()):
        """True if a call to `tools` used one of the short flag letters or long options."""
        if isinstance(tools, str):
            tools = (tools,)
        for args in self.args(*tools):
            for a in args:
                if a.startswith("--"):
                    if a.split("=")[0] in long:
                        return True
                elif a.startswith("-") and any(ch in a[1:] for ch in short):
                    return True
        return False

    def arg(self, tools, pattern):
        """True if a call to `tools` has an argument matching the regex."""
        if isinstance(tools, str):
            tools = (tools,)
        return any(re.search(pattern, a) for args in self.args(*tools) for a in args)


@dataclass
class Achievement:
    id: str
    pet: str
    name: str
    how: str
    cmd: Optional[Callable] = None
    state: Optional[Callable] = None
    needs: tuple = ()           # commands it needs (any one); hidden when none is installed

    def available(self):
        return not self.needs or any(map(which.installed, self.needs))


def tool(s, *names):
    return sum(s["tools"].get(n, 0) for n in names)


def streak(days):
    have, day, count = set(days), date.today(), 0
    while day.isoformat() in have:
        count += 1
        day -= timedelta(days=1)
    return count


def nested_subst(line):
    depth = best = 0
    i = 0
    while i < len(line):
        if line.startswith("$(", i) and not line.startswith("$((", i):
            depth += 1
            best = max(best, depth)
            i += 2
            continue
        if line[i] == ")" and depth:
            depth -= 1
        i += 1
    return best >= 2


A = Achievement
ALL = [
    # Bat: habits
    A("night_owl", "bat", "Night owl", "run a command between midnight and 5 am", cmd=lambda c: c.hour < 5),
    A("streak7", "bat", "Streak", "use the terminal 7 days in a row", state=lambda s: streak(s["days"]) >= 7),
    A("explorer", "bat", "Explorer", "use 20 different tools", state=lambda s: len(s["tools"]) >= 20),

    # Frog: volume
    A("sprinter", "frog", "Sprinter", "run 100 commands in one day", state=lambda s: s["today"]["count"] >= 100),
    A("historian", "frog", "Historian", "look back with `history`", cmd=lambda c: bool(c.args("history"))),
    A("thousand", "frog", "Thousand", "run 1,000 commands", state=lambda s: s["commands"] >= 1000),

    # Turtle: regularity
    A("week", "turtle", "Week", "7 active days", state=lambda s: len(s["days"]) >= 7),
    A("month", "turtle", "Month", "30 active days", state=lambda s: len(s["days"]) >= 30),
    A("year", "turtle", "Year", "365 active days", state=lambda s: len(s["days"]) >= 365),

    # Mushroom: loops
    A("loop", "mushroom", "Loop", "write a `for` loop", cmd=lambda c: bool(re.search(r"(^|[;&|(\s])for\s", c.line))),
    A("reader", "mushroom", "Reader", "read lines with `while read`", cmd=lambda c: bool(re.search(r"while\s+(IFS=\S*\s+)?read\b", c.line))),
    A("ranges", "mushroom", "Ranges", "count with `seq` or `{1..10}`", cmd=lambda c: bool(c.args("seq")) or bool(re.search(r"\{\d+\.\.\d+", c.line))),

    # Slime: substitutions
    A("capture", "slime", "Capture", "capture output with `$( )`", cmd=lambda c: "subst" in c.analysis.constructs),
    A("nested", "slime", "Nested", "nest `$( $( ) )`", cmd=lambda c: nested_subst(c.line)),
    A("substitute", "slime", "Substitute", "use a process substitution `<( )`", cmd=lambda c: "procsub" in c.analysis.constructs),
    A("here", "slime", "Here", "feed a heredoc `<<EOF`", cmd=lambda c: "heredoc" in c.analysis.constructs),

    # Living sofa: sort and uniq
    A("tally", "sofa", "Tally", "count duplicates with `uniq -c`", cmd=lambda c: c.flag("uniq", "c", ("--count",))),
    A("ranking", "sofa", "Ranking", "sort numbers in reverse with `sort -rn`", cmd=lambda c: c.flag("sort", "n") and c.flag("sort", "r")),
    A("unique", "sofa", "Unique", "deduplicate with `sort -u`", cmd=lambda c: c.flag("sort", "u", ("--unique",))),

    # Octopus: pipes
    A("plumber", "octopus", "Plumber", "chain 3 commands with pipes", cmd=lambda c: c.analysis.pipes >= 3),
    A("pipeline", "octopus", "Pipeline", "chain 5 commands with pipes", cmd=lambda c: c.analysis.pipes >= 5),
    A("tee_time", "octopus", "Tee time", "split a stream with `tee`", cmd=lambda c: "tee" in c.analysis.constructs),
    A("merge", "octopus", "Merge", "send stderr into the pipe with `2>&1`", cmd=lambda c: "stderr" in c.analysis.constructs),

    # Gremlin: shows up after risky commands, and evolves as you learn safe habits
    A("inspector", "gremlin", "Inspector", "read a script before running it: `less install.sh`",
      cmd=lambda c: c.arg(("less", "more", "cat", "head", "bat", "view", "vim", "nano"), r"\.sh$")),
    A("checksum", "gremlin", "Checksum", "check a download with `sha256sum`",
      cmd=lambda c: bool(c.args("sha256sum", "sha512sum", "shasum", "b2sum")) or c.arg("gpg", r"^--verify$")),
    A("save_first", "gremlin", "Save first", "download to a file with `curl -o` or `wget`, not into a shell",
      cmd=lambda c: (c.flag("curl", "oO", ("--output", "--remote-name")) or bool(c.args("wget")))
      and not safety.risk(c.line)),
    A("tight", "gremlin", "Tight", "set careful permissions: `chmod u+x` or `chmod 600`",
      cmd=lambda c: c.arg("chmod", r"^(0?[67][0-5][0-5]|u\+r?w?x|go?-r?w?x?|o-r?w?x?)$")),
    A("first_flag", "gremlin", "First flag", "solve a security challenge: `bashou security`",
      state=lambda s: len(s.get("security", [])) >= 1),
    A("investigator", "gremlin", "Investigator", "solve 6 security challenges",
      state=lambda s: len(s.get("security", [])) >= 6),

    # Snail: bashou adventure (and the file basics its chests teach)
    A("builder", "snail", "Builder", "create nested folders with `mkdir -p`", cmd=lambda c: c.flag("mkdir", "p", ("--parents",))),
    A("copycat", "snail", "Copycat", "copy a folder with `cp -r`", cmd=lambda c: c.flag("cp", "rRa", ("--recursive", "--archive"))),
    A("shortcut", "snail", "Shortcut", "make a symbolic link with `ln -s`", cmd=lambda c: c.flag("ln", "s", ("--symbolic",))),
    A("first_steps", "snail", "First steps", "walk 100 m in `bashou adventure`",
      state=lambda s: adv(s).get("walked", 0) >= 100),
    A("checkpoint", "snail", "Checkpoint", "beat a boss in `bashou adventure`", state=lambda s: len(adv(s).get("bosses", [])) >= 1),
    A("polyglot", "snail", "Polyglot", "beat bosses of 3 different topics",
      state=lambda s: len({b["topic"] for b in adv(s).get("bosses", [])}) >= 3),
    A("scholar", "snail", "Scholar", "reach level 3 in a topic", state=lambda s: max(adv(s).get("levels", {0: 0}).values(), default=0) >= 2),
    A("flawless", "snail", "Flawless", "beat a boss without losing a heart on the way",
      state=lambda s: any(b.get("flawless") for b in adv(s).get("bosses", []))),
    A("locksmith", "snail", "Locksmith", "open 5 chests", state=lambda s: len(adv(s).get("trials", [])) >= 5),
    A("questmaster", "snail", "Questmaster", "finish chapter 3", state=lambda s: adv(s).get("chapters_done", 0) >= 3),

    # Dragon: fights
    A("warrior", "dragon", "Warrior", "win a fight", state=lambda s: s["fights_won"] >= 1),
    A("veteran", "dragon", "Veteran", "win 10 fights", state=lambda s: s["fights_won"] >= 10),
    A("legend", "dragon", "Legend", "win 30 fights", state=lambda s: s["fights_won"] >= 30),

    # Fox: find
    A("time_traveller", "fox", "Time traveller", "find by date: `-mtime`, `-mmin` or `-newer`", cmd=lambda c: c.arg("find", r"^-(mtime|mmin|newer|atime|ctime)$")),
    A("executor", "fox", "Executor", "act on results with `find -exec`", cmd=lambda c: c.arg("find", r"^-(exec|execdir|ok)$")),
    A("pruner", "fox", "Pruner", "skip a directory with `-prune`", cmd=lambda c: c.arg("find", r"^-prune$")),
    A("tracker", "fox", "Tracker", "use find 100 times", state=lambda s: tool(s, "find") >= 100),

    # Owl: awk
    A("field_reader", "owl", "Field reader", "set a separator with `awk -F`", cmd=lambda c: c.arg(("awk", "gawk", "mawk"), r"^-F")),
    A("accountant", "owl", "Accountant", "sum a column and print it in `END`", cmd=lambda c: c.arg(("awk", "gawk", "mawk"), r"\+=.*END|END.*\+=|\+=[\s\S]*END")),
    A("scribe", "owl", "Scribe", "format output with `printf` in awk", cmd=lambda c: c.arg(("awk", "gawk", "mawk"), r"printf")),
    A("sage", "owl", "Sage", "use awk 100 times", state=lambda s: tool(s, "awk", "gawk", "mawk") >= 100),

    # Mole: grep
    A("digger", "mole", "Digger", "search a tree with `grep -r`", cmd=lambda c: c.flag(("grep",), "rR", ("--recursive",))),
    A("regex", "mole", "Regex", "use extended regexes: `grep -E`", cmd=lambda c: c.flag(("grep",), "EP", ("--extended-regexp", "--perl-regexp")) or bool(c.args("egrep"))),
    A("context", "mole", "Context", "show lines around matches with `-A`, `-B` or `-C`", cmd=lambda c: c.flag(("grep",), "ABC", ("--context", "--after-context", "--before-context"))),
    A("miner", "mole", "Miner", "use grep 250 times", state=lambda s: tool(s, "grep", "egrep", "fgrep", "rg") >= 250),

    # Snake: sed
    A("in_place", "snake", "In place", "edit a file with `sed -i`", cmd=lambda c: c.flag("sed", "i", ("--in-place",))),
    A("global", "snake", "Global", "replace every match: `s/…/…/g`", cmd=lambda c: c.arg("sed", r"s(.).*\1.*\1[a-zA-Z]*g")),
    A("printer", "snake", "Printer", "print chosen lines with `sed -n …p`", cmd=lambda c: c.flag("sed", "n") and c.arg("sed", r"p$")),

    # Ghost: processes
    A("census", "ghost", "Census", "list every process: `ps aux` or `ps -ef`", cmd=lambda c: c.arg("ps", r"^(aux|-ef|-e|ax|-A)$")),
    A("seeker", "ghost", "Seeker", "find a process by name with `pgrep`", cmd=lambda c: bool(c.args("pgrep"))),
    A("signal", "ghost", "Signal", "send a named signal: `kill -TERM`, `-HUP`…", cmd=lambda c: c.arg(("kill", "pkill", "killall"), r"^-(s$|[A-Z]{3,}|SIG)")),

    # Spider: strace
    A("filter", "spider", "Filter", "trace only some calls with `strace -e`", cmd=lambda c: c.flag("strace", "e")),
    A("follow", "spider", "Follow", "follow child processes with `strace -f`", cmd=lambda c: c.flag("strace", "f")),
    A("summary", "spider", "Summary", "count syscalls with `strace -c`", cmd=lambda c: c.flag("strace", "c")),

    # Ant: xargs
    A("placeholder", "ant", "Placeholder", "place arguments with `xargs -I{}`", cmd=lambda c: c.arg("xargs", r"^-I")),
    A("parallel", "ant", "Parallel", "run jobs in parallel with `xargs -P`", cmd=lambda c: c.arg("xargs", r"^-P")),
    A("null", "ant", "Null", "handle odd file names: `-print0 | xargs -0`", cmd=lambda c: c.flag("xargs", "0", ("--null",))),

    # Axolotl: jq
    # Beaver: git
    A("brancher", "beaver", "Brancher", "start a branch with `git switch -c`",
      cmd=lambda c: c.sub("git", "switch", "-c", "-C", "--create") or c.sub("git", "checkout", "-b", "-B")),
    A("stasher", "beaver", "Stasher", "put work aside with `git stash`", cmd=lambda c: c.sub("git", "stash")),
    A("grapher", "beaver", "Grapher", "draw the history with `git log --graph`", cmd=lambda c: c.sub("git", "log", "--graph")),
    A("bisector", "beaver", "Bisector", "hunt the commit that broke it with `git bisect`", cmd=lambda c: c.sub("git", "bisect")),

    # Squirrel: archives
    A("packer", "squirrel", "Packer", "pack a folder with `tar -czf`", cmd=lambda c: c.tar("c", "z") or c.tar("c", "J")),
    A("peeker", "squirrel", "Peeker", "look inside an archive with `tar -tf`", cmd=lambda c: c.tar("t")),
    A("unpacker", "squirrel", "Unpacker", "extract into a folder with `tar -xf … -C dir`",
      cmd=lambda c: c.tar("x") and c.arg("tar", r"^(-C|--directory)")),
    A("squeezer", "squirrel", "Squeezer", "compress harder with `xz` or `zstd`",
      cmd=lambda c: bool(c.args("xz", "zstd")), needs=("xz", "zstd")),

    # Pigeon: network
    A("headers", "pigeon", "Headers", "see only the headers with `curl -I`", cmd=lambda c: c.flag("curl", "I", ("--head",)),
      needs=("curl",)),
    A("poster", "pigeon", "Poster", "send data with `curl -d`",
      cmd=lambda c: c.flag("curl", "d", ("--data", "--data-raw", "--json")), needs=("curl",)),
    A("tunneler", "pigeon", "Tunneler", "forward a port with `ssh -L`, or jump with `ssh -J`",
      cmd=lambda c: c.flag("ssh", "LRJ"), needs=("ssh",)),
    A("mirror", "pigeon", "Mirror", "sync folders with `rsync -a`", cmd=lambda c: c.flag("rsync", "a", ("--archive",)),
      needs=("rsync",)),
    A("resolver", "pigeon", "Resolver", "ask DNS with `dig +short`", cmd=lambda c: c.arg("dig", r"^(\+short|@.)"),
      needs=("dig",)),
    A("tracer", "pigeon", "Tracer", "follow a name from the root with `dig +trace`", cmd=lambda c: c.arg("dig", r"^\+trace$"),
      needs=("dig",)),

    # Hedgehog: permissions
    A("octal", "hedgehog", "Octal", "set a mode in numbers: `chmod 644`", cmd=lambda c: c.arg("chmod", r"^0?[0-7]{3}$")),
    A("symbolic", "hedgehog", "Symbolic", "add or remove a right: `chmod g+w`", cmd=lambda c: c.arg("chmod", r"^[ugoa]+[-+=][rwxXst]+$")),
    A("owner", "hedgehog", "Owner", "change the owner with `chown user:group`", cmd=lambda c: c.arg("chown", r"^[\w.$-]+:[\w.$-]*$")),
    A("mode_reader", "hedgehog", "Mode reader", "read a file's mode with `stat -c %a`", cmd=lambda c: c.arg("stat", r"%a")),

    # Bee: systemd
    A("status", "bee", "Status", "check a service with `systemctl status`", cmd=lambda c: c.sub("systemctl", "status")),
    A("logbook", "bee", "Logbook", "read a service's logs with `journalctl -u`",
      cmd=lambda c: c.flag("journalctl", "u", ("--unit",)), needs=("journalctl",)),
    A("enabler", "bee", "Enabler", "start a service now and at boot: `systemctl enable --now`",
      cmd=lambda c: c.sub("systemctl", "enable", "--now")),
    A("reload", "bee", "Reload", "after editing a unit file: `systemctl daemon-reload`", cmd=lambda c: c.sub("systemctl", "daemon-reload")),

    # Whale: kubectl
    A("pods", "whale", "Pods", "list every pod with `kubectl get pods -A`", cmd=lambda c: c.sub("kubectl", "get", "-A", "--all-namespaces")),
    A("describer", "whale", "Describer", "see why a pod is stuck with `kubectl describe`", cmd=lambda c: c.sub("kubectl", "describe")),
    A("tailer", "whale", "Tailer", "follow a pod's logs with `kubectl logs -f`",
      cmd=lambda c: c.sub("kubectl", "logs") and c.flag("kubectl", "f", ("--follow",))),
    A("diver", "whale", "Diver", "open a shell in a pod with `kubectl exec -it`",
      cmd=lambda c: c.sub("kubectl", "exec") and c.flag("kubectl", "i") and c.flag("kubectl", "t")),

    # Meerkat: watching the system
    A("disk", "meerkat", "Disk", "see free space with `df -h`", cmd=lambda c: c.flag("df", "h", ("--human-readable",))),
    A("sizer", "meerkat", "Sizer", "size a folder with `du -sh`", cmd=lambda c: c.flag("du", "s") and c.flag("du", "h")),
    A("memory", "meerkat", "Memory", "check the memory with `free -h`", cmd=lambda c: c.flag("free", "h"), needs=("free",)),
    A("watcher", "meerkat", "Watcher", "rerun a command every few seconds with `watch -n`",
      cmd=lambda c: c.flag("watch", "n", ("--interval",)), needs=("watch",)),

    A("raw", "axolotl", "Raw", "print raw strings with `jq -r`", cmd=lambda c: c.flag("jq", "r", ("--raw-output",))),
    A("selector", "axolotl", "Selector", "filter with `select()`", cmd=lambda c: c.arg("jq", r"select\(")),
    A("mapper", "axolotl", "Mapper", "transform arrays with `map()`", cmd=lambda c: c.arg("jq", r"map\(")),
]

# Families about a command this system may not have: hints skip them when it's missing.
FAMILY_NEEDS = {"spider": ("strace",), "axolotl": ("jq",), "whale": ("kubectl",), "bee": ("systemctl",),
                "beaver": ("git",), "hedgehog": ("chmod",)}
for _a in ALL:
    _a.needs = _a.needs or FAMILY_NEEDS.get(_a.pet, ())

BY_ID = {a.id: a for a in ALL}


# How hard an achievement is to learn: hints suggest the easiest ones left first.
EASY = {"builder", "copycat", "historian", "loop", "ranges", "capture", "tally", "unique", "plumber", "inspector", "checksum",
        "tight", "digger", "census", "global", "stasher", "peeker", "headers", "octal", "status",
        "pods", "disk"}
HARD = {"nested", "substitute", "pruner", "scribe", "accountant", "parallel", "null", "mapper", "follow",
        "summary", "filter", "bisector", "tunneler", "reload", "diver", "tracer"}


def difficulty(a):
    """1 easy, 2 medium, 3 hard."""
    return 1 if a.id in EASY else 3 if a.id in HARD else 2


def adv(state):
    return state.get("adventure") or {}


def family(pet):
    """The pet's achievements this system can earn."""
    return [a for a in ALL if a.pet == pet and a.available()]


def usable():
    return [a for a in ALL if a.available()]


def earned(state):
    """Earned achievements this system can still earn (counted against `usable()`)."""
    ids = set(state["achievements"])
    return [a for a in usable() if a.id in ids]
