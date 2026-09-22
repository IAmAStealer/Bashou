"""Pet catalog: pixel sprites, poses and how each pet is unlocked.

The art lives in pets/<id>.json (see doc/contributing/pixel-art.md): a grid of palette keys
('.' is transparent), and poses painted over it, row by row ('-' keeps the pixel below).
"""

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

ART = Path(__file__).resolve().parent / "pets"


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
    idle: str = "breathe"       # what it does when nothing happens: "breathe" (inhale) or "swim" (swim_up/down)

    @property
    def width(self):
        return len(self.base[0])


POSES = ("inhale", "closed", "left", "right", "fidget")     # every pet has these (idle "swim": no inhale)


def _overlay(rows):
    """{"5": "---m-----"} -> [(5, 3, "m")]: the pixels a pose or stage paints ('-' keeps the pixel)."""
    return [(int(r), c, k) for r, row in rows.items() for c, k in enumerate(row) if k != "-"]


def load(path):
    d = json.loads(path.read_text())
    return Pet(id=path.stem, name=d["name"], base=d["base"],
               palette={k: tuple(int(v[i:i + 2], 16) for i in (1, 3, 5)) for k, v in d["palette"].items()},
               poses={name: _overlay(rows) for name, rows in d.get("poses", {}).items()},
               stages={int(n): _overlay(rows) for n, rows in d.get("stages", {}).items()},
               z_at=tuple(d.get("particles", (0, 13))), idle=d.get("idle", "breathe"))


def problems(path):
    """What's wrong in a pet file, in words a contributor can act on."""
    try:
        d = json.loads(path.read_text())
    except json.JSONDecodeError as e:
        return [f"{path.name}: not valid JSON ({e})"]
    found = []
    base, palette = d.get("base") or [], d.get("palette") or {}
    if not base or len({len(r) for r in base}) != 1:
        return found + [f"{path.name}: base must be rows of the same length"]
    if len(base) % 2:
        found.append(f"{path.name}: base needs an even number of rows (2 pixel rows = 1 terminal line)")
    for k, v in palette.items():
        if len(k) != 1 or k in ".-" or not (isinstance(v, str) and len(v) == 7 and v[0] == "#"):
            found.append(f"{path.name}: palette entry {k!r}: one letter -> \"#rrggbb\"")
    used = {k for r in base for k in r} - {"."}
    for part in ("poses", "stages"):
        for name, rows in d.get(part, {}).items():
            for r, row in rows.items():
                if not r.isdigit() or int(r) >= len(base) or len(row) != len(base[0]):
                    found.append(f"{path.name}: {part} {name} row {r}: a row number of base, as wide as base")
                used |= set(row) - {".", "-"}
    for k in sorted(used - set(palette)):
        found.append(f"{path.name}: color {k!r} is used but not in the palette")
    idle = d.get("idle", "breathe")
    for pose in POSES if idle == "breathe" else ("swim_up", "swim_down") + POSES[1:]:
        if pose not in d.get("poses", {}):
            found.append(f"{path.name}: missing pose {pose}")
    zr, zc = d.get("particles", (0, 13))
    if zc + 3 > len(base[0]) or any(base[2 * zr + i][zc + j] != "." for i in (0, 1) for j in range(3)):
        found.append(f"{path.name}: particles spot (row {zr}, column {zc}) must be 3 empty cells")
    return found


# Every pet in board order.
ROSTER = [
    ("bat", "Bat"), ("frog", "Frog"), ("turtle", "Turtle"), ("mushroom", "Mushroom"),
    ("slime", "Slime"), ("sofa", "Living sofa"), ("octopus", "Octopus"), ("dragon", "Dragon"),
    ("fox", "Fox"), ("owl", "Owl"), ("mole", "Mole"), ("snake", "Snake"),
    ("ghost", "Ghost"), ("spider", "Spider"), ("ant", "Ant"), ("axolotl", "Axolotl"),
    ("gremlin", "Gremlin"), ("snail", "Snail"),
    ("beaver", "Beaver"), ("squirrel", "Squirrel"), ("pigeon", "Pigeon"), ("hedgehog", "Hedgehog"),
    ("bee", "Bee"), ("whale", "Whale"), ("meerkat", "Meerkat"),
]
NAMES = dict(ROSTER)
NEEDS = {"whale": "kubectl", "bee": "systemctl"}                   # pet -> the command it's about; hidden when it isn't installed


def roster():
    """The pets of this system, in board order."""
    from .which import installed
    return [(pet, name) for pet, name in ROSTER if pet not in NEEDS or installed(NEEDS[pet])]


def owned(state):
    """Unlocked pets of this system (a Whale unlocked before kubectl was removed stays saved, not counted)."""
    shown = dict(roster())
    return [pet for pet in state["pets"] if pet in shown]

