"""Shell fights: the two output streams, quotes around names with spaces, the first line of a script,
a loop over files, and a first regular expression."""

import stat
import subprocess

from . import Challenge
from .repos import EDITORS
from .trials import trial

ROOMS = ("attic", "cellar", "garage", "kitchen", "library", "loft", "porch", "shed", "studio", "vault")


def runs(work, *cmd):
    try:
        return subprocess.run(list(cmd), cwd=work, capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None


# --- Stderr Stalker: keep only the errors, with 2> -----------------------------------------------------

NOISY = """#!/bin/bash
# Checks every room: what's fine goes to the screen (stdout), what's wrong to the errors (stderr).
{lines}
"""


def noisy_setup(work, rng):
    rooms = rng.sample(ROOMS, 7)
    broken = sorted(rng.sample(rooms, 3), key=rooms.index)
    lines = [f"echo 'error: {r} is locked' >&2" if r in broken else f"echo 'ok: {r}'" for r in rooms]
    script = work / "check.sh"
    script.write_text(NOISY.format(lines="\n".join(lines)))
    script.chmod(0o755)
    return {"errors": [f"error: {r} is locked" for r in broken]}


def noisy_verify(work, meta, value):
    """errors.txt holds the error lines, all of them, and nothing else."""
    path = work / "errors.txt"
    return path.is_file() and path.read_text().split("\n")[:-1] == meta["errors"]


STDERR_STALKER = Challenge(
    level=1, id="stderr_stalker", pet="octopus", tools=("bash",), threat="Stderr Stalker", requires=["bash"],
    fix=True, uses=lambda a: any("check.sh" in name or any("check.sh" in w for w in args) for name, args in a.commands),
    task="The Stderr Stalker hides among the messages of check.sh: some lines say ok, some say error.\nRun "
         "check.sh and save only the error lines into errors.txt. Then: verify",
    help="Here, --help won't help: the answer is in bash itself. Look at the lesson Streams (bashou lesson).",
    hints=["A program has two outputs: stdout (1) for normal results, stderr (2) for errors. Both show on the "
           "screen, which is why they look the same. > sends stdout into a file; 2> sends stderr. Try "
           "./check.sh > /dev/null: only the errors stay on the screen.",
           "Try: ./check.sh 2> errors.txt (the ok lines still show, the errors go into the file). "
           "cat errors.txt to check."],
    setup=noisy_setup, verify=noisy_verify,
)


# --- Space Sprite: a name with a space needs quotes ----------------------------------------------------

def spaced_setup(work, rng):
    first, second = rng.choice([("my", "notes.txt"), ("old", "photos.txt"), ("todo", "list.txt"),
                                ("tax", "2025.txt")])
    name = f"{first} {second}"
    (work / name).write_text("the real one\n")
    (work / first).write_text("a decoy\n")
    (work / second).write_text("another decoy\n")
    (work / "backup").mkdir()
    return {"args": {"name": name}}


def spaced_verify(work, meta, value):
    """backup/ holds the file with the space in its name, and only that one."""
    backup = work / "backup"
    return backup.is_dir() and sorted(p.name for p in backup.iterdir()) == [meta["args"]["name"]]


SPACE_SPRITE = Challenge(
    level=1, id="space_sprite", pet="slime", tools=("cp",), threat="Space Sprite", requires=["cp"], fix=True,
    task="The Space Sprite slipped a space into a file name: \"{name}\".\nCopy that file into backup/, and "
         "only that file. Then: verify",
    help="Here, --help won't help: the shell splits the line before cp even starts. Look at the lesson Quotes.",
    hints=["Bash cuts a command line at every space: cp {name} backup/ hands cp three names, not two, and "
           "copies two other files. ls -l shows them all. Quotes keep the words together as one name.",
           "Try: cp \"{name}\" backup/ (or a backslash before the space). If a wrong file got in, rm it from "
           "backup/ first."],
    zsh="In zsh, a name kept in a variable stays one word: n=\"{name}\"; cp $n backup/ works there, but not in "
        "bash, which splits $n at the space. Typed straight on the line, the space splits in both shells, so "
        "the quotes are a good habit: scripts usually run in bash.",
    setup=spaced_setup, verify=spaced_verify,
)


# --- Shebang Shade: the first line of a script, and the right to run it ---------------------------------

REPORT = """#/bin/bash
# Says how many lines each .txt file has.
for f in *.txt; do
  echo "$f: $(wc -l < "$f")"
done
"""


def shebang_setup(work, rng):
    (work / "report.sh").write_text(REPORT)
    (work / "report.sh").chmod(0o644)
    for room in rng.sample(ROOMS, 2):
        (work / f"{room}.txt").write_text("".join(f"line {i}\n" for i in range(rng.randint(2, 9))))
    return {}


def shebang_verify(work, meta, value):
    """It starts with #!/bin/bash (or #!/usr/bin/env bash), anyone may run it, and ./report.sh works."""
    script = work / "report.sh"
    if not script.is_file():
        return False
    first = script.read_text().split("\n", 1)[0].strip()
    if first not in ("#!/bin/bash", "#!/usr/bin/env bash") or not script.stat().st_mode & stat.S_IXUSR:
        return False
    done = runs(work, "./report.sh")
    return bool(done) and done.returncode == 0 and ".txt:" in done.stdout


SHEBANG_SHADE = Challenge(
    level=1, id="shebang_shade", pet="hedgehog", tools=("chmod",) + EDITORS, threat="Shebang Shade",
    requires=["chmod", "sed"], fix=True, uses=lambda a: "chmod" in a.tools,
    task="The Shebang Shade ate a character from the first line of report.sh, and took away the right to run "
         "it.\nMake ./report.sh run. Then: verify",
    help="Here, look at the Usage line and at u+x in the examples: who may do what.",
    hints=["Two things to fix. The first line, the shebang, says which program reads the script: #! then "
           "the path, #!/bin/bash. Here the ! is missing. And a file needs the x (execute) right to run as "
           "./report.sh: ls -l shows rw-r--r--, no x.",
           "Fix the first line with {editor} report.sh (or sed -i '1s/.*/#!\\/bin\\/bash/' report.sh), then "
           "chmod +x report.sh, then ./report.sh"],
    setup=shebang_setup, verify=shebang_verify,
)


# --- Rename Rat: one command per file, with a for loop -------------------------------------------------

def photos_setup(work, rng):
    names = sorted(rng.sample(("beach", "cake", "cat", "garden", "mountain", "snow", "sunset", "party",
                               "river", "forest"), 6))
    for name in names:
        (work / f"{name}.JPG").write_bytes(f"photo of {name}\n".encode())
    (work / "notes.txt").write_text("keep me\n")
    return {"names": names}


def photos_verify(work, meta, value):
    """Every photo is now NAME.jpg, with its own content, no .JPG left, and nothing else touched."""
    if list(work.glob("*.JPG")) or (work / "notes.txt").read_text() != "keep me\n":
        return False
    return all((work / f"{n}.jpg").is_file() and (work / f"{n}.jpg").read_bytes() == f"photo of {n}\n".encode()
               for n in meta["names"])


RENAME_RAT = Challenge(
    level=2, id="rename_rat", pet="ant", tools=("mv",), threat="Rename Rat", requires=["mv"], fix=True,
    uses=lambda a: "loop" in a.constructs or "rename" in a.tools,
    after=("clutter_critter",),
    task="The Rename Rat shouted every photo's extension: .JPG. Rename each one to .jpg (beach.JPG becomes "
         "beach.jpg), with a loop. Then: verify",
    help="Here, mv renames one file at a time: the loop is the shell's job (lesson Loops).",
    hints=["mv *.JPG *.jpg can't work: mv renames one file at a time. A for loop runs the same command once per "
           "file: for f in *.JPG; do ...; done, with $f holding one name each turn. ${f%.JPG} is that name "
           "without its .JPG at the end. Put echo in front of mv first to see what would happen.",
           "Try: for f in *.JPG; do mv \"$f\" \"${f%.JPG}.jpg\"; done"],
    setup=photos_setup, verify=photos_verify,
)


# --- Pattern Pixie: grep -E with a pattern that fits the whole line ------------------------------------

def codes_setup(work, rng):
    def code(letters, digits):
        return "".join(rng.choice("ABCDEFGHJKLMNPRSTUVWXZ") for _ in range(letters)) + "-" + "".join(
            rng.choice("0123456789") for _ in range(digits))
    good = [code(2, 4) for _ in range(rng.randint(4, 9))]
    bad = [code(3, 4), code(2, 3), code(2, 5), code(2, 4).lower(), "x" + code(2, 4), code(2, 4) + " old",
           code(1, 4), code(2, 4).replace("-", "_")]
    lines = good + bad
    rng.shuffle(lines)
    (work / "codes.txt").write_text("\n".join(lines) + "\n")
    return {"answer": len(good)}


PATTERN_PIXIE = Challenge(
    level=2, id="pattern_pixie", pet="mole", tools=("grep",), threat="Pattern Pixie", requires=["grep"],
    task="The Pattern Pixie mixed fake parcel codes into codes.txt. A real code is exactly 2 capital letters, "
         "a dash and 4 digits, like AB-1234, and nothing else on the line.\nHow many real codes are there?",
    help="Here, find -E (extended patterns), -x (the whole line must match) and -c (count).",
    hints=["A pattern describes the text: [A-Z] is one capital letter, [0-9] one digit, {2} means twice. "
           "So [A-Z]{2}-[0-9]{4} is AB-1234. Without -x it also matches inside longer lines (xAB-1234, "
           "ABC-1234): -x keeps only lines that are the pattern and nothing more.",
           "Try: grep -cxE '[A-Z]{2}-[0-9]{4}' codes.txt"],
    setup=codes_setup,
)


# --- Index Imp: the first line of a script picks its shell, and bash counts from 0 (0.9.0, lesson bash_zsh) --

COLORS = ("red", "green", "blue", "yellow", "purple", "orange", "pink", "brown", "grey", "white")


def index_setup(work, rng):
    """pick.sh prints ${colors[1]}: the second color in bash (which runs it), the first one in zsh."""
    colors = rng.sample(COLORS, 5)
    script = work / "pick.sh"
    script.write_text("#!/bin/bash\n# The Index Imp's pick of the day.\ncolors=(" + " ".join(colors) + ")\n"
                      'echo "${colors[1]}"\n')
    script.chmod(0o755)
    return {"answer": colors[1], "args": {"first": colors[0]}}


INDEX_IMP = Challenge(
    level=1, id="index_imp", pet="slime", tools=("bash",), threat="Index Imp", requires=["bash"],
    uses=lambda a: any("pick.sh" in name or any("pick.sh" in w for w in args) for name, args in a.commands),
    task="The Index Imp wrote pick.sh: it keeps five colors in a list and prints one of them with ${colors[1]}. "
         "Bash numbers the items of a list from 0, zsh from 1, so the same line can pick two different colors.\n"
         "Which color does pick.sh print? Then: answer <color>",
    help="Here, --help won't help: read the first line of pick.sh (head -1 pick.sh). It names the shell that "
         "runs the script.",
    hints=["Read the script before you guess: cat pick.sh. Its first line, #!/bin/bash, says that bash runs it, "
           "whatever shell you type in. Bash counts the items of a list from 0, so [1] is the second color.",
           "Try: ./pick.sh (or bash pick.sh). The script answers for itself."],
    zsh="You type in zsh, where ${colors[1]} is the first item ({first}). pick.sh still runs in bash, because "
        "its first line says so: it prints the second one. That's why scripts name their shell: they then "
        "behave the same in every terminal.",
    setup=index_setup,
)

ALL = [STDERR_STALKER, SPACE_SPRITE, SHEBANG_SHADE, RENAME_RAT, PATTERN_PIXIE, INDEX_IMP]


# --- the chest after the road lesson "Streams and scripts" ---------------------------------------------

STREAMS_CHEST = trial("trial_errors_only", 1, "A noisy script, check.sh, hides in this chest. Run it and save only "
                      "its error lines into errors.txt. Then: verify", STDERR_STALKER.hints, noisy_setup,
                      noisy_verify, requires=["bash"], teaches=["2>"])


# --- the chest after the road lesson "bash and zsh" ------------------------------------------------------

def unmatched_setup(work, rng):
    """No file matches the pattern: bash hands it to echo as it is, zsh would stop with an error."""
    ext = rng.choice(("pdf", "mp3", "odt", "iso", "csv"))
    for name in rng.sample(("notes.txt", "todo.txt", "photo.jpg", "song.ogg", "plan.md"), 3):
        (work / name).write_text("")
    script = work / "nothing.sh"
    script.write_text(f"#!/bin/bash\n# Lists the .{ext} files here.\necho *.{ext}\n")
    script.chmod(0o755)
    return {"answer": f"*.{ext}", "args": {"ext": ext}}


UNMATCHED_CHEST = trial(
    "trial_unmatched_pattern", 1, "nothing.sh lists the .{ext} files of this folder with echo *.{ext}, and there "
    "are none. Run it: what does it print? Then: answer <what it printed>",
    ["When no file matches a pattern, bash leaves the pattern as it is and gives it to the command: echo then "
     "prints the pattern itself. zsh would stop instead, with \"no matches found\". The script's first line "
     "says which of the two runs it.",
     "Try: ./nothing.sh (or bash nothing.sh), then answer exactly what it printed."],
    unmatched_setup, lambda w, m, v: v.strip() == m["answer"], requires=["bash"], teaches=["bash"])

CHESTS = [STREAMS_CHEST, UNMATCHED_CHEST]
