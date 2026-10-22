"""Script fights (skill `script`, owner 2026-10-22): each hands you a script built on the template
(template.sh), with one habit that is fine at the prompt and a bug in a script. The bug only bites on
real-life input: a name with a dash or a newline, a folder with no match, a failing command. `verify` runs
your script again in a fresh folder, on its own tricky input, so only a real fix wins: doing the job by
hand doesn't."""

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import Challenge
from .repos import EDITORS
from .trials import trial
from ..i18n import _


def script(name, what, usage, body, top="", head=""):
    """A script on the template: what it does, its usage line, `head` under the comments (set -e),
    `top` before main (functions, globals), `body` inside main after the argument check."""
    return (f"#!/usr/bin/env bash\n# {what}\n# Usage: {name} {usage}\n\n{head}"
            "die() { printf '%s: %s\\n' \"${0##*/}\" \"$*\" >&2; exit 1; }\n\n" + top +
            "main() {\n  if (( $# " + ("< 1" if usage.endswith("...") else "!= 1") + " )); then\n    printf 'usage: %s " + usage + "\\n' \"${0##*/}\" >&2\n"
            "    exit 2\n  fi\n" + body + "}\n\nmain \"$@\"\n")


def write(work, name, text):
    path = work / name
    path.write_text(text)
    path.chmod(0o755)


def tries(work, name, cases, env=None):
    """Run the player's script (a copy) in a fresh folder per case: `build(box)` fills it, `judge(box, done)`
    says what went wrong ("" when right). The first problem found, or ""."""
    if not (work / name).is_file():
        return _("{script} is gone: the fight needs it.").format(script=name)
    for build, args, judge in cases:
        with tempfile.TemporaryDirectory(prefix="bashou-check-") as tmp:
            box = Path(tmp)
            shutil.copy(work / name, box / name)
            build(box)
            run_env = dict(os.environ, **(env(box) if env else {}))
            try:
                done = subprocess.run(["bash", name, *args], cwd=box, stdin=subprocess.DEVNULL, capture_output=True,
                                      text=True, timeout=10, env=run_env)
            except subprocess.TimeoutExpired:
                return _("{script} didn't finish within 10 seconds.").format(script=name)
            problem = judge(box, done)
            if problem:
                return problem
    return ""


def fight(id, pet, name, level, cases, env=None, **kw):
    """A script fight on `name`: verify and why run `cases` (see tries)."""
    def check(work):
        return tries(work, name, cases(), env)
    return Challenge(id=id, pet=pet, tools=("bash",) + EDITORS, requires=["bash"], level=level, skill="script",
                     fix=True, file=name, verify=lambda work, meta, value: not check(work),
                     why=lambda work: check(work) or None,
                     uses=lambda a: any(name in n or any(name in w for w in args) for n, args in a.commands), **kw)


def said(done):
    """What the script printed, both outputs, for a message."""
    text = (done.stdout + done.stderr).strip()
    return text[-300:] if text else _("(nothing)")


def files(folder, names, text=lambda n: f"{n}\n"):
    folder.mkdir(parents=True, exist_ok=True)
    for n in names:
        (folder / n).write_text(text(n))


# --- Dash Demon: a name that starts with a dash is read as options (lesson script_files) -----------------

TIDY = script("tidy.sh", "Moves every .tmp file of a folder into its trash/ folder.", "FOLDER", """\
  local dir=$1 f
  [[ -d $dir ]] || die "not a folder: $dir"
  cd -- "$dir" || die "cannot enter $dir"
  mkdir -p trash || die "cannot create $dir/trash"
  for f in *.tmp; do
    mv "$f" trash/ || die "cannot move $f"
  done
""")
DASHED = ["-n.tmp", "-f old.tmp", "plain.tmp", "my notes.tmp"]


def tidy_setup(work, rng):
    write(work, "tidy.sh", TIDY)
    files(work / "inbox", ["draft.tmp", rng.choice(["-n.tmp", "-f.tmp", "-i.tmp"]), "cache.tmp", "keep.txt"])
    return {}


