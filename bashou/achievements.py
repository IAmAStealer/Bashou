"""Achievements: each belongs to a pet family and evolves that pet.

A rule is either `cmd` (checked on each successful command, given a Ctx) or
`state` (checked against the saved counters).
"""

import re
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Callable, Optional

from . import challenges, creatures, lesson, safety, which


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
    hidden: bool = False        # a secret: never listed or hinted before you earn it
    example: str = ""           # a command that earns it: the pet's hint shows it
    next: str = ""              # the achievement it leads to (grep -r -> grep -E -> grep -C): a chain, like pet forms
    depth: int = 1              # its place in its chain (1 = where you start): how hard it is. Set below, from `next`

    def available(self):
        return not self.needs or any(map(which.installed, self.needs))


def won_network(s):
    return any(ch.id in s["challenges"] for ch in challenges.network.ALL)


def tool(s, *names):
    return sum(s["tools"].get(n, 0) for n in names)


def lessons_read(s):
    """The lessons (English files) you read to the end."""
    done = set((s.get("lessons") or {}).get("read", []))
    return [le for le in lesson.english() if le["id"] in done]


def first_skill(le):
    return next(iter(lesson.skills_of(le)), "")


def lessons_mastered(s):
    return [le for le in lessons_read(s) if lesson.mastered(s, le)]


def lessons_offered(s):
    """The lessons of the skills you learn."""
    return lesson.shown(s, lesson.english())


def skills_offered(s):
    return {first_skill(le) for le in lessons_offered(s)}


def read_at_least(s, n):
    return len(lessons_read(s)) >= min(n, len(lessons_offered(s)))


def mastered_at_least(s, n):
    return len(lessons_mastered(s)) >= min(n, len(lessons_offered(s)))


def all_lessons_read(s):
    done = set((s.get("lessons") or {}).get("read", []))
    return all(le["id"] in done for le in lesson.shown(s, lesson.english()))


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


def _projects():
    from . import project                        # read only when a project achievement is checked
    return project


def steps_done(s):
    return _projects().steps_done(s)


def project_done(s, pid):
    return pid in _projects().finished(s)


def projects_done(s, language=None, difficulty=None):
    """Finished projects, of a language and difficulty when given."""
    known = {p["id"]: p for p in _projects().english()}
    return [pid for pid in _projects().finished(s) if (not language or known[pid]["language"] == language)
            and (not difficulty or known[pid]["difficulty"] == difficulty)]


def project_streak(s):
    return streak((s.get("projects") or {}).get("days", []))


STEP_MILESTONES = [(1, "first_brick", "First brick"), (3, "foundations", "Foundations"), (5, "scaffolding", "Scaffolding"),
                   (10, "walls_up", "Walls up"), (15, "roof_on", "Roof on"), (20, "site_builder", "Builder"),
                   (30, "stonemason", "Stonemason"), (40, "architect", "Architect"), (50, "site_engineer", "Engineer"),
                   (75, "master_builder", "Master builder"), (100, "city_planner", "City planner"),
                   (150, "wonder", "Wonder of the world")]
# Landscape: `bashou project`. Owner: lots of rewards to keep the motivation, from the first step.
PROJECT_ACHIEVEMENTS = [
    ("python_pdf", "pdf_tamer", "PDF tamer", "merge and split PDFs in Python: `bashou project start python pdf`"),
    ("python_photos", "photo_sorter", "Photo sorter", "sort your photos by date in Python: `bashou project start python photos`"),
    ("python_budget", "budget_keeper", "Budget keeper", "build your budget web page in Python: `bashou project start python budget`"),
    ("shell_pdf", "pdf_juggler", "PDF juggler", "merge and split PDFs with a shell script: `bashou project start shell pdf`"),
    ("shell_backup", "safe_keeper", "Safe keeper", "write a backup script: `bashou project start shell backup`"),
    ("shell_logs", "log_reader", "Log reader", "turn a log into a daily report: `bashou project start shell logs`"),
    ("c_pomodoro", "time_keeper", "Time keeper", "build a Pomodoro timer in C: `bashou project start c pomodoro`"),
    ("c_energy", "meter_reader", "Meter reader", "track your electricity or fuel in C: `bashou project start c energy`"),
    ("c_contacts", "address_book", "Address book", "build a contact book in C: `bashou project start c contacts`"),
    ("rust_todo", "list_maker", "List maker", "build a todo list in Rust: `bashou project start rust todo`"),
    ("rust_netwatch", "watchtower", "Watchtower", "log your internet outages in Rust: `bashou project start rust netwatch`"),
    ("rust_menu", "shopping_planner", "Shopping planner", "turn a weekly menu into a shopping list in Rust: `bashou project start rust menu`"),
    ("rust_papers", "paper_sorter", "Paper sorter", "find duplicates and sort your papers in Rust: `bashou project start rust papers`"),
]
LANGUAGE_ACHIEVEMENTS = [("python", "pythonista", "Pythonista", "finish a Python project"),
                         ("shell", "shell_smith", "Shell smith", "finish a Shell project"),
                         ("c", "c_crafter", "C crafter", "finish a C project"),
                         ("rust", "rustacean", "Rustacean", "finish a Rust project")]


