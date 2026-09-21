"""The hero seen from behind (one per starter form), in the creatures.py format."""

from .. import creatures


def mirrored(halves):
    """Rows from their left half (9 columns, the 9th is the middle): symmetric sprites stay symmetric."""
    return [h + h[:8][::-1] for h in halves]


def with_pixels(rows, changes):
    rows = [list(r) for r in rows]
    for r, c, ch in changes:
        rows[r][c] = ch
    return ["".join(r) for r in rows]


TAIL = [(7, 8, "a"), (8, 8, "a"), (9, 8, "a"), (10, 8, "a")]

BACK = {
    "kitten": with_pixels(mirrored([
        ".........", ".........", ".........", "....a....", "...aoa...", "...aoaaaa",
        "..aoooooo", "..aoooooo", "...aaoooo", "...aooooo", "..aoooooo", "...aaa...",
    ]), [(6, 8, "a"), (8, 8, "a"), (9, 8, "a"), (10, 8, "a")]),
    "cat": with_pixels(mirrored([
        "...a.....", "..apa....", "..aooaaaa", ".aooooooo", ".aooooooo", "aoooaoooo",
        "aoooooooo", ".aaoooooo", ".aoooaooo", "aoooooooo", "aoooooooo", ".aaaa....",
    ]), TAIL + [(6, 8, "l")]),
    "lion": with_pixels(mirrored([
        "....NNNNN", "..NNMMMMM", ".NMMMMMMM", "NMMMMMMMM", "NMMMMMMMM", "NMMMMMMMM",
        ".NMMMMMMM", "..NNMMMMM", "...aooooo", "..aoooooo", ".aooooooo", ".lla.....",
    ]), [(8, 8, "a"), (9, 8, "a"), (10, 8, "a"), (11, 8, "M")]),
    "seedling": mirrored([
        ".........", ".........", ".........", "...LL....", "..LlLL...", "...LLLL.g",
        "........g", ".....aaaa", "....aoooo", "...aooooo", "...aooooo", "....aaaaa",
    ]),
    "sprout": mirrored([
        "...LL....", "..LlLL...", ".LlllL...", ".LLLLLLLg", "..LL....g", "........g",
        "...aaaaaa", "..aoooooo", ".aooooooo", ".aooooooo", "..aoooooo", "...aaaaaa",
    ]),
    "tree": mirrored([
        "....ddddd", "..ddLLLLL", ".dLLlLLfL", "dLLlLLLLL", "dLLLLfLLL", ".ddLLLLLL",
        "...dtTTTT", "...tTTTTT", "...tTTtTT", "...tTTTTT", "...tTtTTT", "..ttt.ttt",
    ]),
    "pebble": mirrored([
        ".........", ".........", ".........", ".........", ".........", ".........",
        "....aaaaa", "..aaolooo", ".aooooooo", ".aooooloo", ".aooooooo", "..aaaaaaa",
    ]),
    "golem": mirrored([
        "......GGG", ".....aGGG", "....aoooo", "....aoooo", "....aoooo", "....aoooo",
        "..aaaoooo", "..aoaoooo", "..aoaoooo", "...a.aooo", ".....aoaa", "....aaa..",
    ]),
    "crystal": mirrored([
        ".C......c", ".cC...aCc", ".cc..aooo", "..a.aoooo", ".ac.aoooo", ".aCaaoooo",
        ".aooaoooo", ".aooaoooo", "..a.aoooo", "....aoocc", "....aoaaa", "...aaa...",
    ]),
}


def hero(form):
    """(frames, palette): the back view, then a step with each side (feet lifted, body up a pixel)."""
    base = BACK.get(form, BACK["kitten"])
    palette = creatures.get(form).palette
    low = max(i for i, row in enumerate(base) if row.strip("."))
    has_feet = "." in base[low].strip(".")

    def step(side):
        rows = [row for row in base]
        if has_feet:                              # lift one foot
            row = list(rows[low])
            for c in (range(0, 8) if side < 0 else range(9, 17)):
                row[c] = "."
            rows[low] = "".join(row)
        return rows[1:] + ["." * 17]              # and bob up a pixel

    return [base, step(-1), base, step(1)], palette


# --- things on the road (drawn from their bottom center by scene.blit) ------------------------

TOPIC_COLORS = {
    "bash": ((90, 200, 110), (40, 120, 60)), "linux": ((240, 200, 70), (150, 110, 30)),
    "python": ((80, 140, 220), (240, 210, 80)), "rust": ((220, 110, 60), (130, 60, 30)),
    "c": ((150, 160, 190), (80, 90, 120)), "debian": ((215, 30, 90), (120, 20, 50)),
    "rocky": ((60, 180, 140), (30, 100, 80)), "cicd": ((170, 110, 230), (90, 50, 140)),
}

MONSTER = [
    "....aaaaa....",
    "..aaoooooaa..",
    ".aoooooooooa.",
    ".aowmoooowmo.",
    "aoowwoooowwoa",
    "aooooommooooa",
    "aooooooooooooa"[:13],
    ".aaoooooooaa.",
    "...aa...aa...",
]

BOSS = [
    "..h.........h.......",
    "..hh...hh...hh......"[:20],
    "...hhhhhhhhhh.......",
    "..aaaaaaaaaaaa......",
    ".aoooooooooooooa....",
    "aooowwoooooowwooa...",
    "aoowmmwooooowmmwooa.",
    "aooowwoooooowwoooa..",
    "aoooooooooooooooooa.",
    "aooottttttttttoooa..",
    "aooottTttTttTtooooa.",
    ".aooooooooooooooa...",
    "..aoooooooooooooa...",
    ".aaooaaaaaaaooaa....",
    "aooa........aooa....",
    "aaa..........aaa....",
]


def symmetric(rows):
    """Rows trimmed to their left part and mirrored, so every boss stays symmetric."""
    half = [r[: (len(r) + 1) // 2] for r in rows]
    return [h + h[:-1][::-1] for h in half]


def monster(topic):
    body, dark = TOPIC_COLORS.get(topic, TOPIC_COLORS["bash"])
    return symmetric(MONSTER), {"a": dark, "o": body, "w": (255, 255, 255), "m": (25, 25, 25)}


def boss(topic):
    body, dark = TOPIC_COLORS.get(topic, TOPIC_COLORS["bash"])
    return symmetric(BOSS), {"a": dark, "o": body, "w": (255, 255, 255), "m": (200, 30, 40),
                             "t": (250, 250, 250), "T": (255, 255, 255), "h": (240, 210, 90)}


CHEST = ([".aaaaaaa.", "aYyyyyyYa", "aaaaYaaaa", "ayyyyyyya", "ayyyyyyya", "aaaaaaaaa"],
         {"a": (110, 70, 35), "y": (175, 120, 60), "Y": (240, 200, 80)})
CAMPFIRE = (["...Y...", "..YOY..", ".YORY..", "..ORO..", "bbbbbbb", ".b.b.b."],
            {"Y": (255, 230, 120), "O": (255, 150, 40), "R": (220, 70, 30), "b": (110, 75, 45)})
SIGNPOST = (["aaaaaaaaa", "ayyyyyyya", "aaaaaaaaa", "....b....", "....b....", "....b....", "...bbb..."],
            {"a": (120, 80, 40), "y": (220, 180, 110), "b": (100, 70, 40)})