def tidy_cases():
    def judge(box, done):
        left = sorted(p.name for p in (box / "box").glob("*.tmp"))
        moved = sorted(p.name for p in (box / "box" / "trash").glob("*")) if (box / "box" / "trash").is_dir() else []
        if done.returncode or left or moved != sorted(DASHED) or not (box / "box" / "keep.txt").is_file():
            return _("On a folder holding {names}, tidy.sh left {left} and said: {said}").format(
                names=", ".join(repr(n) for n in DASHED), left=", ".join(repr(n) for n in left) or _("nothing"),
                said=said(done))
        return ""
    return [(lambda box: files(box / "box", DASHED + ["keep.txt"]), ["box"], judge)]


DASH_DEMON = fight(
    "dash_demon", "hedgehog", "tidy.sh", 2, tidy_cases, threat="Dash Demon", setup=tidy_setup, after=("shebang_shade",),
    task="The Dash Demon hid in inbox/ as a file whose name starts with a dash. tidy.sh moves the .tmp files of a "
         "folder into its trash/, but ./tidy.sh inbox stops on that one.\nFix tidy.sh so it moves every .tmp "
         "file, whatever its name. Then: verify (Bashou runs your tidy.sh on a folder of its own).",
    help="Here, --help won't help: the bug is in the script. Look at the lesson Files in scripts (bashou lesson "
         "script_files).",
    hints=["Run it and read the error: mv says invalid option. The name starts with a dash, so mv takes it for "
           "options, like -n. At the prompt you would see it and type the name another way; a script must "
           "handle it every time.",
           "-- tells a command that no option comes after it: mv -- \"$f\" trash/. Starting the pattern with ./ "
           "works too: for f in ./*.tmp gives ./-n.tmp, which is no option."],
)


# --- Nomatch Nymph: a pattern that matches nothing stays the pattern (lesson script_files) ---------------

COUNT = script("count.sh", "Says how many .jpg photos a folder holds.", "FOLDER", """\
  local dir=$1 f n=0
  [[ -d $dir ]] || die "not a folder: $dir"
  for f in "$dir"/*.jpg; do
    n=$((n + 1))
  done
  printf '%s photos\\n' "$n"
""")


def count_setup(work, rng):
    write(work, "count.sh", COUNT)
    files(work / "albums" / "summer", [f"{n}.jpg" for n in rng.sample(["beach", "boat", "sun", "sand cat"], 3)])
    (work / "albums" / "winter").mkdir(parents=True)
    return {}


def count_cases():
    def expect(n):
        def judge(box, done):
            if done.returncode or done.stdout != f"{n} photos\n":
                return _("On a folder with {n} .jpg, count.sh said: {said}").format(n=n, said=said(done))
            return ""
        return judge
    return [(lambda box: (box / "empty").mkdir(), ["empty"], expect(0)),
            (lambda box: files(box / "pics", ["notes.txt", "map.png"]), ["pics"], expect(0)),
            (lambda box: files(box / "pics", ["a.jpg", "my cat.jpg", "new\nline.jpg", "old.jpg\nnotes.txt", "b.png"]), ["pics"], expect(3))]


NOMATCH_NYMPH = fight(
    "nomatch_nymph", "ghost", "count.sh", 2, count_cases, threat="Nomatch Nymph", setup=count_setup, after=("shebang_shade",),
    task="The Nomatch Nymph counts photos that aren't there: ./count.sh albums/winter says 1 photos, and winter is "
         "empty.\nFix count.sh so an empty folder gives 0 photos. Then: verify (Bashou runs your count.sh on "
         "folders of its own).",
    help="Here, --help won't help: the bug is in the script. Look at the lesson Files in scripts (bashou lesson "
         "script_files).",
    hints=["Put echo \"$f\" inside the loop and run it on winter: f is albums/winter/*.jpg, the pattern itself. "
           "When nothing matches, bash keeps the pattern as it is, and the loop turns once.",
           "Skip what doesn't exist: [[ -e $f ]] || continue as the first line inside the loop. Or turn on "
           "shopt -s nullglob before the loop: a pattern that matches nothing then gives nothing."],
)