A = Achievement
ALL = [
    # Bat: habits
    A("night_owl", "bat", "Night shift", "run a command between midnight and 5 am", cmd=lambda c: c.hour < 5),
    A("streak7", "bat", "Streak", "use the terminal 7 days in a row", state=lambda s: streak(s["days"]) >= 7),
    A("explorer", "bat", "Explorer", "use 20 different tools", state=lambda s: len(s["tools"]) >= 20),

    # Frog: volume
    A("sprinter", "frog", "Sprinter", "run 100 commands in one day", state=lambda s: s["today"]["count"] >= 100, next="thousand"),
    A("historian", "frog", "Historian", "look back with `history`", cmd=lambda c: bool(c.args("history")), example='history | tail'),
    A("thousand", "frog", "Thousand", "run 1,000 commands", state=lambda s: s["commands"] >= 1000),

    # Turtle: regularity
    A("week", "turtle", "Week", "7 active days", state=lambda s: len(s["days"]) >= 7, next="month"),
    A("month", "turtle", "Month", "30 active days", state=lambda s: len(s["days"]) >= 30, next="year"),
    A("year", "turtle", "Year", "365 active days", state=lambda s: len(s["days"]) >= 365),

    # Mushroom: loops
    A("loop", "mushroom", "Loop", "write a `for` loop", cmd=lambda c: bool(re.search(r"(^|[;&|(\s])for\s", c.line)), next="reader", example='for f in *; do echo $f; done'),
    A("reader", "mushroom", "Reader", "read lines with `while read`", cmd=lambda c: bool(re.search(r"while\s+(IFS=\S*\s+)?read\b", c.line)), example='while read -r l; do echo $l; done < file'),
    A("ranges", "mushroom", "Ranges", "count with `seq` or `{1..10}`", cmd=lambda c: bool(c.args("seq")) or bool(re.search(r"\{\d+\.\.\d+", c.line)), next="loop", example='for i in {1..3}; do echo $i; done'),

    # Slime: substitutions
    A("capture", "mushroom", "Capture", "capture output with `$( )`", cmd=lambda c: "subst" in c.analysis.constructs, next="nested", example='echo "today: $(date +%A)"'),
    A("nested", "mushroom", "Nested", "nest `$( $( ) )`", cmd=lambda c: nested_subst(c.line), next="substitute", example='echo $(basename $(pwd))'),
    A("substitute", "mushroom", "Substitute", "use a process substitution `<( )`", cmd=lambda c: "procsub" in c.analysis.constructs, example='diff <(ls /bin) <(ls /usr/bin)'),
    A("here", "mushroom", "Here", "feed a heredoc `<<EOF`", cmd=lambda c: "heredoc" in c.analysis.constructs, example='cat <<EOF > note.txt\nhello\nEOF'),

    # Living sofa: sort and uniq
    A("tally", "sofa", "Tally", "count duplicates with `uniq -c`", cmd=lambda c: c.flag("uniq", "c", ("--count",)), next="ranking", example='sort file | uniq -c'),
    A("ranking", "sofa", "Ranking", "sort numbers in reverse with `sort -rn`", cmd=lambda c: c.flag("sort", "n") and c.flag("sort", "r"), example='du -s * | sort -rn'),
    A("unique", "sofa", "Unique", "deduplicate with `sort -u`", cmd=lambda c: c.flag("sort", "u", ("--unique",)), next="tally", example='sort -u file'),

    # Octopus: pipes
    A("plumber", "octopus", "Plumber", "chain 3 commands with pipes", cmd=lambda c: c.analysis.pipes >= 3, next="pipeline", example='ps aux | grep bash | wc -l'),
    A("pipeline", "octopus", "Pipeline", "chain 5 commands with pipes", cmd=lambda c: c.analysis.pipes >= 5, example='cat f | tr A-Z a-z | sort | uniq -c | sort -rn'),
    A("tee_time", "octopus", "Tee time", "split a stream with `tee`", cmd=lambda c: "tee" in c.analysis.constructs, example='ls | tee list.txt'),
    A("merge", "octopus", "Merge", "send stderr into the pipe with `2>&1`", cmd=lambda c: "stderr" in c.analysis.constructs, example='make 2>&1 | less'),

    # Gremlin: shows up after risky commands, and evolves as you learn safe habits
    A("inspector", "gremlin", "Inspector", "read a script before running it: `less install.sh`",
      cmd=lambda c: c.arg(("less", "more", "cat", "head", "bat", "view", "vim", "nano"), r"\.sh$"), next="save_first", example='less install.sh'),
    A("checksum", "gremlin", "Checksum", "check a download with `sha256sum`",
      cmd=lambda c: bool(c.args("sha256sum", "sha512sum", "shasum", "b2sum")) or c.arg("gpg", r"^--verify$"), example='sha256sum install.sh'),
    A("save_first", "gremlin", "Save first", "download to a file with `curl -o` or `wget`, not into a shell",
      cmd=lambda c: (c.flag("curl", "oO", ("--output", "--remote-name")) or bool(c.args("wget")))
      and not safety.risk(c.line), next="checksum", example='curl -fsSLo install.sh https://example.com/install.sh'),
    A("tight", "gremlin", "Tight", "set careful permissions: `chmod u+x` or `chmod 600`",
      cmd=lambda c: c.arg("chmod", r"^(0?[67][0-5][0-5]|u\+r?w?x|go?-r?w?x?|o-r?w?x?)$"), example='chmod u+x install.sh'),
    A("first_flag", "gremlin", "First flag", "solve a security challenge: `bashou arena security`",
      state=lambda s: len(s.get("security", [])) >= 1, next="investigator"),
    A("investigator", "gremlin", "Investigator", "solve 6 security challenges",
      state=lambda s: len(s.get("security", [])) >= 6),

    # Snail: bashou adventure (and the file basics its chests teach)
    A("builder", "snail", "Builder", "create nested folders with `mkdir -p`", cmd=lambda c: c.flag("mkdir", "p", ("--parents",)), next="copycat", example='mkdir -p camp/tent/bed'),
    A("copycat", "snail", "Copycat", "copy a folder with `cp -r`", cmd=lambda c: c.flag("cp", "rRa", ("--recursive", "--archive")), next="shortcut", example='cp -r notes notes.bak'),
    A("shortcut", "snail", "Shortcut", "make a symbolic link with `ln -s`", cmd=lambda c: c.flag("ln", "s", ("--symbolic",)), example='ln -s ~/projects p'),
    A("first_steps", "snail", "First steps", "walk 100 m in `bashou adventure`",
      state=lambda s: adv(s).get("walked", 0) >= 100, next="checkpoint"),
    A("checkpoint", "snail", "Checkpoint", "beat a boss in `bashou adventure`", state=lambda s: len(adv(s).get("bosses", [])) >= 1, next="polyglot"),
    A("polyglot", "snail", "Polyglot", "beat bosses of 3 different topics",
      state=lambda s: len({b["topic"] for b in adv(s).get("bosses", [])}) >= 3, next="questmaster"),
    A("scholar", "snail", "Scholar", "reach level 3 in a topic", state=lambda s: max(adv(s).get("levels", {0: 0}).values(), default=0) >= 2),
    A("flawless", "snail", "Flawless", "beat a boss without losing a heart on the way",
      state=lambda s: any(b.get("flawless") for b in adv(s).get("bosses", []))),
    A("locksmith", "snail", "Locksmith", "open 5 chests", state=lambda s: len(adv(s).get("trials", [])) >= 5),
    A("questmaster", "snail", "Questmaster", "finish chapter 3", state=lambda s: adv(s).get("chapters_done", 0) >= 3),

    # Dragon: fights
    A("warrior", "dragon", "Warrior", "win a fight", state=lambda s: s["fights_won"] >= 1, next="veteran", example='bashou fight'),
    A("veteran", "dragon", "Veteran", "win 10 fights", state=lambda s: s["fights_won"] >= 10, next="legend"),
    A("legend", "dragon", "Legend", "win 30 fights", state=lambda s: s["fights_won"] >= 30),

    # Fox: find
    A("time_traveller", "fox", "Time traveller", "find by date: `-mtime`, `-mmin` or `-newer`", cmd=lambda c: c.arg("find", r"^-(mtime|mmin|newer|atime|ctime)$"), next="executor", example='find . -mtime -1'),
    A("executor", "fox", "Executor", "act on results with `find -exec`", cmd=lambda c: c.arg("find", r"^-(exec|execdir|ok)$"), next="pruner", example="find . -name '*.tmp' -exec rm {} +"),
    A("pruner", "fox", "Pruner", "skip a directory with `-prune`", cmd=lambda c: c.arg("find", r"^-prune$"), example='find . -name .git -prune -o -type f -print'),
    A("tracker", "fox", "Tracker", "use find 100 times", state=lambda s: tool(s, "find") >= 100),

    # Owl: awk
    A("field_reader", "owl", "Field reader", "set a separator with `awk -F`", cmd=lambda c: c.arg(("awk", "gawk", "mawk"), r"^-F"), next="accountant", example="awk -F: '{print $1}' /etc/passwd"),
    A("accountant", "owl", "Accountant", "sum a column and print it in `END`", cmd=lambda c: c.arg(("awk", "gawk", "mawk"), r"\+=.*END|END.*\+=|\+=[\s\S]*END"), next="scribe", example="awk '{s+=$1} END {print s}' f"),
    A("scribe", "owl", "Scribe", "format output with `printf` in awk", cmd=lambda c: c.arg(("awk", "gawk", "mawk"), r"printf"), example='awk \'{printf "%-10s %s\\n", $1, $2}\' f'),
    A("sage", "owl", "Sage", "use awk 100 times", state=lambda s: tool(s, "awk", "gawk", "mawk") >= 100),

    # Mole: grep
    A("digger", "mole", "Digger", "search a tree with `grep -r`", cmd=lambda c: c.flag(("grep",), "rR", ("--recursive",)), next="regex", example='grep -rn TODO .'),
    A("regex", "mole", "Regex", "use extended regexes: `grep -E`", cmd=lambda c: c.flag(("grep",), "EP", ("--extended-regexp", "--perl-regexp")) or bool(c.args("egrep")), next="context", example="grep -E 'cat|dog' f"),
    A("context", "mole", "Context", "show lines around matches with `-A`, `-B` or `-C`", cmd=lambda c: c.flag(("grep",), "ABC", ("--context", "--after-context", "--before-context")), example='grep -C2 error log'),
    A("miner", "mole", "Miner", "use grep 250 times", state=lambda s: tool(s, "grep", "egrep", "fgrep", "rg") >= 250),

    # Snake: sed
    A("in_place", "snake", "In place", "edit a file with `sed -i`", cmd=lambda c: c.flag("sed", "i", ("--in-place",)), next="printer", example="sed -i 's/old/new/' f"),
    A("global", "snake", "Global", "replace every match: `s/…/…/g`", cmd=lambda c: c.arg("sed", r"s(.).*\1.*\1[a-zA-Z]*g"), next="in_place", example="sed 's/a/b/g' f"),
    A("printer", "snake", "Printer", "print chosen lines with `sed -n …p`", cmd=lambda c: c.flag("sed", "n") and c.arg("sed", r"p$"), example="sed -n '1,5p' f"),

    # Ghost: processes
    A("census", "ghost", "Census", "list every process: `ps aux` or `ps -ef`", cmd=lambda c: c.arg("ps", r"^(aux|-ef|-e|ax|-A)$"), next="seeker", example='ps aux'),
    A("seeker", "ghost", "Seeker", "find a process by name with `pgrep`", cmd=lambda c: bool(c.args("pgrep")), next="signal", example='pgrep -a bash'),
    A("signal", "ghost", "Signal", "send a named signal: `kill -TERM`, `-HUP`…", cmd=lambda c: c.arg(("kill", "pkill", "killall"), r"^-(s$|[A-Z]{3,}|SIG)"), example='kill -TERM <pid>'),

    # Spider: strace
    A("filter", "spider", "Filter", "trace only some calls with `strace -e`", cmd=lambda c: c.flag("strace", "e"), next="follow", example='strace -e trace=openat ls'),
    A("follow", "spider", "Follow", "follow child processes with `strace -f`", cmd=lambda c: c.flag("strace", "f"), example='strace -f bash -c ls'),
    A("summary", "spider", "Summary", "count syscalls with `strace -c`", cmd=lambda c: c.flag("strace", "c"), next="filter", example='strace -c ls'),

    # Ant: xargs
    A("placeholder", "ant", "Placeholder", "place arguments with `xargs -I{}`", cmd=lambda c: c.arg("xargs", r"^-I"), next="null", example='ls | xargs -I{} echo {}'),
    A("parallel", "ant", "Parallel", "run jobs in parallel with `xargs -P`", cmd=lambda c: c.arg("xargs", r"^-P"), example='ls | xargs -P4 -n1 echo'),
    A("null", "ant", "Null", "handle odd file names: `-print0 | xargs -0`", cmd=lambda c: c.flag("xargs", "0", ("--null",)), next="parallel", example='find . -print0 | xargs -0 ls'),

    # Axolotl: jq
    # Beaver: git
    A("brancher", "beaver", "Brancher", "start a branch with `git switch -c`",
      cmd=lambda c: c.sub("git", "switch", "-c", "-C", "--create") or c.sub("git", "checkout", "-b", "-B"), next="grapher", example='git switch -c try-it'),
    A("stasher", "beaver", "Stasher", "put work aside with `git stash`", cmd=lambda c: c.sub("git", "stash"), next="brancher", example='git stash'),
    A("grapher", "beaver", "Grapher", "draw the history with `git log --graph`", cmd=lambda c: c.sub("git", "log", "--graph"), next="bisector", example='git log --oneline --graph'),
    A("bisector", "beaver", "Bisector", "hunt the commit that broke it with `git bisect`", cmd=lambda c: c.sub("git", "bisect"), example='git bisect start'),

    # Squirrel: archives
    A("packer", "squirrel", "Packer", "pack a folder with `tar -czf`", cmd=lambda c: c.tar("c", "z") or c.tar("c", "J"), next="unpacker", example='tar -czf notes.tgz notes'),
    A("peeker", "squirrel", "Peeker", "look inside an archive with `tar -tf`", cmd=lambda c: c.tar("t"), next="packer", example='tar -tf notes.tgz'),
    A("unpacker", "squirrel", "Unpacker", "extract into a folder with `tar -xf … -C dir`",
      cmd=lambda c: c.tar("x") and c.arg("tar", r"^(-C|--directory)"), next="squeezer", example='tar -xf notes.tgz -C /tmp'),
    A("squeezer", "squirrel", "Squeezer", "compress harder with `xz` or `zstd`",
      cmd=lambda c: bool(c.args("xz", "zstd")), needs=("xz", "zstd"), example='xz -k big.log'),

    # Pigeon: network
    A("headers", "pigeon", "Headers", "see only the headers with `curl -I`", cmd=lambda c: c.flag("curl", "I", ("--head",)),
      needs=("curl",), next="poster", example='curl -I https://example.com'),
    A("poster", "pigeon", "Poster", "send data with `curl -d`",
      cmd=lambda c: c.flag("curl", "d", ("--data", "--data-raw", "--json")), needs=("curl",), example="curl -d 'a=1' https://httpbin.org/post"),
    A("tunneler", "pigeon", "Tunneler", "forward a port with `ssh -L`, or jump with `ssh -J`",
      cmd=lambda c: c.flag("ssh", "LRJ"), needs=("ssh",), example='ssh -L 8080:localhost:80 server'),
    A("mirror", "pigeon", "Mirror", "sync folders with `rsync -a`", cmd=lambda c: c.flag("rsync", "a", ("--archive",)),
      needs=("rsync",), next="tunneler", example='rsync -av notes/ backup/'),
    A("resolver", "pigeon", "Resolver", "ask DNS with `dig +short`", cmd=lambda c: c.arg("dig", r"^(\+short|@.)"),
      needs=("dig",), next="tracer", example='dig +short example.com'),
    A("tracer", "pigeon", "Tracer", "follow a name from the root with `dig +trace`", cmd=lambda c: c.arg("dig", r"^\+trace$"),
      needs=("dig",), example='dig +trace example.com'),

    # Packet: the network, from an address to a packet on the wire
    A("interfaces", "packet", "Interfaces", "list your addresses with `ip -br addr`",
      cmd=lambda c: c.sub("ip", "addr") or c.sub("ip", "a") or c.sub("ip", "address"), needs=("ip",), next="six_sense", example='ip -br addr'),
    A("six_sense", "packet", "Sixth sense", "show only your IPv6 addresses with `ip -6 addr`",
      cmd=lambda c: c.flag("ip", "6"), needs=("ip",), next="pathfinder", example='ip -6 addr'),
    A("pathfinder", "packet", "Pathfinder", "ask which way a packet would go with `ip route get 1.1.1.1`",
      cmd=lambda c: c.sub("ip", "get"), needs=("ip",), next="hops", example='ip route get 1.1.1.1'),
    A("listener", "packet", "Listener", "see who waits for connections with `ss -tlnp`",
      cmd=lambda c: c.flag("ss", "l", ("--listening",)), needs=("ss",), next="established", example='ss -tlnp'),
    A("established", "packet", "Established", "list the open connections with `ss -tn state established`",
      cmd=lambda c: c.arg("ss", r"^(established|estab)$"), needs=("ss",), next="knocker", example='ss -tn state established'),
    A("nsswitch", "packet", "Like a program", "look up a name the way programs do: `getent hosts example.org`",
      cmd=lambda c: c.sub("getent", "hosts") or c.sub("getent", "ahosts"), needs=("getent",), next="reverse", example='getent hosts example.org'),
    A("reverse", "packet", "Reverse", "find the name of an address with `dig -x 1.1.1.1`",
      cmd=lambda c: c.flag("dig", "x"), needs=("dig",), next="stub", example='dig -x 1.1.1.1'),
    A("stub", "packet", "Behind the stub", "see your real DNS servers with `resolvectl status`",
      cmd=lambda c: bool(c.args("resolvectl")), needs=("resolvectl",), example='resolvectl status'),
    A("hops", "packet", "Hops", "list the routers on the way with `tracepath` or `traceroute`",
      cmd=lambda c: bool(c.args("tracepath", "traceroute", "mtr")), needs=("tracepath", "traceroute", "mtr"), example='tracepath -n 1.1.1.1'),
    A("knocker", "packet", "Knocker", "check that a port answers with `nc -zv host 22`",
      cmd=lambda c: c.flag(("nc", "ncat", "netcat"), "z"), needs=("nc", "ncat", "netcat"), next="capture_reader", example='nc -zv localhost 22'),
    A("capture_reader", "packet", "Capture reader", "read a saved capture with `tcpdump -nn -r file.pcap`",
      cmd=lambda c: c.flag("tcpdump", "r"), needs=("tcpdump",), example='tcpdump -nn -r capture.pcap'),
    A("net_fighter", "packet", "On the wire", "win a network fight: `bashou fight`", state=lambda s: won_network(s)),

    # Hedgehog: permissions
    A("octal", "hedgehog", "Octal", "set a mode in numbers: `chmod 644`", cmd=lambda c: c.arg("chmod", r"^0?[0-7]{3}$"), next="mode_reader", example='chmod 644 notes.txt'),
    A("symbolic", "hedgehog", "Symbolic", "add or remove a right: `chmod g+w`", cmd=lambda c: c.arg("chmod", r"^[ugoa]+[-+=][rwxXst]+$"), next="owner", example='chmod g+w notes.txt'),
    A("owner", "hedgehog", "Owner", "change the owner with `chown user:group`", cmd=lambda c: c.arg("chown", r"^[\w.$-]+:[\w.$-]*$"), example='sudo chown $USER:$USER f'),
    A("mode_reader", "hedgehog", "Mode reader", "read a file's mode with `stat -c %a`", cmd=lambda c: c.arg("stat", r"%a"), next="symbolic", example='stat -c %a notes.txt'),

    # Bee: systemd
    A("status", "bee", "Status", "check a service with `systemctl status`", cmd=lambda c: c.sub("systemctl", "status"), next="logbook", example='systemctl status cron'),
    A("logbook", "bee", "Logbook", "read a service's logs with `journalctl -u`",
      cmd=lambda c: c.flag("journalctl", "u", ("--unit",)), needs=("journalctl",), next="enabler", example='journalctl -u cron'),
    A("enabler", "bee", "Enabler", "start a service now and at boot: `systemctl enable --now`",
      cmd=lambda c: c.sub("systemctl", "enable", "--now"), next="reload", example='sudo systemctl enable --now cron'),
    A("reload", "bee", "Reload", "after editing a unit file: `systemctl daemon-reload`", cmd=lambda c: c.sub("systemctl", "daemon-reload"), example='sudo systemctl daemon-reload'),

    # Whale: kubectl
    A("pods", "whale", "Pods", "list every pod with `kubectl get pods -A`", cmd=lambda c: c.sub("kubectl", "get", "-A", "--all-namespaces"), next="describer", example='kubectl get pods -A'),
    A("describer", "whale", "Describer", "see why a pod is stuck with `kubectl describe`", cmd=lambda c: c.sub("kubectl", "describe"), next="tailer", example='kubectl describe pod <name>'),
    A("tailer", "whale", "Tailer", "follow a pod's logs with `kubectl logs -f`",
      cmd=lambda c: c.sub("kubectl", "logs") and c.flag("kubectl", "f", ("--follow",)), next="diver", example='kubectl logs -f <pod>'),
    A("diver", "whale", "Diver", "open a shell in a pod with `kubectl exec -it`",
      cmd=lambda c: c.sub("kubectl", "exec") and c.flag("kubectl", "i") and c.flag("kubectl", "t"), example='kubectl exec -it <pod> -- sh'),

    # Meerkat: watching the system
    A("disk", "meerkat", "Disk", "see free space with `df -h`", cmd=lambda c: c.flag("df", "h", ("--human-readable",)), next="sizer", example='df -h'),
    A("sizer", "meerkat", "Sizer", "size a folder with `du -sh`", cmd=lambda c: c.flag("du", "s") and c.flag("du", "h"), next="memory", example='du -sh *'),
    A("memory", "meerkat", "Memory", "check the memory with `free -h`", cmd=lambda c: c.flag("free", "h"), needs=("free",), next="watcher", example='free -h'),
    A("watcher", "meerkat", "Watcher", "rerun a command every few seconds with `watch -n`",
      cmd=lambda c: c.flag("watch", "n", ("--interval",)), needs=("watch",), example='watch -n 2 df -h'),

    # Duck: debugging, like the rubber duck you explain your code to (owner: "ducks are awesome")
    A("quack", "duck", "Quack", "explain a command to your duck: `bashou learn <command>`", cmd=lambda c: c.sub("bashou", "learn"), example='bashou learn'),
    A("xray", "duck", "X-ray", "watch a script run line by line with `bash -x`", cmd=lambda c: c.flag("bash", "x"), next="linter", example='bash -x deploy.sh'),
    A("dry_run", "duck", "Dry run", "check a script's syntax without running it: `bash -n`", cmd=lambda c: c.flag("bash", "n"), next="xray", example='bash -n deploy.sh'),
    A("exit_code", "duck", "Exit code", "check how the last command ended: `echo $?`",
      cmd=lambda c: "$?" in c.line and bool(c.args("echo", "printf")), next="dry_run", example='ls /nope; echo $?'),
    A("linter", "duck", "Linter", "find bugs before they bite with `shellcheck`", cmd=lambda c: bool(c.args("shellcheck")),
      needs=("shellcheck",), example='shellcheck deploy.sh'),

    # Snow leopard: secrets (gpg, pass). Never hidden when gpg or pass is missing: the pets invite you to install them.
    A("sealed", "leopard", "Sealed", "encrypt a file with `gpg -c` (a passphrase) or `gpg -e` (a key)",
      cmd=lambda c: c.flag(("gpg", "gpg2"), "ce", ("--symmetric", "--encrypt")), next="keymaker", example='gpg -c notes.txt'),
    A("keymaker", "leopard", "Keymaker", "make your own key pair with `gpg --full-generate-key`",
      cmd=lambda c: c.arg(("gpg", "gpg2"), r"^--(full-gen|gen|quick-gen|full-generate|generate|quick-generate)-key$"), next="vault", example='gpg --full-generate-key'),
    A("vault", "leopard", "Vault", "start a password store with `pass init`", cmd=lambda c: c.sub("pass", "init"), next="generator", example='pass init <your key id>'),
    A("generator", "leopard", "Generator", "let `pass generate` make a strong password", cmd=lambda c: c.sub("pass", "generate"), next="keeper", example='pass generate web/forum 24'),
    A("keeper", "leopard", "Keeper", "hand a password to a command with `$(pass show …)`, never in clear",
      cmd=lambda c: c.sub("pass", "show") and "subst" in c.analysis.constructs, example='curl -u "admin:$(pass show web/admin)" https://example.org'),  # gitleaks:allow (reads it from pass)

    # Spark: the Sage Owl's library. Owner: fire, for the Library of Alexandria that burned, and for the books
    # still destroyed today; what you learn, nobody can burn. Ten forms, the Phoenix when the family is complete.
    # Counts stop at what your skills offer: a player who learns only Rust can still reach the Phoenix.
    A("kindling", "spark", "Kindling", "read a lesson to the end: `bashou lesson`", state=lambda s: read_at_least(s, 1), next="page_turner"),
    A("page_turner", "spark", "Page turner", "read 3 lessons to the end", state=lambda s: read_at_least(s, 3), next="bookworm"),
    A("mastery", "spark", "Mastery", "master a lesson you read: do the fights and achievements it prepares",
      state=lambda s: mastered_at_least(s, 1), next="librarian"),
    A("bookworm", "spark", "Bookworm", "read 6 lessons to the end", state=lambda s: read_at_least(s, 6), next="lesson_scholar"),
    A("polymath", "spark", "Polymath", "read lessons of 3 different skills",
      state=lambda s: len({first_skill(le) for le in lessons_read(s)}) >= min(3, len(skills_offered(s)))),
    A("librarian", "spark", "Librarian", "master 5 lessons you read", state=lambda s: mastered_at_least(s, 5), next="torchbearer"),
    A("lesson_scholar", "spark", "Scholar", "read 12 lessons to the end", state=lambda s: read_at_least(s, 12), next="well_read"),
    A("torchbearer", "spark", "Torchbearer", "master 10 lessons you read", state=lambda s: mastered_at_least(s, 10)),
    A("well_read", "spark", "Well read", "read 20 lessons to the end", state=lambda s: read_at_least(s, 20), next="alexandria"),
    A("alexandria", "spark", "Alexandria", "read every lesson of the skills you learn",
      state=lambda s: all_lessons_read(s)),

    A("raw", "axolotl", "Raw", "print raw strings with `jq -r`", cmd=lambda c: c.flag("jq", "r", ("--raw-output",)), next="selector", example="jq -r '.name' f.json"),
    A("selector", "axolotl", "Selector", "filter with `select()`", cmd=lambda c: c.arg("jq", r"select\("), next="mapper", example="jq '.[] | select(.ok)' f.json"),
    A("mapper", "axolotl", "Mapper", "transform arrays with `map()`", cmd=lambda c: c.arg("jq", r"map\("), example="jq 'map(.id)' f.json"),
]

