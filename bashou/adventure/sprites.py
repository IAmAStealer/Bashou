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



BACK = {
    "stardust": [
        ".................",
        "...w.............",
        ".............s...",
        "......hhhhs......",
        ".s...hhHHHhh.....",
        "....hhHeeeHhh....",
        "....hHeoooeHh....",
        "....hHeoooeHh....",
        "....hHeoooeHh....",
        "....hhHeeeHhh....",
        ".....hhHHHhh..w..",
        "......hhhhh......",
    ],
    "comet": [                      # from behind: the nucleus, its coma, and the tail streaming back
        "...............tt",
        ".............tttT",
        "....dddd...tttTT.",
        "...dcyyycdttTTT..",
        "..dcywwwycttTT...",
        "..dcyw wycuuT....".replace(" ", "w"),
        "..dcywwwycuu.....",
        "..dcyyyyycu......",
        "...dcyyycd.......",
        "....dddd.........",
        ".................",
        ".................",
    ],
    "planet": [
        "........h........",
        ".....hhwwohh.....",
        "....hGGooowwh....",
        "....hGggOOooh....",
        "...hGggOOOOoNh...",
        "...hGgOOOOOnnh...",
        "...hGOOOOOOnnh...",
        "...howwwOOOnnh...",
        "....hooOOOnNh....",
        "....hoooooNNh....",
        ".....hhwwohh.....",
        "........h........",
    ],
    "star": [
        "......ggggg......",
        "....gghhehhgg....",
        "...ghheoooehhg...",
        "...gheoyyyoehg...",
        "..gheoyywyyoehg..",
        "..gheoywwwyoehg..",
        "..gheoywwwyoehg..",
        "..gheoyywyyoehg..",
        "...gheoyyyoehg...",
        "...ghheoooehhg...",
        "....gghhehhgg....",
        "......ggggg......",
    ],
    "seedling": [
        ".................", ".................", "......LL.........", "......LlL........", ".......Lg........",
        "........g........", "......aagaa......", ".....aoooooa.....", "....aoooooooa....", "....aoooooooa....",
        ".....aoooooa.....", "......aaaaa......",
    ],
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


def back_of(form):
    """The form whose back view stands for `form`: itself, or the closest earlier form of its starter
    that has one (back views get drawn after the forms)."""
    if form in BACK:
        return form
    for forms in creatures.STARTERS.values():
        if form in forms:
            before = [f for f in reversed(forms[:forms.index(form)]) if f in BACK]
            after = [f for f in forms[forms.index(form):] if f in BACK]
            if before or after:
                return (before or after)[0]
    return "stardust"


def hero(form):
    """(frames, palette): the back view, then a step with each side (feet lifted, body up a pixel)."""
    form = back_of(form)
    base = BACK[form]
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
    "systemd": ((120, 190, 210), (50, 90, 110)),
    "logic": ((230, 190, 80), (150, 110, 50)),
    "sql": ((90, 170, 215), (40, 90, 130)),
    "network": ((70, 200, 190), (25, 110, 110)),
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

def symmetric(rows):
    """Rows trimmed to their left part and mirrored, so every boss stays symmetric."""
    half = [r[: (len(r) + 1) // 2] for r in rows]
    return [h + h[:-1][::-1] for h in half]


def monster(topic):
    body, dark = TOPIC_COLORS.get(topic, TOPIC_COLORS["bash"])
    return symmetric(MONSTER), {"a": dark, "o": body, "w": (255, 255, 255), "m": (25, 25, 25)}


CHEST = ([".aaaaaaa.", "aYyyyyyYa", "aaaaYaaaa", "ayyyyyyya", "ayyyyyyya", "aaaaaaaaa"],
         {"a": (110, 70, 35), "y": (175, 120, 60), "Y": (240, 200, 80)})
SIGNPOST = (["aaaaaaaaa", "ayyyyyyya", "aaaaaaaaa", "....b....", "....b....", "....b....", "...bbb..."],
            {"a": (120, 80, 40), "y": (220, 180, 110), "b": (100, 70, 40)})


def half(rows):
    """Rows from their left half (10 columns, the 10th is the middle): 19 wide, symmetric."""
    return [r + r[:9][::-1] for r in rows]


# topic: (rows, palette). Our own designs.
BOSSES = {
    "bash": (half([
        "..h.......", "..hh......", "...hhggggg", "..gggggggg", ".gggwwwggg", ".ggwwmwggg",
        ".gggwwwggg", ".ggggggggg", "..gdtdtdtd", "..gddddddd", "...ggggggg", ".GGggg$ggg",
        "GGGggggggg", ".G.ggggggg", "...gg.....", "..ggg.....",
    ]), {"h": (230, 220, 190), "g": (80, 170, 90), "G": (50, 120, 60), "w": (255, 255, 255),
         "m": (200, 40, 40), "d": (40, 30, 30), "t": (250, 250, 240), "$": (250, 220, 90)}),
    "linux": (half([
        "......rrrr", ".....rrrrr", "....ssssss", "...sbbbbbb", "...bbwwwbb", "..bbwmwwbb",
        "..bbwwwwbb", "..bbbwyyyy", ".bbbwwwwww", "sbbwwwwwww", "sbbwwwwwww", "s.bbwwwwww",
        "..bbbwwwww", "...bbbbbbb", "...yyy....", "..yyyy....",
    ]), {"r": (210, 50, 50), "s": (170, 175, 190), "b": (35, 35, 45), "w": (240, 240, 245),
         "m": (25, 25, 25), "y": (245, 190, 40)}),
    "python": ([
        "......bbbbb........", ".....bbbbbbb.......", "....bbwmbwmbb......", "....bbbbbbbbb......",
        ".....bbbrrbb.......", "......bbbb.........", ".......bbb.........", "........bbb........",
        "..yyyyyy..bbb......", ".yybbbbyyy.bbb.....", "yybb..bbbyy.bbb....", "yb......bbyy.bb....",
        "yb.......bbyybb....", ".yb......bbbbyy....", "..yyyyyyyyyyyy.....", "...yyyyyyyyyy......",
    ], {"b": (70, 125, 200), "y": (240, 205, 70), "w": (255, 255, 255), "m": (25, 25, 25), "r": (220, 60, 70)}),
    "rust": (half([
        "..oo......", ".oooo.....", "oo.oo.....", "oo.oo.....", ".ooo......", "..oo..w.w.",
        "..oo..m.m.", "...ooooooo", "..oooooooo", ".ooooddddd", "oooooooooo", ".o.ooooooo",
        "o.o.oooooo", "...o.o.o.o", "..o.o.o.o.", "..........",
    ]), {"o": (220, 105, 55), "d": (150, 60, 30), "w": (255, 255, 255), "m": (25, 25, 25)}),
    "c": (half([
        "....aaaaaa", "...aooooo0", "...aoylooo", "...aooooo0", "...aaoooaa", ".aaaoooooo",
        "aooaoo#ooo", "aooaoo##oo", "aoaoooo#oo", ".aaooooooo", "..aooooooo", "..aooaaaao",
        "..aooa....", "..aooa....", ".aaooa....", ".aaaaa....",
    ]), {"a": (80, 85, 100), "o": (140, 145, 160), "0": (140, 145, 160), "y": (120, 230, 255),
         "l": (230, 250, 255), "#": (40, 40, 50)}),
    "debian": (half([
        "......pppp", "....pppPPP", "...ppPPppp", "..pPPpp...", "..pPp..www", ".pPp..wmww",
        ".pPp..wwww", ".pPp...ppp", ".pPpp..ppP", "..pPPpppPP", "...ppPPPPp", "....pppppp",
        ".....pp.pp", "....p..p..", "...p..p...", "..........",
    ]), {"p": (215, 30, 90), "P": (150, 20, 60), "w": (255, 255, 255), "m": (25, 25, 25)}),
    "rocky": (half([                           # the Stone Titan: stacked boulders, moss on its head and shoulders
        "......gggg", ".....gglll", ".....sllll", ".....swwll", ".....swmll", ".....sllSS",
        "..ggg.sSSS", ".ggsssssss", "gsslssSlls", "ssls.sSlll", "sls..ssSls", "SSs..sslSs",
        "SSS..SssSs", ".....sss..", "....ssss..", "....SSSS..",
    ]), {"g": (40, 180, 120), "s": (140, 142, 138), "S": (90, 92, 90), "l": (185, 188, 182),
         "w": (255, 255, 255), "m": (25, 25, 25)}),
    "cicd": ([
        ".vv.......vv....vv.", "vwmv.....vwmv..vwmv", "vvvv.....vvvv..vvvv", ".vv.......vv....vv.",
        ".vv.......vv...vv..", "..vv......vv...vv..", "...vv.....vv..vv...", "....vv....vv.vv....",
        ".....vvvvvvvvvv....", "....vVVVVVVVVVVv...", "...vVVVVVVVVVVVVv..", "...vVVVVVVVVVVVVv..",
        "....vVVVVVVVVVVv...", ".....vvvvvvvvvv....", ".....vv......vv....", "....vvv......vvv...",
    ], {"v": (150, 95, 215), "V": (185, 140, 240), "w": (255, 255, 255), "m": (25, 25, 25)}),
    "systemd": (half([
        "........cc", ".......ccc", "......cccc", "....ccwwcc", "....ccwmcc", ".....ccccc",
        "......CCCC", "......cccc", "......cccc", ".....ccccc", "....cccccc", "...cccgccc",
        "..ccccgcCC", ".cccccgccc", "cccccccccc", ".ccccccccc",
    ]), {"c": (120, 190, 210), "C": (50, 90, 110), "g": (200, 210, 220), "w": (255, 255, 255),
         "m": (25, 25, 25)}),
    "logic": (half([
        "........ss", "......ssss", ".....sbsbs", "....sbsbsb", "....sbffff", "....sbfwmf",
        "....sbffff", "....sbfffm", "...sbs.fff", "...sbs..ff", "..ssss.lll", ".lllllllll",
        "llllllllll", "lLlllLllll", "lL.lL..lLl", "..........",
    ]), {"s": (230, 190, 80), "b": (60, 90, 170), "f": (210, 170, 120), "l": (200, 160, 80),
         "L": (150, 110, 50), "w": (255, 255, 255), "m": (25, 25, 25)}),
    "sql": (half([                             # the Deadlock Wyvern: two heads, each waiting for the other's lock
        "..........", ".gg.......", "gwmg......", "gggg......", ".gg.......", "..gg......",
        "...gg.....", "....gg....", "WW...gggg.", "WWW.gGGGGG", ".WWWgGGGyy", "..WWgGGyyk",
        "....gGGyyy", "....gGGGGG", ".....gg...", "....ggg...",
    ]), {"g": (50, 110, 160), "G": (110, 170, 215), "W": (80, 90, 150), "y": (230, 190, 70), "k": (60, 45, 30),
         "w": (255, 255, 255), "m": (25, 25, 25)}),
    "network": (half([                         # the Latency Kraken: its arms are cables, with plugs at the tips
        "......kkkk", "....kkKKKK", "...kKKKKKK", "..kKKKKKKK", "..kKwwKKKK", "..kKwmKKKK",
        "..kKKKKKKK", "...kKKKKKK", "....kKkKkK", "...kK.kK.k", "..kK..kK.k", ".kK..kK..k",
        ".k..kK...k", "yk..k....k", "y...y....y", "..........",
    ]), {"k": (25, 110, 110), "K": (70, 200, 190), "y": (230, 200, 80), "w": (255, 255, 255), "m": (25, 25, 25)}),
}


def boss(topic):
    return BOSSES.get(topic, BOSSES["bash"])


def pet(sprite_id):
    """A pet met on the road, by its sprite id (pets/<id>.json)."""
    p = creatures.get(sprite_id)
    return p.base, p.palette


# Every event of the road -> what stands on it, from the chapter's topic: (rows, palette).
AHEAD = {
    "monster": monster,
    "boss": boss,
    "chest": lambda topic: CHEST,
    "fork": lambda topic: SIGNPOST,
    "lesson": lambda topic: pet("barn_owl"),             # the Sage Owl
}


def ahead(kind, topic):
    return AHEAD[kind](topic)
