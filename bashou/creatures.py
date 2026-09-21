"""Pet catalog: pixel sprites, poses and how each pet is unlocked.

A sprite is a grid of palette keys ('.' is transparent). A pose is a list of
(row, col, key) pixels painted over the base grid.
"""

from dataclasses import dataclass, field


def sprite(text, width=17):
    """Rows of a sprite, padded to `width` with transparent pixels."""
    rows = [row.ljust(width, ".") for row in text.strip().split("\n")]
    assert all(len(r) == width for r in rows), "sprite row too wide"
    return rows


def pixels(spec):
    """'8,0,a 8,1,o' -> [(8, 0, 'a'), (8, 1, 'o')]"""
    out = []
    for px in spec.split():
        r, c, k = px.split(",")
        out.append((int(r), int(c), k))
    return out


@dataclass
class Pet:
    id: str
    name: str
    base: list
    palette: dict
    poses: dict = field(default_factory=dict)
    stages: dict = field(default_factory=dict)   # stage number -> extra pixels (cumulative)
    z_at: tuple = (0, 13)       # terminal row / column of the 3-cell particle spot (z, ♪, ✦)
    unlock: str = ""            # human hint shown on the board

    @property
    def width(self):
        return len(self.base[0])


CAT = Pet(
    id="cat",
    name="Cat",
    base=[
        "...a......a......",
        "..apa....apa.....",
        "..appaaaappa.....",
        ".aooooooooooa....",
        ".aogwoooowgoa....",
        "aoogmoooomgooa...",
        "aooooonnoooooa...",
        ".aaooooooooaa....",
        ".aoooccccoooa....",
        "aoooccccccoooa.aa",
        "alloccccccollaaoa",
        ".aaaaaaaaaaaaaaa.",
    ],
    palette={
        "a": (214, 140, 40), "o": (245, 167, 52), "l": (255, 196, 110), "c": (255, 236, 205),
        "p": (255, 176, 166), "n": (190, 100, 100), "g": (150, 210, 110), "m": (25, 25, 25),
        "w": (255, 255, 255), "r": (220, 70, 80), "R": (165, 45, 60), "y": (250, 210, 70),
        "Y": (205, 150, 30), "b": (110, 170, 255),
    },
    poses={
        "fidget": pixels("0,3,. 0,2,a"),
        "inhale": pixels("8,0,a 8,1,o 8,12,o 8,13,a"),
        "closed": pixels("4,3,o 4,4,o 4,9,o 4,10,o 5,3,a 5,4,a 5,9,a 5,10,a"),
        "left": pixels("5,3,m 5,4,g 5,9,m 5,10,g"),
        "right": pixels("5,3,g 5,4,m 5,9,g 5,10,m"),
        "tail_up": pixels("5,15,a 6,14,a 6,15,o 6,16,a 7,14,a 7,15,o 7,16,a "
                          "8,14,a 8,15,o 8,16,a 9,14,a 9,15,o 9,16,a"),
        "wash1": pixels("6,2,l 6,3,l 7,2,l 7,3,l 10,1,o 10,2,o"),
        "wash2": pixels("5,4,l 5,5,l 6,4,l 6,5,l 7,6,p 10,1,o 10,2,o"),
    },
)

# Every pet in board order.
ROSTER = [
    ("bat", "Bat"), ("frog", "Frog"), ("turtle", "Turtle"), ("mushroom", "Mushroom"),
    ("slime", "Slime"), ("sofa", "Living sofa"), ("octopus", "Octopus"), ("dragon", "Dragon"),
    ("fox", "Fox"), ("owl", "Owl"), ("mole", "Mole"), ("snake", "Snake"),
    ("ghost", "Ghost"), ("spider", "Spider"), ("ant", "Ant"), ("axolotl", "Axolotl"),
]
NAMES = dict(ROSTER)

