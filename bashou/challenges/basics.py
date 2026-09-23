"""First fights: one command, one option at most. They come before the tool fights (owner, 2026-09-22)."""

from . import Challenge

WORDS = ("milk", "bread", "cables", "spare keys", "tea", "batteries", "stamps", "socks", "coffee",
         "notebook", "pens", "soap", "rice", "lamp", "towels", "screws", "tape", "candles")
NAMES = ("ada", "bo", "casey", "dara", "eli", "fern", "gil", "hana", "ines", "joss", "kim", "lior",
         "mira", "nils", "omar", "pia", "quinn", "remy", "sana", "tao")
ROOMS = ("attic", "cellar", "garage", "kitchen", "library", "loft", "porch", "shed", "studio", "vault")


def notes_setup(work, rng):
    lines = [rng.choice(WORDS) for _ in range(rng.randint(12, 40))]
    (work / "notes.txt").write_text("\n".join(lines) + "\n")
    return {"answer": len(lines)}


def servers_setup(work, rng):
    hosts = rng.sample(NAMES, 8)
    rooms = [rng.choice(ROOMS) for _ in hosts]
    lines = [f"{h},{r},{rng.randint(1000, 9999)}" for h, r in zip(hosts, rooms)]
    (work / "servers.csv").write_text("\n".join(lines) + "\n")
    n = rng.randint(2, len(lines))
    return {"answer": rooms[n - 1], "args": {"n": n}}


def names_setup(work, rng):
    names = rng.sample(NAMES, 10)
    (work / "names.txt").write_text("\n".join(names) + "\n")
    return {"answer": min(names)}


def boot_setup(work, rng):
    steps = [f"step-{rng.randint(100, 999)}" for _ in range(rng.randint(15, 30))]
    (work / "boot.log").write_text("\n".join(steps) + "\n")
    return {"answer": steps[-1]}


LINE_MOTH = Challenge(
    level=1, id="line_moth", pet="sofa", tools=("wc",), threat="Line Moth",
    task="The Line Moth eats one line at a time.\nHow many lines does notes.txt have?",
    help="Here, find the option that counts lines.",
    hints=["`bashou learn wc` takes the command apart, `wc --help` lists its options. "
           "One command, one option, no pipe.",
           "Try: wc -l notes.txt"],
    setup=notes_setup,
)

COLUMN_CRAB = Challenge(
    level=1, id="column_crab", pet="owl", tools=("cut",), threat="Column Crab",
    task="The Column Crab pinches the wrong column.\n"
         "servers.csv holds name,room,port. Which room is on line {n}?",
    help="Here, find the options for the delimiter (what separates columns) and the fields to keep.",
    hints=["`bashou learn cut` explains it: -d says what separates the columns, -f which one to keep. "
           "Print the column, then read the line you need.",
           "Try: cut -d, -f2 servers.csv"],
    setup=servers_setup,
)

JUMBLE_SPRITE = Challenge(
    level=1, id="jumble_sprite", pet="sofa", tools=("sort",), threat="Jumble Sprite",
    task="The Jumble Sprite shuffled names.txt.\nWhich name comes first in alphabetical order?",
    help="Here, the Usage line is enough: sort FILE prints it in order.",
    hints=["`bashou learn sort` explains it: sort prints a file in order, no option needed.",
           "Try: sort names.txt"],
    setup=names_setup,
)

LAST_WORD_WISP = Challenge(
    level=1, id="last_word_wisp", pet="mole", tools=("tail", "head"), threat="Last-word Wisp",
    task="The Last-word Wisp hides at the end of boot.log.\nWhat is the last line of the file?",
    help="Here, find how to choose how many lines to show.",
    hints=["`bashou learn tail`: tail shows the end of a file, head its start. One command is enough.",
           "Try: tail -1 boot.log"],
    setup=boot_setup,
)

ALL = [LINE_MOTH, COLUMN_CRAB, JUMBLE_SPRITE, LAST_WORD_WISP]


def recipe_setup(work, rng):
    steps = [f"add-{rng.choice(WORDS).replace(' ', '-')}-{rng.randint(10, 99)}" for _ in range(8)]
    (work / "recipe.txt").write_text("\n".join(steps) + "\n")
    n = rng.randint(2, 6)
    return {"answer": steps[n - 1], "args": {"n": n}}


def contacts_setup(work, rng):
    people = rng.sample(NAMES, 9)
    numbers = [f"0{rng.randint(1, 9)}-{rng.randint(10, 99)}-{rng.randint(10, 99)}-{rng.randint(10, 99)}"
               for _ in people]
    (work / "contacts.txt").write_text("\n".join(f"{p} {n}" for p, n in zip(people, numbers)) + "\n")
    i = rng.randrange(len(people))
    return {"answer": numbers[i], "args": {"who": people[i]}}


