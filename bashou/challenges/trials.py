"""Shell trials: the locked chests of `bashou adventure`. Do something to files, then type `answer`.

Level 1: create, move, copy, rename, remove. Level 2: permissions, links, appending, find.
Level 3: archives, sed, grep -r. Everything happens in the sandbox folder.
"""

import tarfile

from . import Challenge

NAMES = ["amber", "birch", "cobalt", "dune", "ember", "fern", "glade", "harbor", "iris", "juniper"]


def trial(id, level, task, hints, setup, verify, requires=(), teaches=()):
    """`teaches`: the tool it practices; the chest right after that tool's lesson picks it."""
    return Challenge(id=id, pet="", tools=tuple(teaches), threat="Locked chest", task=task, hints=hints,
                     setup=setup, verify=verify, requires=list(requires) or ["ls"], level=level, kind="trial")


# --- level 1 ------------------------------------------------------------------------------------

def dirs_setup(work, rng):
    a, b, c = rng.sample(NAMES, 3)
    return {"args": {"path": f"{a}/{b}/{c}"}}


DIRS = trial("trial_dirs", 1, "Build the camp: create the folders {path} (all of them, in one command).",
             ["mkdir creates a folder; one option creates the missing parents too.", "Try: mkdir -p {path}"],
             dirs_setup, lambda w, m, v: (w / m["args"]["path"]).is_dir())


def note_setup(work, rng):
    return {"args": {"word": rng.choice(["north", "south", "east", "west"])}}


NOTE = trial("trial_note", 1, "Leave a trail: create the file map.txt containing the word {word}.",
             ["echo prints a word, > sends it into a file.", "Try: echo {word} > map.txt"],
             note_setup, lambda w, m, v: (w / "map.txt").is_file() and m["args"]["word"] in (w / "map.txt").read_text())


def move_setup(work, rng):
    (work / "chest").mkdir()
    (work / "key.txt").write_text("a small golden key\n")
    return {}


MOVE = trial("trial_move", 1, "Put the key (key.txt) into the chest/ folder.",
             ["mv moves a file (and renames it).", "Try: mv key.txt chest/"],
             move_setup, lambda w, m, v: (w / "chest" / "key.txt").is_file() and not (w / "key.txt").exists())


def copy_setup(work, rng):
    scroll = work / "scroll"
    scroll.mkdir()
    for name in rng.sample(NAMES, 3):
        (scroll / f"{name}.txt").write_text(f"spell of {name}\n")
    return {"args": {}, "files": sorted(p.name for p in scroll.iterdir())}


COPY = trial("trial_copy", 1, "Make a backup: copy the folder scroll/ with everything in it to backup/.",
             ["cp copies files; folders need an option to copy what's inside.", "Try: cp -r scroll backup"],
             copy_setup, lambda w, m, v: (w / "backup").is_dir()
             and sorted(p.name for p in (w / "backup").iterdir()) == m["files"] and (w / "scroll").is_dir())


def rename_setup(work, rng):
    (work / "rusty_sword.txt").write_text("a sword\n")
    return {}


RENAME = trial("trial_rename", 1, "Polish the sword: rename rusty_sword.txt to shiny_sword.txt.",
               ["The same command moves and renames.", "Try: mv rusty_sword.txt shiny_sword.txt"],
               rename_setup, lambda w, m, v: (w / "shiny_sword.txt").is_file() and not (w / "rusty_sword.txt").exists())


def clean_setup(work, rng):
    keep = rng.sample(NAMES, 3)
    for name in keep:
        (work / f"{name}.txt").write_text("keep me\n")
    for name in rng.sample(NAMES, 4):
        (work / f"{name}.tmp").write_text("junk\n")
    return {"keep": [f"{n}.txt" for n in keep]}


CLEAN = trial("trial_clean", 1, "Sweep the camp: remove every .tmp file, keep the .txt ones.",
              ["rm removes files; *.tmp matches every name ending in .tmp.", "Try: rm *.tmp"],
              clean_setup, lambda w, m, v: not list(w.glob("*.tmp")) and all((w / k).is_file() for k in m["keep"]))


# --- level 2 ------------------------------------------------------------------------------------

def spell_setup(work, rng):
    spell = work / "spell.sh"
    spell.write_text("#!/bin/sh\necho '✨ it worked' > cast.txt\necho '✨ cast!'\n")
    spell.chmod(0o644)
    return {}


SPELL = trial("trial_spell", 2, "Make spell.sh runnable, then run it (./spell.sh).",
              ["A file needs the x permission to be run.", "Try: chmod u+x spell.sh && ./spell.sh"],
              spell_setup, lambda w, m, v: (w / "cast.txt").is_file())


def link_setup(work, rng):
    (work / "camp" / "tent").mkdir(parents=True)
    return {}


LINK = trial("trial_link", 2, "Make a shortcut: a symbolic link named home that points to camp/tent.",
             ["ln makes links; one option makes a symbolic (soft) link.", "Try: ln -s camp/tent home"],
             link_setup, lambda w, m, v: (w / "home").is_symlink() and (w / "home").resolve() == (w / "camp" / "tent").resolve())


def journal_setup(work, rng):
    lines = [f"day {i}: walked" for i in range(1, rng.randint(3, 6))]
    (work / "journal.txt").write_text("\n".join(lines) + "\n")
    return {"lines": lines}


JOURNAL = trial("trial_journal", 2, "Write in the journal: add the line rested at the end of journal.txt, "
                "without erasing it.",
                [">> appends, > would replace the whole file.", "Try: echo rested >> journal.txt"],
                journal_setup, lambda w, m, v: (w / "journal.txt").read_text().splitlines() == m["lines"] + ["rested"])