for _i, (_n, _id, _name) in enumerate(STEP_MILESTONES):
    ALL.append(A(_id, "landscape", _name, ("finish a step of a project: `bashou project`" if _n == 1 else
                                           "finish {n} steps of projects".replace("{n}", str(_n))),
                 state=lambda s, n=_n: steps_done(s) >= n,
                 next=STEP_MILESTONES[_i + 1][1] if _i + 1 < len(STEP_MILESTONES) else ""))
for _pid, _id, _name, _how in PROJECT_ACHIEVEMENTS:
    ALL.append(A(_id, "landscape", _name, _how, state=lambda s, pid=_pid: project_done(s, pid)))
for _lang, _id, _name, _how in LANGUAGE_ACHIEVEMENTS:
    ALL.append(A(_id, "landscape", _name, _how, state=lambda s, lang=_lang: bool(projects_done(s, lang))))
ALL += [A("climber", "landscape", "Climber", "finish a medium project", state=lambda s: bool(projects_done(s, difficulty="medium"))),
        A("summit", "landscape", "Summit", "finish a hard project", state=lambda s: bool(projects_done(s, difficulty="hard"))),
        A("steady_builder", "landscape", "Steady builder", "finish project steps 7 days in a row",
          state=lambda s: project_streak(s) >= 7)]

