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
    "bash": ((90, 200, 110), (40, 120, 60)), "script": ((150, 175, 95), (85, 105, 55)),
    "linux": ((240, 200, 70), (150, 110, 30)),
    "python": ((80, 140, 220), (240, 210, 80)), "rust": ((220, 110, 60), (130, 60, 30)),
    "c": ((150, 160, 190), (80, 90, 120)), "debian": ((215, 30, 90), (120, 20, 50)),
    "rocky": ((60, 180, 140), (30, 100, 80)), "cicd": ((170, 110, 230), (90, 50, 140)),
    "logic": ((230, 190, 80), (150, 110, 50)),
    "sql": ((90, 170, 215), (40, 90, 130)),
    "network": ((70, 200, 190), (25, 110, 110)),
    "ai": ((125, 100, 220), (80, 60, 165)),
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
    "bash": ([                      # the Bash Beast: horns, brows, a $_ screen on its chest
        "h.................h", "hh...............hh", ".hh..GGGGGGGGG..hh.", "..hGGgggggggggGGh..",
        "..GgggggggggggggG..", ".GgBBBgggggggBBBgG.", ".GgyykgggGgggkyygG.", ".Gggggggg.gggggggG.",
        ".GgwkwkwkWkwkwkwgG.", ".GgkkkkkkkkkkkkkgG.", "GGggSSSSSSSSSSSggGG", "Gg.gS.$p_pppppSg.gG",
        "Gg.gSpppppppppSg.gG", "...gSSSSSSSSSSSg...", "...GGg.......gGG...", "..GGGG.......GGGG..",
    ], {"h": (235, 225, 195), "g": (80, 175, 95), "G": (40, 110, 55), "B": (30, 70, 35), "y": (250, 220, 80),
        "k": (25, 25, 25), "w": (255, 255, 240), "W": (210, 210, 195), "S": (60, 60, 70), "p": (20, 30, 25),
        "$": (110, 240, 120), "_": (110, 240, 120)}),
    "script": ([                      # the Errexit Ogre: one brow, tusks, a STOP sign in its fist
        "...................", "....GGGGGGGGGGG....", "RrrrRggggggggggG...", "rrrrrgggggggggggG..",
        "rwwwrBBBBBBBBBBgG..", "rrrrrkgggggggkwgG..", "RrrrRgggggggggggG..", "..nggt.ggggg.tggG..",
        "..nGgddddDddddgG...", "..nGgggggggggggGG..", ".GngGgggggggggGggG.", "GgngrrrrrRrrrrrgggG",
        "Gg.GrrrryRyrrrrG.gG", "...GGgggGGGgggGG...", "...GG.........GG...", "..GGG.........GGG..",
    ], {"g": (150, 178, 95), "G": (80, 104, 52), "B": (45, 55, 30), "w": (255, 255, 255), "k": (25, 25, 25),
        "t": (250, 245, 225), "d": (90, 40, 40), "D": (90, 40, 40), "r": (210, 55, 45), "R": (140, 30, 25),
        "y": (245, 195, 60), "n": (130, 90, 50)}),
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
        "......kkkk", "....kkKKKK", "...kKhhKKK", "..kKhKKKKK", "..kKkKKKKK", "..kKwkKKKK",
        "..kKwmKKKK", "..kKKKKKKK", "..kKsKKmmm", "...ksssKKK", "...cC..cC.", "..cC..cC..",
        ".cC...cC..", ".cC....cC.", "yyy...yyy.", "Y.Y...Y.Y.",
    ]), {"k": (20, 80, 85), "K": (70, 200, 190), "h": (170, 240, 230), "s": (40, 150, 145), "c": (35, 55, 70),
         "C": (80, 110, 130), "y": (230, 200, 80), "Y": (190, 190, 200), "w": (255, 255, 255), "m": (25, 25, 25)}),
    "ai": (half([                              # the Mirage Djinn: sure of itself, made of smoke from the waist down
        "........tt", "......tttt", ".....tTtgg", "....tTtttt", "....tTTTTt", ".....sssss",
        "....swmsss", "....sssshs", ".....ssmmm", "..yy..ssss", ".yhhssssss", "..yhhhhhhh",
        "....SssSSS", ".....kKKKK", "......kKKK", "........kK",
    ]), {"t": (235, 230, 215), "T": (185, 175, 160), "g": (240, 190, 50), "s": (125, 100, 220),
         "S": (80, 60, 165), "h": (170, 155, 245), "y": (240, 190, 50), "w": (255, 255, 255),
         "m": (25, 25, 25), "k": (160, 225, 235), "K": (95, 175, 205)}),
}


# The first Latency Kraken (cable arms one pixel wide): replaced in 0.9.1, kept for later (owner liked both).
KRAKEN_V1 = (half([
    "......kkkk", "....kkKKKK", "...kKKKKKK", "..kKKKKKKK", "..kKwwKKKK", "..kKwmKKKK",
    "..kKKKKKKK", "...kKKKKKK", "....kKkKkK", "...kK.kK.k", "..kK..kK.k", ".kK..kK..k",
    ".k..kK...k", "yk..k....k", "y...y....y", "..........",
]), {"k": (25, 110, 110), "K": (70, 200, 190), "y": (230, 200, 80), "w": (255, 255, 255), "m": (25, 25, 25)})

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