# Names of the three stages: unlocked, evolved (2 achievements), legendary (whole family).
STAGES = {
    "bat": ("Batling", "Bat", "Night bat"),
    "frog": ("Tadpole", "Frog", "Frog prince"),
    "turtle": ("Hatchling", "Turtle", "Elder turtle"),
    "mushroom": ("Spore", "Mushroom", "Glowshroom"),
    "slime": ("Droplet", "Slime", "King slime"),
    "sofa": ("Cushion", "Living sofa", "Throne"),
    "octopus": ("Octopup", "Octopus", "Kraken"),
    "dragon": ("Dragon egg", "Dragon", "Elder dragon"),
    "fox": ("Fox cub", "Fox", "Nine-tailed fox"),
    "owl": ("Owlet", "Owl", "Grand owl"),
    "mole": ("Molekin", "Mole", "Mole king"),
    "snake": ("Snakelet", "Snake", "Great serpent"),
    "ghost": ("Wisp", "Ghost", "Phantom"),
    "spider": ("Spiderling", "Spider", "Weaver"),
    "ant": ("Ant", "Soldier ant", "Ant queen"),
    "axolotl": ("Axolittle", "Axolotl", "Axolord"),
}
FROG = Pet(
    id="frog", name="Frog",
    base=sprite("""
..aaa.....aaa..
.awwwa...awwwa.
.awmwa...awmwa.
aoooooooooooooa
aoooooooooooooa
aopooooooooopoa
.aoooaaaaaoooa.
.aoocccccccooa.
aoocccccccccooa
aoocccccccccooa
allocccccccolla
.aaaaaaaaaaaaa.
"""),
    palette={"a": (60, 130, 60), "o": (110, 190, 80), "l": (165, 220, 110), "c": (225, 240, 180),
             "w": (255, 255, 255), "m": (25, 25, 25), "p": (255, 160, 160)},
    poses={
        "fidget": pixels("6,5,c 6,6,c 6,7,c 6,8,c 6,9,c"),
        "inhale": pixels("7,0,a 7,1,o 7,3,c 7,11,c 7,13,o 7,14,a"),
        "closed": pixels("1,2,o 1,3,o 1,4,o 2,2,a 2,3,a 2,4,a 1,10,o 1,11,o 1,12,o 2,10,a 2,11,a 2,12,a"),
        "left": pixels("2,2,m 2,3,w 2,10,m 2,11,w"),
        "right": pixels("2,3,w 2,4,m 2,11,w 2,12,m"),
    },
    z_at=(0, 14),
)

TURTLE = Pet(
    id="turtle", name="Turtle",
    base=sprite("""
................
................
................
....SSSSSSS.....
..SShhhShhhSS...
.ShhhhShhhhhS...
ShhhhShhhhShhS.gg
SSSSSSSSSSSSSSgmg
.eggeeeeeeeggeggg
.gg.gg...gg.gg...
................
................
"""),
    palette={"S": (120, 85, 45), "h": (175, 130, 70), "g": (130, 190, 90), "e": (95, 150, 70),
             "m": (25, 25, 25)},
    poses={
        "fidget": pixels("6,15,. 6,16,. 7,14,S 7,15,. 7,16,. 8,14,. 8,15,. 8,16,."),
        "left": pixels("7,15,g 7,14,m"),
        "right": pixels("7,15,g 7,16,m"),
        "inhale": pixels("3,3,S 3,11,S"),
        "closed": pixels("7,15,e"),
    },
    z_at=(1, 13),
)

MUSHROOM = Pet(
    id="mushroom", name="Mushroom",
    base=sprite("""
....aaaaaaa....
..aarrrrwwraa..
.arwwrrrrwwrra.
arrwwrrrrrrrwra
arrrrrwwrrrrrra
.aaaaaaaaaaaaa.
...scccccccs...
...ccmcccmccc..
...ccmcccmccc..
...cpccnccpcc..
..sccccccccccs.
..sssssssssss..
"""),
    palette={"a": (170, 40, 50), "r": (225, 70, 70), "w": (255, 245, 235), "s": (215, 195, 160),
             "c": (245, 232, 205), "m": (25, 25, 25), "p": (255, 170, 170), "n": (150, 80, 80)},
    poses={
        "fidget": pixels("1,8,r 1,9,r 1,6,w 1,7,w 4,6,r 4,7,r 4,8,w 4,9,w"),
        "left": pixels("7,5,c 8,5,c 7,4,m 8,4,m 7,9,c 8,9,c 7,8,m 8,8,m"),
        "right": pixels("7,5,c 8,5,c 7,6,m 8,6,m 7,9,c 8,9,c 7,10,m 8,10,m"),
        "inhale": pixels("1,1,a 2,0,a 5,0,a 5,14,a"),
        "closed": pixels("7,5,c 7,9,c"),
    },
)