# Secret achievements: security tools. Nothing announces them; they just pop up, and the first one
# brings a pet that isn't on the board ("secret" in its family file).
def _uses(*names):
    tools = set(names)
    return lambda c: bool(c.analysis.tools & tools)


SECRET = [
    A("exploiter", "cat", "Exploiter", "run Metasploit", hidden=True,
      cmd=_uses("msfconsole", "msfvenom", "msfdb", "searchsploit", "msfrpcd")),
    A("auditor", "cat", "Auditor", "audit a machine with `lynis`", hidden=True, cmd=_uses("lynis", "chkrootkit", "rkhunter")),
    A("sniffer", "cat", "Sniffer", "watch packets go by", hidden=True, cmd=_uses("wireshark", "tshark", "tcpdump", "termshark")),
    A("cracker", "cat", "Cracker", "try passwords with John or hashcat", hidden=True,
      cmd=_uses("john", "hashcat", "johnny", "zip2john", "ssh2john", "hashid")),
    A("reverser", "cat", "Reverser", "take a binary apart", hidden=True,
      cmd=_uses("ghidra", "ghidraRun", "radare2", "r2", "rizin", "jadx", "retdec-decompiler", "ida", "cutter",
                "apktool", "dnSpy")),
    A("net_mapper", "cat", "Mapper", "scan a network with `nmap`", hidden=True, cmd=_uses("nmap", "masscan", "zmap", "rustscan")),
    A("web_scanner", "cat", "Web scanner", "scan a site with `nikto`", hidden=True,
      cmd=_uses("nikto", "wpscan", "nuclei", "whatweb", "zaproxy")),
    A("wardriver", "cat", "Wardriver", "listen to Wi-Fi with the aircrack suite", hidden=True,
      cmd=_uses("aircrack-ng", "airodump-ng", "aireplay-ng", "airmon-ng", "wifite", "kismet", "reaver")),
    A("interceptor", "cat", "Interceptor", "sit in the middle of the traffic", hidden=True,
      cmd=_uses("burpsuite", "mitmproxy", "mitmdump", "bettercap", "ettercap", "responder")),
    A("injector", "cat", "Injector", "test injections with `sqlmap`", hidden=True, cmd=_uses("sqlmap", "commix")),
    A("bruteforcer", "cat", "Bruteforcer", "knock on every door", hidden=True,
      cmd=_uses("hydra", "medusa", "patator", "crackmapexec", "netexec", "nxc")),
    A("buster", "cat", "Buster", "look for hidden paths", hidden=True,
      cmd=_uses("gobuster", "ffuf", "dirb", "dirbuster", "feroxbuster", "wfuzz")),
    A("forensic", "cat", "Forensic", "dig into a dump or a firmware", hidden=True,
      cmd=_uses("volatility", "volatility3", "vol.py", "binwalk", "autopsy", "foremost", "testdisk")),
]
ALL += SECRET