def gems_setup(work, rng):
    count = 0
    for i in range(rng.randint(3, 6)):
        folder = work / "cave" / rng.choice(NAMES) / rng.choice(NAMES)
        folder.mkdir(parents=True, exist_ok=True)
        for j in range(rng.randint(0, 3)):
            (folder / f"gem{i}{j}.gem").write_text("✦\n")
            count += 1
        (folder / f"rock{i}.txt").write_text("just a rock\n")
    return {"answer": len(list((work / "cave").rglob("*.gem")))}


GEMS = trial("trial_gems", 2, "How many .gem files are hidden in cave/, at any depth? Then: answer <number>",
             ["find searches every folder below; wc -l counts lines.", "Try: find cave -name '*.gem' | wc -l"],
             gems_setup, lambda w, m, v: v.strip() == str(m["answer"]), requires=["find"])


# --- level 3 ------------------------------------------------------------------------------------

def loot_setup(work, rng):
    loot = work / "loot"
    loot.mkdir()
    for name in rng.sample(NAMES, 3):
        (loot / f"{name}.coin").write_text("1\n")
    return {"files": sorted(p.name for p in loot.iterdir())}


def loot_verify(work, meta, value):
    try:
        with tarfile.open(work / "loot.tar.gz", "r:gz") as tar:
            names = {n.rsplit("/", 1)[-1] for n in tar.getnames()}
    except (OSError, tarfile.TarError):
        return False
    return set(meta["files"]) <= names


LOOT = trial("trial_loot", 3, "Pack the loot: put the folder loot/ into a compressed archive loot.tar.gz.",
             ["tar: c creates, z compresses with gzip, f names the archive.", "Try: tar czf loot.tar.gz loot"],
             loot_setup, loot_verify, requires=["tar"])


def letter_setup(work, rng):
    text = "Dear dragon,\nThe dragon of the hills says hi.\nYour friend, the other dragon.\n"
    (work / "letter.txt").write_text(text)
    return {"expected": text.replace("dragon", "friend")}


LETTER = trial("trial_letter", 3, "Make peace: in letter.txt, replace every dragon with friend (edit the file in place).",
               ["sed can edit a file in place; g replaces every match on a line.",
                "Try: sed -i 's/dragon/friend/g' letter.txt"],
               letter_setup, lambda w, m, v: (w / "letter.txt").read_text() == m["expected"], requires=["sed"])


def scrolls_setup(work, rng):
    names = rng.sample(NAMES, 6)
    lib = work / "library"
    for i, name in enumerate(names):
        folder = lib / names[(i + 1) % 6]
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f"{name}.txt").write_text("old words, nothing here\n")
    winner = rng.choice(names)
    hit = next(lib.rglob(f"{winner}.txt"))
    hit.write_text("under the third stone lies the treasure\n")
    return {"answer": hit.name}


SCROLLS = trial("trial_scrolls", 3, "One scroll in library/ talks about the treasure. Which file? Then: answer <file name>",
                ["grep -r searches every file below a folder; -l prints only the file names.",
                 "Try: grep -rl treasure library"],
                scrolls_setup, lambda w, m, v: v.strip().rsplit("/", 1)[-1] == m["answer"], requires=["grep"])


# --- after a lesson ----------------------------------------------------------------------------

def people_setup(work, rng):
    names = rng.sample(["ada", "linus", "grace", "ken", "dennis", "margaret", "alan", "barbara"], 6)
    cities = ["paris", "lyon", "brest", "nantes"]
    rows = [(n, rng.randint(18, 70), rng.choice(cities)) for n in names]
    (work / "people.txt").write_text("".join(f"{n} {a} {c}\n" for n, a, c in rows))
    return {"names": [r[0] for r in rows], "cities": len({r[2] for r in rows})}


NAMES_COL = trial("trial_awk_names", 2, "people.txt has a name, an age and a city per line. Make names.txt with "
                  "only the names, one per line.",
                  ["awk '{print $1}' prints the first field; > writes it to a file.",
                   "Try: awk '{print $1}' people.txt > names.txt"],
                  people_setup, lambda w, m, v: (w / "names.txt").is_file()
                  and (w / "names.txt").read_text().split() == m["names"], requires=["awk"], teaches=["awk"])


def prices_setup(work, rng):
    items = rng.sample(["apple", "bread", "cheese", "milk", "tea", "rice", "soap"], 5)
    prices = [rng.randint(1, 20) for _ in items]
    (work / "prices.txt").write_text("".join(f"{i} {p}\n" for i, p in zip(items, prices)))
    return {"answer": sum(prices)}


PRICES = trial("trial_awk_sum", 2, "prices.txt has an item and a price per line. What's the total? Then: answer <number>",
               ["awk can add up a column in a variable and print it in END.",
                "Try: awk '{s += $2} END {print s}' prices.txt"],
               prices_setup, lambda w, m, v: v.strip() == str(m["answer"]), requires=["awk"], teaches=["awk"])

CITIES = trial("trial_pipe_cities", 2, "How many different cities are in people.txt (3rd column)? Then: answer <number>",
               ["Three steps joined with | (a pipe): keep the city column (awk '{print $3}' or cut -d' ' -f3), "
                "keep each city once, count the lines (wc -l).",
                "To keep each city once, sort first: uniq only removes duplicates that are next to each other, "
                "and sort puts identical lines together. sort -u does both at once.",
                "Try: awk '{print $3}' people.txt | sort -u | wc -l"],
               people_setup, lambda w, m, v: v.strip() == str(m["cities"]), requires=["sort", "wc"], teaches=["|"])


TRIALS = [DIRS, NOTE, MOVE, COPY, RENAME, CLEAN, SPELL, LINK, JOURNAL, GEMS, LOOT, LETTER, SCROLLS,
          NAMES_COL, PRICES, CITIES]