FOX = Pet(
    id="fox", name="Fox",
    base=sprite("""
.k.......k.......
kak.....kak......
aoaaaaaaaoa......
aomooooomoa......
aomooooomoa......
awwooooowwa......
.awwwkwwwa.......
..awwwwwa....aaa.
.aoowwwooa..aooa.
aooowwwoooa.aoowa
aowwoooowwoaaowwa
.aaaaaaaaaaaaaaa.
"""),
    palette={"k": (60, 40, 35), "a": (200, 95, 35), "o": (240, 130, 50), "w": (255, 245, 235),
             "m": (25, 25, 25)},
    poses={
        "fidget": pixels("0,1,. 0,0,k"),
        "inhale": pixels("8,0,a 8,1,o 8,9,o 8,10,a"),
        "closed": pixels("3,2,o 3,8,o 4,2,k 4,3,k 4,7,k 4,8,k"),
        "left": pixels("3,2,o 4,2,o 3,1,m 4,1,m 3,8,o 4,8,o 3,7,m 4,7,m"),
        "right": pixels("3,2,o 4,2,o 3,3,m 4,3,m 3,8,o 4,8,o 3,9,m 4,9,m"),
        "tail_up": pixels("3,13,w 3,14,w 4,12,a 4,13,w 4,14,w 4,15,a 5,12,a 5,13,o 5,14,o 5,15,a "
                          "6,12,a 6,13,o 6,14,o 6,15,a 7,12,a 7,13,o 7,14,o 7,15,a 8,13,o 8,14,o 8,15,a "
                          "9,13,o 9,14,o 9,15,a 10,13,o 10,14,a 10,15,."),
    },
)

OWL = Pet(
    id="owl", name="Owl",
    base=sprite("""
.a...........a.
.aa.........aa.
.aoaaaaaaaaaoa.
aowwwoaaaowwwoa
awyyywoaowyyywa
awymywooowymywa
awyyywoyowyyywa
aowwwoyyyowwwoa
aooocclcclcooaa
aaoclcclcclcaaa
.aoocclccclooa.
..aayy...yyaa..
"""),
    palette={"a": (110, 75, 45), "o": (160, 115, 70), "w": (245, 235, 215), "y": (245, 190, 60),
             "m": (25, 25, 25), "c": (225, 205, 170), "l": (150, 110, 70)},
    poses={
        "fidget": pixels("0,1,. 0,0,a 0,13,. 0,14,a"),
        "inhale": pixels("9,0,a 10,0,a 10,14,a"),
        "closed": pixels("4,2,w 4,3,w 4,4,w 5,2,a 5,3,a 5,4,a 6,2,w 6,3,w 6,4,w "
                         "4,10,w 4,11,w 4,12,w 5,10,a 5,11,a 5,12,a 6,10,w 6,11,w 6,12,w"),
        "left": pixels("5,3,y 5,2,m 5,11,y 5,10,m"),
        "right": pixels("5,3,y 5,4,m 5,11,y 5,12,m"),
    },
    z_at=(0, 14),
)

GHOST = Pet(
    id="ghost", name="Ghost",
    base=sprite("""
....aaaaaa.....
..aawwwwwwaa...
.awwwwwwwwwwa..
awwwwwwwwwwwwa.
awwmmwwwwmmwwa.
awwmmwwwwmmwwa.
awpwwwwmwwwpwa.
awwwwwwwwwwwwa.
awwwwwwwwwwwwa.
awwwwwwwwwwwwa.
awwaawwaawwaawa
.aa..aa..aa..a.
"""),
    palette={"a": (150, 170, 220), "w": (240, 245, 255), "m": (40, 40, 60), "p": (255, 180, 200)},
    poses={
        "fidget": pixels("10,3,w 10,5,a 10,7,w 10,9,a 10,11,w 10,13,a 11,1,. 11,3,a 11,5,. 11,7,a 11,9,. 11,11,a 11,13,. 11,14,a"),
        "inhale": pixels("7,14,a 8,14,a"),
        "closed": pixels("4,3,w 4,4,w 4,9,w 4,10,w"),
        "left": pixels("4,4,w 5,4,w 4,10,w 5,10,w 4,2,m 5,2,m 4,8,m 5,8,m"),
        "right": pixels("4,3,w 5,3,w 4,9,w 5,9,w 4,5,m 5,5,m 4,11,m 5,11,m"),
    },
)