for _a in ALL:                                   # a family's commands: in its file ("achievement_needs")
    _a.needs = _a.needs or creatures.FAMILIES[_a.pet].achievement_needs

BY_ID = {a.id: a for a in ALL}


def chain_problems():
    """What's wrong with the `next` links: an unknown id, another pet's, a loop, two leading to one."""
    found, led = [], {}
    for a in ALL:
        if a.next and (a.next not in BY_ID or BY_ID[a.next].pet != a.pet):
            found.append(f"{a.id}: next {a.next!r} isn't one of the {a.pet}'s")
        elif a.next:
            if a.next in led:
                found.append(f"{a.next}: both {led[a.next]} and {a.id} lead to it")
            led[a.next] = a.id
    for a in ALL:
        seen, b = set(), a
        while b.next in BY_ID and b.id not in seen:
            seen.add(b.id)
            b = BY_ID[b.next]
        if b.id in seen:
            found.append(f"{a.id}: its chain loops")
    return found


def _depths():
    for a in ALL:
        if a.next in BY_ID and a.id not in {b.next for b in ALL}:          # the start of a chain
            depth, b = 1, a
            while b.next in BY_ID and depth <= len(ALL):
                depth += 1
                b = BY_ID[b.next]
                b.depth = depth


_depths()
PREV = {a.next: a for a in ALL if a.next}           # the achievement that leads to this one




def adv(state):
    return state.get("adventure") or {}


def family(pet):
    """The pet's achievements this system can earn."""
    return [a for a in ALL if a.pet == pet and a.available()]


def usable():
    """Every achievement this system can earn and show: the secret ones don't count."""
    return [a for a in ALL if a.available() and not a.hidden]


def secrets(state):
    """The secret achievements found so far."""
    ids = set(state["achievements"])
    return [a for a in ALL if a.hidden and a.id in ids]


def earned(state):
    """Earned achievements this system can still earn (counted against `usable()`)."""
    ids = set(state["achievements"])
    return [a for a in usable() if a.id in ids]