# --- Newline Nixie: names read from ls are cut at spaces and newlines (lesson script_files) --------------

SIZE = script("size.sh", "Adds up the size of the files in a folder, in bytes.", "FOLDER", """\
  local dir=$1 f total=0
  [[ -d $dir ]] || die "not a folder: $dir"
  for f in $(ls "$dir"); do
    total=$((total + $(wc -c < "$dir/$f")))
  done
  printf '%s bytes\\n' "$total"
""")
ODD = {"a.txt": "hello\n", "my notes.txt": "a longer line of notes\n", "new\nline.txt": "x\n"}


def size_setup(work, rng):
    write(work, "size.sh", SIZE)
    box = work / "reports"
    box.mkdir()
    for name in ("q1.txt", rng.choice(["q2 final.txt", "q2 (old).txt", "q2 draft v2.txt"]), "q3.txt"):
        (box / name).write_text(f"report {name}\n" * rng.randint(2, 6))
    return {}


def size_cases():
    def build(box):
        (box / "box" / "sub").mkdir(parents=True)
        for name, text in ODD.items():
            (box / "box" / name).write_text(text)
        (box / "box" / "sub" / "inside.txt").write_text("not counted\n")

    def judge(box, done):
        total = sum(len(t.encode()) for t in ODD.values())
        if done.returncode or done.stdout != f"{total} bytes\n":
            return _("On a folder of {n} files ({names}), {total} bytes in all, size.sh said: {said}").format(
                n=len(ODD), names=", ".join(repr(n) for n in ODD), total=total, said=said(done))
        return ""
    return [(build, ["box"], judge)]


NEWLINE_NIXIE = fight(
    "newline_nixie", "snail", "size.sh", 2, size_cases, threat="Newline Nixie", setup=size_setup, after=("shebang_shade",),
    task="The Newline Nixie writes file names with spaces, and even with a line break inside. size.sh adds up the "
         "bytes of a folder's files, but ./size.sh reports fails on one of them.\nFix size.sh so every name "
         "counts. Then: verify (Bashou runs your size.sh on a folder of its own).",
    help="Here, --help won't help: the bug is in the script. Look at the lesson Files in scripts (bashou lesson "
         "script_files).",
    hints=["✘ $(ls \"$dir\") turns the names into text, and the shell cuts that text at every space and line break: "
           "q2 final.txt becomes q2 and final.txt. ls is for your eyes, at the prompt.",
           "Let the shell give the names themselves: for f in \"$dir\"/*; do, then [[ -f $f ]] || continue to "
           "skip folders, and wc -c < \"$f\" (f already holds the folder)."],
)


# --- Stdin Siren: a command inside a read loop eats the loop's input (lesson script_files) ---------------

REMOTE = """#!/usr/bin/env bash
# A pretend ssh, for this fight: remote HOST CMD answers for HOST. Like ssh, it reads its standard input
# to pass it on to the command over there.
cat > /dev/null
printf '%s: up\\n' "$1"
"""
CHECK = script("check.sh", "Asks each server of a list (one per line) if it's up.", "LIST", """\
  local list=$1 host
  [[ -r $list ]] || die "cannot read $list"
  while IFS= read -r host; do
    ./remote "$host" uptime
  done < "$list"
""")
HOSTS = ["web1", "web2", "db1", "cache", "backup"]


def check_setup(work, rng):
    write(work, "check.sh", CHECK)
    write(work, "remote", REMOTE)
    (work / "servers.txt").write_text("".join(f"{h}\n" for h in rng.sample(HOSTS, 4)))
    return {}


