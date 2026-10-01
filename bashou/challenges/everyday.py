"""Everyday fights: the first moves of the path. Read a tool's help, fix a file in an editor, tidy files
into folders, remove with a wildcard, ask the computer how many processors it has."""

import os

from . import Challenge
from .repos import EDITORS
from .trials import trial

NAMES = ("ada", "bo", "casey", "dara", "eli", "fern", "gil", "hana", "ines", "joss", "kim", "lior",
         "mira", "nils", "omar", "pia", "quinn", "remy", "sana", "tao")


# --- Flag Phantom: sort puts capitals first, --help shows the option that ignores case ------------------

def names_setup(work, rng):
    """The first name, case ignored, is written in small letters, and a capitalized name comes later in the
    alphabet: a plain sort (capitals first in most systems) shows the wrong one on top."""
    names = sorted(rng.sample(NAMES, 9))
    first, rest = names[0], names[1:]
    capitals = rng.sample(rest, 4)
    shown = [first] + [n.capitalize() if n in capitals else n for n in rest]
    rng.shuffle(shown)
    (work / "names.txt").write_text("\n".join(shown) + "\n")
    return {"answer": first}


FLAG_PHANTOM = Challenge(
    level=1, id="flag_phantom", pet="sofa", tools=("sort",), threat="Flag Phantom", requires=["sort"],
    task="The Flag Phantom wrote some of the names in names.txt with a capital letter, and sort may put every capital "
         "first.\nWhich name comes first in alphabetical order when you ignore capitals?",
    help="Here, find the option that ignores the case (capital or small letters).",
    hints=["Every tool explains its options: sort --help. Look for the word case: one option folds small "
           "letters and capitals together, so Mira and mira count as the same letters.",
           "Try: sort -f names.txt (-f is short for --ignore-case). The first line is the answer, "
           "written as in the file."],
    setup=names_setup,
    verify=lambda w, m, v: v.strip().lower() == m["answer"],
)


# --- Typo Troll: one wrong word to fix in an editor ------------------------------------------------------

RECIPE = ["Pancakes for four", "250 g of flour", "2 eggs", "half a litre of milk", "a pinch of salt",
          "1 spoon of sugar", "Mix, rest one hour, then cook in a hot pan."]
TYPOS = {"flour": "flower", "eggs": "egss", "milk": "mlik", "salt": "slat", "sugar": "suger"}


def recipe_setup(work, rng):
    good = rng.choice(sorted(TYPOS))
    bad = TYPOS[good]
    n = next(i for i, line in enumerate(RECIPE) if good in line.split())
    lines = RECIPE[:n] + [RECIPE[n].replace(good, bad)] + RECIPE[n + 1:]
    (work / "recipe.txt").write_text("\n".join(lines) + "\n")
    return {"args": {"bad": bad, "good": good, "n": n + 1}}


def recipe_verify(work, meta, value):
    """The recipe is whole again: every line as written, and nothing else changed."""
    path = work / "recipe.txt"
    return path.is_file() and [line.rstrip() for line in path.read_text().strip().splitlines()] == RECIPE


TYPO_TROLL = Challenge(
    level=1, id="typo_troll", pet="ant", tools=EDITORS, threat="Typo Troll", requires=["sed"], fix=True,
    help="Here, look at the last lines of nano's screen instead: ^O means Ctrl+O, and each key says what it does.",
    task="The Typo Troll scribbled in recipe.txt: on line {n}, {bad} should be {good}.\nFix the word in the "
         "file. Then: verify",
    hints=["Open the file in an editor: {editor} recipe.txt. Move with the arrow keys to line {n}, fix the "
           "word, then save and quit ({save_keys}). cat recipe.txt shows the result.",
           "With {editor}: {editor} recipe.txt, fix {bad} into {good}, {save_keys}. Or in one command, "
           "without opening the file: sed -i 's/{bad}/{good}/' recipe.txt"],
    setup=recipe_setup, verify=recipe_verify,
)


# --- Clutter Critter: mkdir and mv, to tidy files into folders ------------------------------------------

PHOTOS = ("beach", "cake", "cat", "garden", "mountain", "snow", "sunset", "party")
DOCS = ("budget", "letter", "notes", "plans", "recipes", "todo", "travel")


def clutter_setup(work, rng):
    photos = [f"{p}.jpg" for p in rng.sample(PHOTOS, 4)]
    docs = [f"{d}.txt" for d in rng.sample(DOCS, 3)]
    for name in photos:
        (work / name).write_bytes(b"\xff\xd8 a photo\n")
    for name in docs:
        (work / name).write_text("a document\n")
    return {"photos": sorted(photos), "docs": sorted(docs)}


def clutter_verify(work, meta, value):
    """photos/ holds the photos, docs/ the documents, and nothing is left loose."""
    def names(folder):
        return sorted(p.name for p in folder.iterdir()) if folder.is_dir() else None
    loose = [n for n in meta["photos"] + meta["docs"] if (work / n).exists()]
    return names(work / "photos") == meta["photos"] and names(work / "docs") == meta["docs"] and not loose