SLIME = Pet(
    id="slime", name="Slime",
    base=sprite("""
.......a.........
......aoa........
.....awooa.......
....awooooa......
...awooooooa.....
..aoooooooooa....
.aooomooomoooa...
.aooomooomoooa...
.aopoooqooopoa...
.aoooooooooooa...
..aoooooooooa....
...aaaaaaaaa.....
"""),
    palette={"a": (50, 150, 130), "o": (110, 215, 185), "w": (230, 255, 245), "m": (25, 25, 25), "p": (255, 160, 170), "q": (40, 100, 85)},
    poses={
        "fidget": pixels("0,7,. 0,8,a 1,6,. 1,7,a 1,8,o 1,9,a"),
        "inhale": pixels("10,1,a 10,2,o 10,12,o 10,13,a 11,2,a 11,12,a"),
        "closed": pixels("6,5,o 6,9,o 7,4,q 7,5,q 7,9,q 7,10,q"),
        "left": pixels("6,5,o 7,5,o 6,4,m 7,4,m 6,9,o 7,9,o 6,8,m 7,8,m"),
        "right": pixels("6,5,o 7,5,o 6,6,m 7,6,m 6,9,o 7,9,o 6,10,m 7,10,m"),
    },
)

SOFA = Pet(
    id="sofa", name="Living sofa",
    base=sprite("""
.................
.................
..aaaaaaaaaaa....
.aoooooooooooa...
.aoooomomooooa...
.aoooomomooooa...
.aoooooqoooooa...
aoacccccccccaoa..
aoaclllllllcaoa..
aoaaaaaaaaaaaoa..
aoooooooooooooa..
.kk.........kk...
"""),
    palette={"a": (140, 50, 60), "o": (205, 85, 95), "c": (235, 200, 150), "l": (250, 225, 185), "m": (25, 25, 25), "q": (110, 35, 45), "k": (90, 60, 40)},
    poses={
        "fidget": pixels("8,4,c 8,5,c 8,9,c 8,10,c"),
        "inhale": pixels("7,4,l 7,5,l 7,6,l 7,7,l 7,8,l 7,9,l 7,10,l"),
        "closed": pixels("4,6,o 4,8,o"),
        "left": pixels("4,6,o 5,6,o 4,8,o 5,8,o 4,5,m 5,5,m 4,7,m 5,7,m"),
        "right": pixels("4,6,o 5,6,o 4,8,o 5,8,o 4,7,m 5,7,m 4,9,m 5,9,m"),
    },
)

OCTOPUS = Pet(
    id="octopus", name="Octopus",
    base=sprite("""
.....aaaaa.......
...aaoooooaa.....
..aoowwoooooa....
.aoowooooooooa...
.aoomooooomooa...
.aoomooooomooa...
.aopoooqooopoa...
..aoooooooooa....
.aoa.aoaoa.aoa...
ao...ao.oa...oa..
.a....a.a....a...
.................
"""),
    palette={"a": (110, 65, 150), "o": (180, 125, 220), "w": (235, 220, 255), "m": (25, 25, 25), "p": (255, 160, 170), "q": (80, 40, 110)},
    poses={
        "fidget": pixels("9,0,. 10,1,. 8,0,a 7,1,a"),
        "inhale": pixels("7,1,a 7,2,o 7,12,o 7,13,a"),
        "closed": pixels("4,4,o 4,10,o 5,3,q 5,4,q 5,10,q 5,11,q"),
        "left": pixels("4,4,o 5,4,o 4,3,m 5,3,m 4,10,o 5,10,o 4,9,m 5,9,m"),
        "right": pixels("4,4,o 5,4,o 4,5,m 5,5,m 4,10,o 5,10,o 4,11,m 5,11,m"),
    },
)

DRAGON = Pet(
    id="dragon", name="Dragon",
    base=sprite("""
..y.......y......
..yaaaaaaay......
.aoooooooooa.....
.aomwooowmoa.....
.aommooommoa.....
.aooononoooa.....
..aoooooooa......
v.aocccccoa.v....
vvaocccccoavv....
.vaocccccoav...ay
..aoooooooa.aooa.
..ll.aaa.ll.aaa..
"""),
    palette={"a": (45, 115, 70), "o": (90, 180, 100), "c": (240, 220, 140), "y": (250, 230, 170), "m": (25, 25, 25), "w": (255, 255, 255), "n": (35, 85, 50), "v": (130, 90, 190), "l": (250, 230, 170)},
    poses={
        "fidget": pixels("6,0,v 6,12,v 9,1,. 9,11,. 8,1,. 8,11,."),
        "right": pixels("3,3,m 3,4,w 3,8,m 3,9,w"),
        "inhale": pixels("6,1,a 6,2,o 6,10,o 6,11,a"),
        "closed": pixels("3,3,o 3,4,o 3,8,o 3,9,o"),
        "left": pixels("3,3,w 3,4,m 3,8,w 3,9,m"),
        "tail_up": pixels("8,15,a 8,16,y 9,15,o 9,16,a"),
    },
)