# Names of the three stages: unlocked, evolved (2 achievements), legendary (whole family).
STAGES = {
    "bat": ("Mouseling", "Bat", "Vampire"),
    "gremlin": ("Gremlin", "Goblin", "Orc"),
    "snail": ("Slug", "Snail", "Gary"),
    "frog": ("Tadpole", "Tree frog", "Toad"),
    "turtle": ("Hatchling", "Turtle", "Sea turtle"),
    "mushroom": ("Spore", "Mushroom", "Blob"),
    "slime": ("Droplet", "Slime", "King slime"),
    "sofa": ("Beanbag", "Armchair", "Throne"),
    "octopus": ("Octopito", "Octopus", "Kraken"),
    "dragon": ("Dragon egg", "Dragonet", "Dragon"),
    "fox": ("Fennec", "Fox", "Kitsune"),
    "owl": ("Pygmy owl", "Barn owl", "Horned owl"),
    "mole": ("Molekin", "Mole", "Mole king"),
    "snake": ("Snakelet", "Snake", "Basilisk"),
    "ghost": ("Spirit", "Wisp", "Ghost"),
    "spider": ("Spiderling", "Spider", "Tarantula"),
    "ant": ("Worker ant", "Soldier ant", "Queen ant"),
    "axolotl": ("Larva", "Axolotl", "Xolotl"),
    "beaver": ("Kit", "Beaver", "Platypus"),
    "squirrel": ("Red squirrel", "Chipmunk", "Flying squirrel"),
    "pigeon": ("Squab", "Pigeon", "Messenger"),
    "hedgehog": ("Hoglet", "Hedgehog", "Porcupine"),
    "bee": ("Brood", "Bee", "Queen bee"),
    "whale": ("Calf", "Whale", "Leviathan"),
    "meerkat": ("Pup", "Meerkat", "Sentinel"),
}



# Pets whose first stage is another animal: the sprite of each stage.
FORMS = {
    "bat": ("mouseling", "bat", "vampire"),
    "frog": ("tadpole", "frog", "toad"),
    "fox": ("fennec", "fox", "kitsune"),
    "owl": ("pygmy_owl", "barn_owl", "owl"),
    "turtle": ("hatchling", "turtle", "sea_turtle"),
    "mushroom": ("spore", "mushroom", "blob"),
    "octopus": ("octopito", "octopus", "kraken"),
    "sofa": ("beanbag", "sofa", "throne"),
    "dragon": ("dragon_egg", "dragon", "great_dragon"),
    "snake": ("snakelet", "snake", "basilisk"),
    "ghost": ("spirit", "wisp", "ghost"),
    "spider": ("spiderling", "spider", "tarantula"),
    "ant": ("ant", "soldier_ant", "queen_ant"),
    "axolotl": ("larva", "axolotl", "xolotl"),
    "gremlin": ("gremlin", "goblin", "orc"),
    "snail": ("slug", "snail", "gary"),
}


def form(pet_id, stage):
    """The sprite id of a pet at a stage."""
    return FORMS.get(pet_id, (pet_id,) * 3)[stage - 1]


# Starters: chosen once, they level up with every 5 achievements and change shape at levels 4 and 7.
STARTERS = {
    "star": ("stardust", "planet", "star"),
    "sprout": ("seedling", "sprout", "tree"),
    "pebble": ("pebble", "golem", "crystal"),
}
FORM_NAMES = {"stardust": "Stardust", "planet": "Planet", "star": "Star", "seedling": "Seedling", "sprout": "Sprout",
              "tree": "Tree spirit", "pebble": "Pebble", "golem": "Rock golem", "crystal": "Crystal golem"}
STARTER_BLURBS = {
    "star": "Bright and curious. Grows from a speck of dust into a star.",
    "sprout": "Calm and patient. Grows scripts from tiny seeds.",
    "pebble": "Solid and loyal. Knows the filesystem rock by rock.",
}

PETS = {path.stem: load(path) for path in sorted(ART.glob("*.json"))}
LARGE = {path.stem: load(path) for path in sorted((ART / "large").glob("*.json"))}   # `bashou config size large`


def get(pet_id, size="small"):
    """A pet's sprite; with size "large", its big pixel art when it has one."""
    if size == "large" and pet_id in LARGE:
        return LARGE[pet_id]
    return PETS.get(pet_id, PETS["stardust"])


def main():
    """python3 -m bashou.creatures check | show <pet>"""
    from . import render
    args = sys.argv[1:]
    if args[:1] == ["show"] and len(args) == 2:
        pet = load(ART / f"{args[1]}.json")
        cells = [[True] * pet.width for _ in range(len(pet.base) // 2)]
        frames = [("base", [], 1)] + [(p, [p], 1) for p in pet.poses] + [(f"stage {n}", [], n) for n in pet.stages]
        for name, poses, stage in frames:
            print(name)
            print("\n".join(render.lines(pet, poses, cells, stage)).replace(render.SKIP, " ") + "\n")
        return 0
    if args == ["check"]:
        found = [p for path in sorted(ART.glob("*.json")) + sorted((ART / "large").glob("*.json"))
                 for p in problems(path)]
        print("\n".join(found) or f"{len(PETS)} pets OK, {len(LARGE)} large")
        return 1 if found else 0
    print(main.__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