def check_cases():
    def build(box):
        write(box, "remote", REMOTE)                     # ours: the fix belongs in check.sh
        (box / "hosts.txt").write_text("".join(f"{h}\n" for h in HOSTS))

    def judge(box, done):
        if done.returncode or done.stdout.splitlines() != [f"{h}: up" for h in HOSTS]:
            return _("With {n} servers in the list, check.sh said: {said}").format(n=len(HOSTS), said=said(done))
        return ""
    return [(build, ["hosts.txt"], judge)]


STDIN_SIREN = fight(
    "stdin_siren", "octopus", "check.sh", 3, check_cases, threat="Stdin Siren", setup=check_setup, after=("nomatch_nymph",),
    task="The Stdin Siren sings to the commands inside a loop. check.sh asks each server of a list if it's up, with "
         "./remote (a pretend ssh), but ./check.sh servers.txt only asks the first one.\nFix check.sh so it "
         "asks them all. Then: verify (Bashou runs your check.sh with its own list).",
    help="Here, --help won't help: the bug is in the script. Look at the lesson Files in scripts (bashou lesson "
         "script_files).",
    hints=["Every command inside the while loop reads from the same place as read: the list. remote, like ssh, "
           "reads all it can from its input to pass it on, so it swallows the rest of the list after the first "
           "server.",
           "Give remote nothing to read: ./remote \"$host\" uptime < /dev/null (with a real ssh: ssh -n does the "
           "same)."],
)


# --- Masked Mole: local x=$(cmd) hides the failure of cmd (lesson script_errors) -----------------------

STAMP = script("stamp.sh", "Writes the checksum of each file into FILE.sum.", "FILE...", """\
  local f
  for f in "$@"; do
    stamp "$f"
  done
""", top="""\
stamp() {
  local sum=$(cksum < "$1") || die "cannot read $1"
  printf '%s\\n' "$sum" > "$1.sum"
}

""")


def stamp_setup(work, rng):
    write(work, "stamp.sh", STAMP)
    for name in rng.sample(["notes.txt", "plan.txt", "todo.txt", "list.txt"], 2):
        (work / name).write_text(f"{name}\n")
    return {}


def stamp_cases():
    def build(box):
        (box / "notes.txt").write_text("some notes\n")

    def good(box, done):
        want = subprocess.run(["cksum"], input="some notes\n", capture_output=True, text=True).stdout
        got = (box / "notes.txt.sum").read_text() if (box / "notes.txt.sum").is_file() else ""
        if done.returncode or got != want:
            return _("On a file that exists, stamp.sh said: {said}").format(said=said(done))
        return ""

    def missing(box, done):
        if done.returncode == 0 or (box / "gone.txt.sum").exists():
            return _("On a file that doesn't exist, stamp.sh ended with status {status} and {wrote}. It should stop "
                     "with an error instead.").format(
                status=done.returncode,
                wrote=_("wrote gone.txt.sum") if (box / "gone.txt.sum").exists() else _("wrote nothing"))
        if re.search(r"^\s*(?:local|declare|typeset|export|readonly)\b[^;&|#\n]*?\w=[^;&|\n]*?\$\((?!\()",
                     (box / "stamp.sh").read_text(), re.M):
            return _("stamp.sh stops now, but a local x=$(…) (or declare, export, readonly) is still there: || sees "
                     "that command's status, not the one inside $( ), so it hides the next failure. Declare first, "
                     "assign on the next line.")
        return ""
    return [(build, ["notes.txt"], good), (build, ["notes.txt", "gone.txt"], missing)]


MASKED_MOLE = fight(
    "masked_mole", "mole", "stamp.sh", 2, stamp_cases, threat="Masked Mole", setup=stamp_setup, after=("shebang_shade",),
    task="The Masked Mole hides failures behind a mask. stamp.sh writes each file's checksum into FILE.sum and "
         "should stop when a file can't be read, but ./stamp.sh nothing.txt ends as if all went well, and leaves "
         "an empty nothing.txt.sum.\nFix stamp.sh so a missing file stops it with an error. Then: verify.",
    help="Here, --help won't help: the bug is in the script. Look at the lesson Errors in scripts (bashou lesson "
         "script_errors).",
    hints=["cksum fails on the missing file, and || die should catch it. But on that line the status || sees is "
           "local's, not cksum's: local is a command too, it always works, and its status (0) "
           "replaces cksum's.",
           "Declare first, assign on the next line: local sum, then sum=$(cksum < \"$1\") || die \"cannot read "
           "$1\". Now || sees cksum's status."],
)