MOLE = Pet(
    id="mole", name="Mole",
    base=sprite("""
.................
.................
....aaaaaaa......
..aaoooooooaa....
.aoooooooooooa...
.aoomooooomooa...
aooooccnccooooa..
aooocccccccoooa..
llooooqoqooooll..
lllooooooooolll..
.aoooooooooooa...
..aaaaaaaaaaa....
"""),
    palette={"a": (80, 60, 55), "o": (125, 100, 90), "c": (215, 190, 170), "n": (255, 140, 160), "m": (25, 25, 25), "l": (250, 200, 190), "q": (70, 50, 45)},
    poses={
        "fidget": pixels("6,7,c 5,7,n"),
        "inhale": pixels("4,0,a 4,1,o 4,13,o 4,14,a"),
        "closed": pixels("5,3,m 5,11,m"),
        "left": pixels("5,4,o 5,3,m 5,10,o 5,9,m"),
        "right": pixels("5,4,o 5,5,m 5,10,o 5,11,m"),
    },
)

SNAKE = Pet(
    id="snake", name="Snake",
    base=sprite("""
......aaaa.......
.....aoooooa.....
....aomoooomoa...
....aoooooooooa..
.....aopooopaa...
......aaoooaa....
....aaaoooaaaa...
...aoooooooooooa.
..aollllllllllloa
..aaoooooooooooa.
.aoooooooooooooa.
..aaaaaaaaaaaaa..
"""),
    palette={"a": (50, 110, 50), "o": (120, 190, 80), "l": (215, 230, 140), "m": (25, 25, 25), "p": (255, 160, 170), "r": (230, 70, 80)},
    poses={
        "fidget": pixels("4,14,r 4,15,r 5,15,r"),
        "inhale": pixels("10,0,a 10,15,o 10,16,a"),
        "closed": pixels("2,6,o 2,11,o 3,6,a 3,11,a"),
        "left": pixels("2,6,o 2,5,m 2,11,o 2,10,m"),
        "right": pixels("2,6,o 2,7,m 2,11,o 2,12,m"),
        "tail_up": pixels("4,14,r 4,15,r 5,15,r"),
    },
)

SPIDER = Pet(
    id="spider", name="Spider",
    base=sprite("""
.................
.................
.a...aaaaaaa...a.
.a..aoooooooa..a.
..aaoowwowwooaa..
aa.aoowmomwooa.aa
..aaoooooooooaa..
.a.aoopoqopooa.a.
a..aoooooooooa..a
.aa.aaoooooaa.aa.
a....aaaaaaa....a
.................
"""),
    palette={"a": (140, 115, 185), "o": (95, 72, 130), "w": (255, 255, 255), "m": (25, 25, 25), "p": (255, 160, 170), "q": (40, 25, 55)},
    poses={
        "fidget": pixels("10,0,. 9,0,a 10,16,. 9,16,a"),
        "inhale": pixels("3,3,a 3,4,o 3,12,o 3,13,a"),
        "closed": pixels("4,6,o 4,7,o 4,9,o 4,10,o 5,6,m 5,7,m 5,9,m 5,10,m"),
        "left": pixels("5,7,w 5,6,m"),
        "right": pixels("5,9,w 5,10,m"),
    },
)

ANT = Pet(
    id="ant", name="Ant",
    base=sprite("""
..a...a..........
...a.a...........
..aaaaa..........
.aoooooa.........
.aomoooa...aaaa..
.aooooqa.aaooooa.
..aaaaaaaoooooooa
....a.aooaooooooa
...a..a.aa.aaaaa.
..a..a...a..a..a.
.........a...a..a
.................
"""),
    palette={"a": (110, 40, 35), "o": (190, 75, 60), "m": (25, 25, 25), "q": (80, 25, 20)},
    poses={
        "fidget": pixels("0,6,. 0,7,a"),
        "inhale": pixels("4,10,a 4,15,a"),
        "closed": pixels("4,3,q 4,4,q"),
        "left": pixels("4,3,o 4,2,m"),
        "right": pixels("4,3,o 4,4,m"),
    },
)

