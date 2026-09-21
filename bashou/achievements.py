"""Achievements: each belongs to a pet family and evolves that pet.

A rule is either `cmd` (checked on each successful command, given a Ctx) or
`state` (checked against the saved counters).
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable, Optional


@dataclass
class Ctx:
    analysis: object
    line: str
    hour: int

    def args(self, *tools):
        """Argument lists of every call to one of `tools`."""
        return [a for name, a in self.analysis.commands if name in tools]

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
    A("raw", "axolotl", "Raw", "print raw strings with `jq -r`", cmd=lambda c: c.flag("jq", "r", ("--raw-output",))),
    A("selector", "axolotl", "Selector", "filter with `select()`", cmd=lambda c: c.arg("jq", r"select\(")),
    A("mapper", "axolotl", "Mapper", "transform arrays with `map()`", cmd=lambda c: c.arg("jq", r"map\(")),
]

BY_ID = {a.id: a for a in ALL}


def family(pet):
    return [a for a in ALL if a.pet == pet]