# --- Errexit Eel: set -e stops at ((count++)) when count is 0 (lesson script_errors) -------------------

ERRORS = script("errors.sh", "Counts the ERROR lines of a log.", "LOG", """\
  local log=$1 line count=0
  [[ -r $log ]] || die "cannot read $log"
  while IFS= read -r line; do
    if [[ $line == ERROR* ]]; then
      ((count++))
    fi
  done < "$log"
  printf 'ERROR lines: %s\\n' "$count"
""", head="set -e\n\n")


def errors_setup(work, rng):
    write(work, "errors.sh", ERRORS)
    lines = ["INFO start"] + ["ERROR disk full"] * rng.randint(2, 4) + ["INFO save", "WARN slow"]
    rng.shuffle(lines)
    (work / "app.log").write_text("\n".join(lines) + "\n")
    return {}


def errors_cases():
    def expect(n):
        def judge(box, done):
            if done.returncode or done.stdout != f"ERROR lines: {n}\n":
                return _("On a log with {n} ERROR lines, errors.sh ended with status {status} and said: {said}").format(
                    n=n, status=done.returncode, said=said(done))
            return ""
        return judge

    def log(lines):
        return lambda box: (box / "app.log").write_text("".join(f"{x}\n" for x in lines))
    return [(log(["INFO a", "ERROR b", "ERROR c", "INFO d", "ERROR e"]), ["app.log"], expect(3)),
            (log(["INFO a", "INFO b"]), ["app.log"], expect(0)),
            (log(["ERROR only"]), ["app.log"], expect(1))]


ERREXIT_EEL = fight(
    "errexit_eel", "snake", "errors.sh", 2, errors_cases, threat="Errexit Eel", setup=errors_setup, after=("masked_mole",),
    task="The Errexit Eel bites scripts that trust set -e. errors.sh counts the ERROR lines of a log, but "
         "./errors.sh app.log prints nothing at all, and ends with status 1.\nFix errors.sh so it prints the "
         "count. Then: verify (Bashou runs your errors.sh on logs of its own).",
    help="Here, --help won't help: the bug is in the script. Look at the lesson Errors in scripts (bashou lesson "
         "script_errors).",
    hints=["set -e stops the script at the first command that fails. Run bash -x errors.sh app.log: it stops "
           "right after ((count++)). (( )) answers like a test: 0 is false, so it 'fails'. And count++ gives the "
           "old value, 0, the first time.",
           "Count in a way that never fails: count=$((count + 1)). Or keep set -e out of this script: then check "
           "the commands that matter yourself, with || die."],
)


# --- Echo Echidna: echo reads data like -n as its options (lesson script_data) --------------------------

NAMES = script("names.sh", "Copies the names of a list that aren't empty into LIST.ok.", "LIST", """\
  local list=$1 name
  [[ -r $list ]] || die "cannot read $list"
  while IFS= read -r name; do
    [[ -n $name ]] || continue
    echo "$name"
  done < "$list" > "$list.ok"
""")
GUESTS = ["Ana", "-n", "", "Zoé", "-e", "-E", "back\\slash", "50%", "", "Sam"]   # 50%: data never goes in the format


def names_setup(work, rng):
    write(work, "names.sh", NAMES)
    guests = ["Ana", "Sam", "Léa", "Omar", "Yu"]
    rng.shuffle(guests)
    guests.insert(rng.randint(1, 4), "-n")
    guests.insert(2, "")
    (work / "guests.txt").write_text("\n".join(guests) + "\n")
    return {}


