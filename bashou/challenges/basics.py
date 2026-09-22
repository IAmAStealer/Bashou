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
    hints=["`bashou learn wc` takes the command apart, `wc --help` lists its options. "
           "One command, one option, no pipe.",
           "Try: wc -l notes.txt"],
    setup=notes_setup,
)

COLUMN_CRAB = Challenge(
    level=1, id="column_crab", pet="owl", tools=("cut",), threat="Column Crab",
    task="The Column Crab pinches the wrong column.\n"
         "servers.csv holds name,room,port. Which room is on line {n}?",
    hints=["`bashou learn cut` explains it: -d says what separates the columns, -f which one to keep. "
           "Print the column, then read the line you need.",
           "Try: cut -d, -f2 servers.csv"],
    setup=servers_setup,
)

JUMBLE_SPRITE = Challenge(
    level=1, id="jumble_sprite", pet="sofa", tools=("sort",), threat="Jumble Sprite",
    task="The Jumble Sprite shuffled names.txt.\nWhich name comes first in alphabetical order?",
    hints=["`bashou learn sort` explains it: sort prints a file in order, no option needed.",
           "Try: sort names.txt"],
    setup=names_setup,
)

LAST_WORD_WISP = Challenge(
    level=1, id="last_word_wisp", pet="mole", tools=("tail", "head"), threat="Last-word Wisp",
    task="The Last-word Wisp hides at the end of boot.log.\nWhat is the last line of the file?",
    hints=["`bashou learn tail`: tail shows the end of a file, head its start. One command is enough.",
           "Try: tail -1 boot.log"],
    setup=boot_setup,
)

ALL = [LINE_MOTH, COLUMN_CRAB, JUMBLE_SPRITE, LAST_WORD_WISP]