AXOLOTL = Pet(
    id="axolotl", name="Axolotl",
    base=sprite("""
.................
....aaaaaaa......
gg.aoooooooa.gg..
..aoooooooooa....
gg.aomooomoa.gg..
..aoomooomooa....
g..aopoqopoa..g..
...aoooooooa....a
...accccccca...ao
..aocccccccoa.ao.
..lao.ooo.oal..oa
...aa.....aa.....
"""),
    palette={"a": (220, 110, 150), "o": (255, 175, 200), "c": (255, 225, 230), "g": (200, 70, 130), "m": (25, 25, 25), "p": (255, 120, 150), "q": (170, 60, 100), "l": (255, 175, 200)},
    poses={
        "fidget": pixels("2,0,. 3,0,g 2,14,. 3,14,g"),
        "inhale": pixels("8,2,a 8,3,o 8,11,o 8,12,a"),
        "closed": pixels("4,5,o 4,9,o 5,4,q 5,5,q 5,9,q 5,10,q"),
        "left": pixels("4,5,o 5,5,o 4,4,m 5,4,m 4,9,o 5,9,o 4,8,m 5,8,m"),
        "right": pixels("4,5,o 5,5,o 4,6,m 5,6,m 4,9,o 5,9,o 4,10,m 5,10,m"),
    },
)

KITTEN = Pet(
    id="kitten", name="Kitten",
    base=sprite("""
.................
.................
.................
.................
.a.......a.......
.paaaaaaap.......
aoooooooooa......
aogwooowgoa......
aogmooomgoa.a....
aopoonoopoa.a....
.aocccccoa.a.....
.aaaaaaaaa.......
"""),
    palette={"a": (214, 140, 40), "o": (245, 167, 52), "c": (255, 236, 205), "p": (255, 176, 166), "n": (190, 100, 100), "g": (150, 210, 110), "m": (25, 25, 25), "w": (255, 255, 255)},
    poses={
        "inhale": pixels("10,0,a 10,1,o 10,9,o 10,10,a"),
        "closed": pixels("7,2,o 7,3,o 7,7,o 7,8,o 8,2,a 8,3,a 8,7,a 8,8,a"),
        "left": pixels("8,2,m 8,3,g"),
        "right": pixels("8,7,g 8,8,m"),
        "fidget": pixels("4,1,. 4,0,a"),
        "tail_up": pixels("10,11,. 9,12,. 7,12,a 6,12,a"),
    },
)

LION = Pet(
    id="lion", name="Lion",
    base=sprite("""
...NNNNNNNNN.....
..NMMMMMMMMMN....
.NMMaoooooaMMN...
NMMaogwowgoaMMN..
NMMaogmomgoaMMN..
NMMaooonoooaMMN..
.NMMacncncaMMN..N
..NMMacccaMMN...M
...aoooooooa...a.
..aoocccccooa.a..
.aoocccccccooaa..
.lla.aaaaa.all...
"""),
    palette={"a": (214, 140, 40), "o": (245, 167, 52), "l": (255, 196, 110), "c": (255, 236, 205), "n": (190, 100, 100), "g": (150, 210, 110), "m": (25, 25, 25), "w": (255, 255, 255), "M": (165, 90, 35), "N": (200, 115, 40)},
    poses={
        "inhale": pixels("8,2,a 8,3,o 8,11,o 8,12,a"),
        "closed": pixels("3,5,o 3,6,o 3,8,o 3,9,o 4,5,a 4,6,a 4,8,a 4,9,a"),
        "left": pixels("4,5,m 4,6,g 4,8,m 4,9,g"),
        "right": pixels("4,5,g 4,6,m 4,8,g 4,9,m"),
        "fidget": pixels("0,3,. 0,11,. 2,0,N 2,14,N"),
        "tail_up": pixels("5,16,N 6,16,M 7,16,a 8,15,."),
    },
)