def names_cases():
    def judge(box, done):
        want = [g for g in GUESTS if g]
        out = box / "list.txt.ok"
        got = out.read_text().split("\n")[:-1] if out.is_file() else []
        if done.returncode or got != want:
            return _("From the names {want}, names.sh wrote {got}.").format(
                want=", ".join(repr(g) for g in want), got=", ".join(repr(g) for g in got) or _("nothing"))
        return ""
    return [(lambda box: (box / "list.txt").write_text("\n".join(GUESTS) + "\n"), ["list.txt"], judge)]


ECHO_ECHIDNA = fight(
    "echo_echidna", "hedgehog", "names.sh", 2, names_cases, threat="Echo Echidna", setup=names_setup, after=("shebang_shade",),
    task="The Echo Echidna eats a guest called -n. names.sh copies the names of a list into LIST.ok, skipping the "
         "empty lines, but after ./names.sh guests.txt, guests.txt.ok misses a name, and two names share a "
         "line.\nFix names.sh so every name comes out as it went in. Then: verify (Bashou runs your names.sh "
         "on a list of its own).",
    help="Here, --help won't help: the bug is in the script. Look at the lesson Data in scripts (bashou lesson "
         "script_data).",
    hints=["echo reads its first word as an option when it looks like one: echo \"-n\" is echo with the option "
           "-n (no newline) and nothing to print. The data was taken for an option.",
           "printf never takes its values for options: printf '%s\\n' \"$name\" prints the name as it is, then "
           "a newline. The format comes first, the data after."],
)


# --- Trap Troll: a temp file left behind, with a name anyone can guess (lesson script_cleanup) ----------

FIXED_TMP = Path("/", "tmp", "bashou-report.tmp")   # the guessable name the fight teaches against; tests clean it
REPORT = script("report.sh", "Writes the 3 most frequent lines of a log into LOG.top.", "LOG", """\
  local log=$1
  [[ -r $log ]] || die "cannot read $log"
  sort -- "$log" > "$tmp" || die "cannot sort $log"
  [[ -s $tmp ]] || die "$log is empty"
  uniq -c < "$tmp" | sort -rn | head -n 3 > "$log.top"
  rm -f -- "$tmp"
""", top="tmp=/tmp/bashou-report.tmp\n\n")


def report_setup(work, rng):
    write(work, "report.sh", REPORT)
    ips = [f"10.0.0.{rng.randint(2, 99)}" for _ in range(4)]
    (work / "access.log").write_text("".join(f"{ip}\n" for ip in rng.choices(ips, k=12)))
    (work / "empty.log").write_text("")
    return {}


def report_cases():
    def forget():
        try:
            if FIXED_TMP.is_file() and FIXED_TMP.stat().st_uid == os.getuid():
                FIXED_TMP.unlink()
        except OSError:
            pass

    def build(text):
        def go(box):
            forget()
            (box / "tmp").mkdir()
            (box / "app.log").write_text(text)
        return go

    def left(box):
        return sorted(p.name for p in (box / "tmp").iterdir()) + ([str(FIXED_TMP)] if FIXED_TMP.exists() else [])

    def failing(box, done):
        junk = left(box)
        forget()
        if done.returncode == 0:
            return _("On an empty log, report.sh should stop with an error: it ended with status 0.")
        if junk:
            return _("On an empty log, report.sh stopped (good) but left {junk} behind.").format(junk=", ".join(junk))
        return ""

    def working(box, done):
        junk = left(box)
        forget()
        top = (box / "app.log.top").read_text().split() if (box / "app.log.top").is_file() else []
        if done.returncode or top[:2] != ["3", "b"]:
            return _("On a log where b comes 3 times, report.sh said: {said}").format(said=said(done))
        if junk:
            return _("report.sh worked but left {junk} behind.").format(junk=", ".join(junk))
        text = (box / "report.sh").read_text()
        if "mktemp" not in text:
            return _("No leftovers this time, but the temp file still has a name anyone can guess: make it with "
                     "mktemp.")
        if not re.search(r"\btrap\b.*\bEXIT\b", text):
            return _("No leftovers this time, but only because every exit has its own rm: the next die someone adds "
                     "will forget it. One trap … EXIT removes the file however the script ends.")
        return ""
    return [(build(""), ["app.log"], failing), (build("a\nb\nb\nc\nb\n"), ["app.log"], working)]