def people_setup(work, rng):
    people = rng.sample(NAMES, 9)
    ages = [rng.randint(18, 79) for _ in people]
    lines = [f"{p} {a} {rng.choice(ROOMS)}" for p, a in zip(people, ages)]
    (work / "people.txt").write_text("\n".join(lines) + "\n")
    n = rng.randint(2, len(lines))
    return {"answer": ages[n - 1], "args": {"n": n}}


def crates_setup(work, rng):
    crates = work / "crates"
    crates.mkdir()
    for _ in range(rng.randint(6, 12)):
        (crates / f"{rng.choice(WORDS).replace(' ', '-')}-{rng.randint(10, 99)}.txt").write_text("junk\n")
    key = f"{rng.choice(NAMES)}-{rng.randint(100, 999)}.key"
    (crates / key).write_text("open me\n")
    return {"answer": key}


def poem_setup(work, rng):
    lines = rng.sample([w for w in WORDS if " " not in w], 8)
    (work / "poem.txt").write_text("\n".join(lines) + "\n")
    n = rng.randint(2, 8)
    return {"answer": lines[n - 1], "args": {"n": n}}


def scores_setup(work, rng):
    scores = rng.sample(range(10, 999), 12)
    (work / "scores.txt").write_text("\n".join(str(s) for s in scores) + "\n")
    return {"answer": max(scores)}


FIRST_LINE_IMP = Challenge(
    level=1, id="first_line_imp", pet="mole", tools=("head",), threat="First-line Imp",
    task="The First-line Imp swaps the steps of recipe.txt.\nWhat is written on line {n}?",
    help="Here, find how to choose how many lines to show.",
    hints=["`bashou learn head`: head shows the start of a file, -n how many lines. Then read the last one.",
           "Try: head -{n} recipe.txt"],
    setup=recipe_setup,
)

NEEDLE_GNAT = Challenge(
    level=1, id="needle_gnat", pet="mole", tools=("grep",), threat="Needle Gnat",
    task="The Needle Gnat buzzes around contacts.txt.\nWhat is {who}'s phone number?",
    help="Here, the Usage line is enough: a PATTERN, then a FILE.",
    hints=["`bashou learn grep`: grep keeps the lines that contain a word. No option needed.",
           "Try: grep {who} contacts.txt"],
    setup=contacts_setup,
)

FIELD_WASP = Challenge(
    level=1, id="field_wasp", pet="owl", tools=("awk",), threat="Field Wasp",
    task="The Field Wasp mixes up the columns of people.txt (name age room).\n"
         "How old is the person on line {n}?",
    help="awk's help is short: its real language is in `man awk`. Here you need the 'program' part: "
         "'{print $2}'.",
    hints=["`bashou learn awk`: awk cuts each line into fields, $1 is the first word, $2 the second. "
           "Print the column, then read the line you need.",
           "Try: awk '{print $2}' people.txt"],
    setup=people_setup,
)

DUST_BUNNY = Challenge(
    level=1, id="dust_bunny", pet="fox", tools=("ls",), threat="Dust Bunny",
    task="A Dust Bunny rolled into crates/.\nWhich file in there ends in .key?",
    help="Here, the Usage line is enough: ls FOLDER.",
    hints=["`bashou learn ls`: ls lists what a folder holds. One command, no option.",
           "Try: ls crates"],
    setup=crates_setup,
)

VERSE_VIPER = Challenge(
    level=1, id="verse_viper", pet="snake", tools=("sed",), threat="Verse Viper",
    task="The Verse Viper coils around poem.txt.\nWhat word is on line {n}?",
    help="Here, find the option that stops sed printing every line (-n); the script 'Np' prints line N.",
    hints=["`bashou learn sed`: with -n sed stays quiet, and '{n}p' prints only that line.",
           "Try: sed -n '{n}p' poem.txt"],
    setup=poem_setup,
)

PEAK_HARPY = Challenge(
    level=2, id="peak_harpy", pet="sofa", tools=("sort",), threat="Peak Harpy",
    task="The Peak Harpy nests on the highest score.\nWhat is the biggest number in scores.txt?",
    help="Here, find the option that compares numbers, not text.",
    hints=["sort compares as text unless you pass -n, which compares as numbers. "
           "The last line of the sorted file is the biggest one: `tail -1`.",
           "Try: sort -n scores.txt | tail -1"],
    setup=scores_setup,
)

ALL += [FIRST_LINE_IMP, NEEDLE_GNAT, FIELD_WASP, DUST_BUNNY, VERSE_VIPER, PEAK_HARPY]