SEEDLING = Pet(
    id="seedling", name="Seedling",
    base=sprite("""
.................
.................
.................
.LL...LL.........
LlLL.LLlL........
.LLLgLLL.........
....g............
..aaaaa..........
.aoooooa.........
aomooomoa........
aoponopoa........
.aaaaaaa.........
"""),
    palette={"a": (140, 95, 55), "o": (205, 155, 100), "L": (80, 160, 75), "l": (150, 210, 110), "g": (60, 120, 55), "m": (25, 25, 25), "p": (255, 160, 150), "n": (120, 70, 40)},
    poses={
        "inhale": pixels("8,0,a 8,1,o 8,7,o 8,8,a"),
        "closed": pixels("9,2,n 9,3,n 9,5,n 9,6,n"),
        "left": pixels("9,2,o 9,1,m 9,6,o 9,5,m"),
        "right": pixels("9,2,o 9,3,m 9,6,o 9,7,m"),
        "fidget": pixels("3,1,. 3,2,. 2,1,L 2,2,L"),
    },
)

SPROUT = Pet(
    id="sprout", name="Sprout",
    base=sprite("""
...LL...LL.......
..LlLL.LLlL......
.LlllL.LlllL.....
.LLLLLgLLLLL.....
..LL..g..LL......
......g..........
...aaaaaaa.......
..aoooooooa......
.aomooooomoa.....
.aopoonoopoa.....
..aoooooooa......
...aaaaaaa.......
"""),
    palette={"a": (140, 95, 55), "o": (205, 155, 100), "L": (80, 160, 75), "l": (150, 210, 110), "g": (60, 120, 55), "m": (25, 25, 25), "p": (255, 160, 150), "n": (120, 70, 40)},
    poses={
        "inhale": pixels("7,1,a 7,2,o 7,10,o 7,11,a"),
        "closed": pixels("8,2,n 8,3,n 8,9,n 8,10,n"),
        "left": pixels("8,3,o 8,2,m 8,9,o 8,8,m"),
        "right": pixels("8,3,o 8,4,m 8,9,o 8,10,m"),
        "fidget": pixels("0,3,. 0,9,. 1,2,. 1,10,."),
    },
)

TREE = Pet(
    id="tree", name="Tree spirit",
    base=sprite("""
....ddddddd......
..ddLLLLLLLdd....
.dLLlLLfLLlLLd...
dLLlLLLLLLLlLLd..
dLLLLfLLLfLLLLd..
.ddLLLLLLLLLdd...
...dtTTTTTtd.....
g..tTmTTTmTt..g..
.g.tpTTnTTpt.g...
..gtTTTTTTTtg....
...tTTTTTTTt.....
..ttt.ttt.ttt....
"""),
    palette={"L": (80, 160, 75), "l": (150, 210, 110), "g": (60, 120, 55), "m": (25, 25, 25), "p": (255, 160, 150), "n": (120, 70, 40), "d": (50, 115, 60), "t": (125, 85, 50), "T": (170, 120, 75), "f": (255, 200, 220)},
    poses={
        "inhale": pixels("0,3,d 0,11,d 5,1,d 5,13,d"),
        "closed": pixels("7,5,t 7,4,t 7,9,t 7,10,t"),
        "left": pixels("7,5,T 7,4,m 7,9,T 7,8,m"),
        "right": pixels("7,5,T 7,6,m 7,9,T 7,10,m"),
        "fidget": pixels("9,2,. 9,12,. 6,0,g 6,14,g"),
    },
)

PEBBLE = Pet(
    id="pebble", name="Pebble",
    base=sprite("""
.................
.................
.................
.................
.................
.................
...aaaaa.........
.aaololoaa.......
aoooooooooa......
aomooooomoa......
aopoonoopoa......
.aaaaaaaaa.......
"""),
    palette={"a": (85, 90, 100), "o": (140, 145, 155), "l": (185, 190, 200), "m": (25, 25, 25), "p": (255, 160, 170), "n": (60, 60, 70)},
    poses={
        "inhale": pixels("7,0,a 7,10,a"),
        "closed": pixels("9,2,n 9,1,n 9,8,n 9,9,n"),
        "left": pixels("9,2,o 9,1,m 9,8,o 9,7,m"),
        "right": pixels("9,2,o 9,3,m 9,8,o 9,9,m"),
        "fidget": pixels("6,3,. 6,8,a"),
    },
)