TRAP_TROLL = fight(
    "trap_troll", "beaver", "report.sh", 3, report_cases, env=lambda box: {"TMPDIR": str(box / "tmp")},
    threat="Trap Troll", setup=report_setup, after=("masked_mole",),
    task="The Trap Troll lives on the files scripts forget. report.sh keeps the 3 most frequent lines of a log, "
         "with a temp file in /tmp. ./report.sh empty.log stops with an error, as it should, and leaves "
         "/tmp/bashou-report.tmp behind. And that fixed name is one any other user can create first.\nFix "
         "report.sh: a temp file of its own, removed however the script ends. Then: verify.",
    help="Here, --help won't help: the bug is in the script. Look at the lesson Cleaning up (bashou lesson "
         "script_cleanup).",
    hints=["die stops the script before the rm -f on the last line: an rm at the end only runs when all went "
           "well. And /tmp is shared: a name known in advance can be taken, or turned into a link to one of "
           "your files, by another user.",
           "At the top, replace the fixed name: tmp=$(mktemp) || exit 1, then trap 'rm -f -- \"$tmp\"' EXIT on "
           "the next line. mktemp makes a new private file; the trap removes it at every exit, die included."],
)

ALL = [DASH_DEMON, NOMATCH_NYMPH, NEWLINE_NIXIE, STDIN_SIREN, MASKED_MOLE, ERREXIT_EEL, ECHO_ECHIDNA, TRAP_TROLL]


# --- the chests after the road lessons "Scripts that fail well" and "Names that bite" -------------------

SAVE = script("save.sh", "Copies a file into backup/.", "FILE", """\
  mkdir -p backup || die "cannot create backup/"
  cp -- "$1" backup/
  printf 'saved %s\\n' "$1"
""")


def save_setup(work, rng):
    write(work, "save.sh", SAVE)
    (work / "notes.txt").write_text("notes\n")
    return {}


def save_cases():
    def judge(box, done):
        if done.returncode == 0 or "saved" in done.stdout:
            return _("On a file that doesn't exist, save.sh ended with status {status} and said: {said}").format(
                status=done.returncode, said=said(done))
        return ""
    return [(lambda box: None, ["gone.txt"], judge)]


SAVE_CHEST = trial(
    "trial_failing_copy", 2, "save.sh copies a file into backup/ and says saved. ./save.sh gone.txt says saved too, "
    "and gone.txt doesn't exist. Make save.sh stop with an error when cp fails. Then: verify",
    ["cp fails, prints its error, and the script goes on to the next line. A script doesn't stop by itself: it "
     "has to check.",
     "Add || die \"cannot copy $1\" at the end of the cp line."],
    save_setup, lambda work, meta, value: not tries(work, "save.sh", save_cases()), requires=["bash", "cp"],
    teaches=["||"], why=lambda work: tries(work, "save.sh", save_cases()) or None, file="save.sh")


def dash_setup(work, rng):
    (work / "-n").write_text("")
    return {}


DASH_CHEST = trial(
    "trial_dash_name", 1, "A file here is called -n. Write its name into name.txt, exactly, with printf. Then: verify",
    ["echo -n prints nothing: echo takes -n for its option. printf never takes its values for options.",
     "Try: printf '%s\\n' -n > name.txt"],
    dash_setup, lambda work, meta, value: (work / "name.txt").is_file() and (work / "name.txt").read_text() == "-n\n",
    requires=["bash"], teaches=["printf"])

CHESTS = [SAVE_CHEST, DASH_CHEST]
