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
    unlock="your first friend",
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
    stages={
        2: pixels("7,1,R 7,2,r 7,3,r 7,4,r 7,5,r 7,6,r 7,7,r 7,8,r 7,9,r 7,10,r 7,11,r 7,12,R "
                  "8,9,r 8,10,r 9,10,R"),
        3: pixels("7,1,R 7,2,r 7,3,r 7,4,r 7,5,r 7,6,r 7,7,r 7,8,r 7,9,r 7,10,r 7,11,r 7,12,R "
                  "8,9,r 8,10,r 9,10,R "
                  "0,5,y 0,8,y 1,5,y 1,6,y 1,7,y 1,8,y 2,5,Y 2,6,b 2,7,b 2,8,Y"),
    },
    poses={
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

# Every pet in board order. Pets without art yet reuse the cat until they are drawn.
ROSTER = [
    ("cat", "Cat"), ("frog", "Frog"), ("turtle", "Turtle"), ("mushroom", "Mushroom"),
    ("slime", "Slime"), ("sofa", "Living sofa"), ("octopus", "Octopus"), ("dragon", "Dragon"),
    ("fox", "Fox"), ("owl", "Owl"), ("mole", "Mole"), ("snake", "Snake"),
    ("ghost", "Ghost"), ("spider", "Spider"), ("ant", "Ant"), ("axolotl", "Axolotl"),
]
NAMES = dict(ROSTER)

# Names of the three stages: unlocked, evolved (2 achievements), legendary (whole family).
STAGES = {
    "cat": ("Cat", "Scarf cat", "Cat king"),
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
        "inhale": pixels("7,14,a 8,14,a"),
        "closed": pixels("4,3,w 4,4,w 4,9,w 4,10,w"),
        "left": pixels("4,4,w 5,4,w 4,10,w 5,10,w 4,2,m 5,2,m 4,8,m 5,8,m"),
        "right": pixels("4,3,w 5,3,w 4,9,w 5,9,w 4,5,m 5,5,m 4,11,m 5,11,m"),
    },
)

PETS = {p.id: p for p in (CAT, FROG, TURTLE, MUSHROOM, FOX, OWL, GHOST)}


def get(pet_id):
    return PETS.get(pet_id, CAT)