CLUTTER_CRITTER = Challenge(
    level=1, id="clutter_critter", pet="squirrel", tools=("mv",), threat="Clutter Critter", requires=["mkdir", "mv"],
    fix=True, uses=lambda a: {"mkdir", "mv"} <= a.tools,
    help="Here, the Usage lines show that mv takes several files (SOURCE...) and one DIRECTORY at the end.",
    task="The Clutter Critter threw photos and documents all over the folder.\nCreate the folders photos and "
         "docs, put every .jpg into photos/ and every .txt into docs/. Then: verify",
    hints=["Two steps. mkdir creates folders, and it takes several names at once. Then mv moves files into a "
           "folder: the last name is where they go. A * stands for any name, so *.jpg means every file "
           "ending in .jpg.",
           "Try: mkdir photos docs, then mv *.jpg photos/ and mv *.txt docs/. ls -R shows where everything is."],
    setup=clutter_setup, verify=clutter_verify,
)


# --- Glob Goblin: one wildcard, and only the right files go --------------------------------------------

def reports_setup(work, rng):
    gone = [f"report-2025-{m:02}.csv" for m in sorted(rng.sample(range(1, 13), 5))]
    kept = ([f"report-2024-{m:02}.csv" for m in sorted(rng.sample(range(1, 13), 3))]
            + ["report-2025-summary.txt", f"old-report-2025-{rng.randint(1, 12):02}.csv", "notes.txt"])
    for name in gone + kept:
        (work / name).write_text("month,total\n")
    return {"gone": gone, "kept": kept}


def reports_verify(work, meta, value):
    return (not any((work / n).exists() for n in meta["gone"])
            and all((work / n).is_file() for n in meta["kept"]))


GLOB_GOBLIN = Challenge(
    level=1, id="glob_goblin", pet="fox", tools=("rm",), threat="Glob Goblin", requires=["rm"], fix=True,
    help="Here, look at -i: rm asks before removing each file. Handy to check what a pattern catches.",
    task="The Glob Goblin piled up old reports. Remove the 2025 monthly reports, report-2025-*.csv, and only "
         "them: the 2024 ones, the summary and your notes stay.\nThen: verify",
    hints=["A wildcard pattern becomes a list of names before the command runs: * stands for any characters. "
           "rm has no undo, so first look at what the pattern catches with ls report-2025-*.csv. The pattern "
           "starts with report, so old-report-... isn't caught.",
           "When ls shows exactly the five monthly files: rm report-2025-*.csv"],
    setup=reports_setup, verify=reports_verify,
)


# --- Core Counter: nproc --------------------------------------------------------------------------------

def cores():
    """What nproc prints: the processors this program may use (all of them, in most cases)."""
    try:
        return len(os.sched_getaffinity(0))
    except (AttributeError, OSError):
        return os.cpu_count() or 1


CORE_COUNTER = Challenge(
    level=1, id="core_counter", pet="meerkat", tools=("nproc",), threat="Core Counter", requires=["nproc"],
    skill="linux",
    task="The Core Counter wants to know who it's up against.\nHow many processors (cores) can programs use on "
         "this computer?",
    help="Here, the Usage line is enough: the command takes no file.",
    hints=["A processor (core) runs one program at a time; with several, several programs run at once. "
           "One short command, n for number and proc for processors, prints how many there are.",
           "Try: nproc"],
    setup=lambda work, rng: {},
    verify=lambda w, m, v: v.strip() in {str(cores()), str(os.cpu_count())},
)

ALL = [FLAG_PHANTOM, TYPO_TROLL, CLUTTER_CRITTER, GLOB_GOBLIN, CORE_COUNTER]


# --- the chests after the road lessons "files and editing", "help and wildcards" -----------------------

def notes_setup(work, rng):
    (work / "notes").mkdir()
    for name in rng.sample(DOCS, 3):
        (work / f"{name}.txt").write_text("a note\n")
    return {}


FILES_CHEST = trial("trial_tidy_notes", 1, "Notes lie loose in this chest. Move every .txt file into the folder "
                    "notes/. Then: verify",
                    ["mv moves files; the last name is where they go. *.txt means every name ending in .txt.",
                     "Try: mv *.txt notes/"],
                    notes_setup, lambda w, m, v: not list(w.glob("*.txt")) and len(list((w / "notes").glob("*.txt"))) == 3,
                    requires=["mv"], teaches=["mv"])
GLOB_CHEST = trial("trial_glob_reports", 1, "Old reports fill this chest. Remove report-2025-*.csv and nothing "
                   "else. Then: verify", GLOB_GOBLIN.hints, reports_setup, reports_verify, requires=["rm"],
                   teaches=["*"])
CHESTS = [FILES_CHEST, GLOB_CHEST]