GOLEM = Pet(
    id="golem", name="Rock golem",
    base=sprite("""
....GGGGG........
...aGGoGGa.......
..aoooooooa......
..aomooomoa......
..aoooooooa......
..aoponopoa......
aaaoooooooaaa....
aoaoooooooaoa....
aoaoooooooaoa....
.a.aoooooa.a.....
...aoaaaoa.......
..aaa...aaa......
"""),
    palette={"a": (85, 90, 100), "o": (140, 145, 155), "G": (110, 165, 80), "m": (25, 25, 25), "p": (255, 160, 170), "n": (60, 60, 70)},
    poses={
        "inhale": pixels("5,0,a 5,1,a 5,11,a 5,12,a"),
        "closed": pixels("3,4,n 3,3,n 3,8,n 3,9,n"),
        "left": pixels("3,4,o 3,3,m 3,8,o 3,7,m"),
        "right": pixels("3,4,o 3,5,m 3,8,o 3,9,m"),
        "fidget": pixels("0,6,p"),
    },
)

CRYSTAL = Pet(
    id="crystal", name="Crystal golem",
    base=sprite("""
C......c......C..
cC...aCcCa...Cc..
cc..aoooooa..cc..
.a.aoooooooa.a...
ac.aomooomoa.ca..
aCaaoooooooaaCa..
aooaoponopoaooa..
aooaoooooooaooa..
.a.aoooooooa.a...
...aoocccooa.....
...aoaaaaaoa.....
..aaa.....aaa....
"""),
    palette={"a": (85, 90, 100), "o": (140, 145, 155), "m": (25, 25, 25), "p": (255, 160, 170), "n": (60, 60, 70), "c": (110, 215, 235), "C": (200, 245, 255)},
    poses={
        "inhale": pixels("9,6,C 9,7,C 9,8,C"),
        "closed": pixels("4,5,n 4,4,n 4,9,n 4,10,n"),
        "left": pixels("4,5,o 4,4,m 4,9,o 4,8,m"),
        "right": pixels("4,5,o 4,6,m 4,9,o 4,10,m"),
        "fidget": pixels("0,0,c 1,0,C 0,14,c 1,14,C 1,7,C 1,8,c"),
    },
    z_at=(0, 10),
)

BAT = Pet(
    id="bat", name="Bat",
    base=sprite("""
.................
.....a.....a.....
W....aa...aa....W
WW..aoooooooa..WW
WWWaoooeoeoooaWWW
WWWaoowmomwooaWWW
WWWWaoooooooaWWWW
.WWWaopowopoaWWW.
.W.WaoooooooaW.W.
....WaaoooaaW....
......a.a.a......
.................
"""),
    palette={"W": (70, 55, 95), "a": (90, 75, 120), "o": (125, 105, 160), "m": (25, 25, 25), "w": (255, 255, 255), "p": (255, 170, 190), "e": (245, 225, 245)},
    poses={
        "inhale": pixels("7,0,W 7,16,W"),
        "closed": pixels("4,7,o 4,9,o 5,7,a 5,9,a"),
        "left": pixels("5,6,m 5,7,w"),
        "right": pixels("5,9,w 5,10,m"),
        "fidget": pixels("2,0,. 2,16,. 3,0,. 3,16,. 8,1,. 8,15,."),
    },
)

# Starters: chosen once, they level up with every 5 achievements and change shape at levels 4 and 7.
STARTERS = {
    "cat": ("kitten", "cat", "lion"),
    "sprout": ("seedling", "sprout", "tree"),
    "pebble": ("pebble", "golem", "crystal"),
}
FORM_NAMES = {"kitten": "Kitten", "cat": "Cat", "lion": "Lion", "seedling": "Seedling", "sprout": "Sprout",
              "tree": "Tree spirit", "pebble": "Pebble", "golem": "Rock golem", "crystal": "Crystal golem"}
STARTER_BLURBS = {
    "cat": "Curious and cuddly. Knows every shortcut of your shell.",
    "sprout": "Calm and patient. Grows scripts from tiny seeds.",
    "pebble": "Solid and loyal. Knows the filesystem rock by rock.",
}

PETS = {p.id: p for p in (KITTEN, CAT, LION, SEEDLING, SPROUT, TREE, PEBBLE, GOLEM, CRYSTAL,
                         BAT, FROG, TURTLE, MUSHROOM, SLIME, SOFA, OCTOPUS, DRAGON,
                         FOX, OWL, MOLE, SNAKE, GHOST, SPIDER, ANT, AXOLOTL)}


def get(pet_id):
    return PETS.get(pet_id, KITTEN)
