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
    symmetric: bool = False     # its outline is a mirror image, and must stay one (`check`)
    lone_pixels: bool = False   # pixels touching no other are on purpose: sparkles, spores, bubbles
    next: str = ""              # the sprite of the form it evolves into; none for a last form

    @property
    def can_evolve(self):
        return bool(self.next)

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
               z_at=tuple(d.get("particles", (0, 13))), idle=d.get("idle", "breathe"),
               symmetric=d.get("symmetric", False), lone_pixels=d.get("lone_pixels", False), next=d.get("next", ""))


def mirror_breaks(base):
    """Rows whose outline isn't a mirror image (colors aside: highlights may sit on one side)."""
    shapes = ["".join("." if k == "." else "x" for k in row) for row in base]
    return [i for i, shape in enumerate(shapes) if shape != shape[::-1]]


def lone(base):
    """(row, column) of each pixel touching no other: a stray one, unless the sprite says it's on purpose."""
    h, w = len(base), len(base[0])
    return [(r, c) for r in range(h) for c in range(w)
            if base[r][c] != "." and all(base[r + dr][c + dc] == "." for dr in (-1, 0, 1) for dc in (-1, 0, 1)
                                         if (dr or dc) and 0 <= r + dr < h and 0 <= c + dc < w)]


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
    if d.get("next") and not (path.parent / f"{d['next']}.json").exists():
        found.append(f"{path.name}: \"next\" is {d['next']!r}, and there's no {d['next']}.json to evolve into")
    if d.get("symmetric"):
        for i in mirror_breaks(base):
            found.append(f"{path.name}: row {i} is no longer a mirror image (\"symmetric\": true)")
    if not d.get("lone_pixels"):
        for r, c in lone(base):
            found.append(f"{path.name}: lone pixel at row {r}, column {c} (on purpose? add \"lone_pixels\": true)")
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
    ("bee", "Bee"), ("whale", "Whale"), ("meerkat", "Meerkat"), ("leopard", "Snow leopard"), ("duck", "Duck"),
    ("spark", "Spark"), ("packet", "Packet"),
    ("cat", "Hacker cat"),
]
NAMES = dict(ROSTER)
NEEDS = {"whale": "kubectl", "bee": "systemctl"}                   # pet -> the command it's about; hidden when it isn't installed


SECRET = {"cat"}            # not on the board until you find it (secret achievements bring it)


def roster(state=None):
    """The pets of this system, in board order; a secret pet only once you have it."""
    from .which import installed
    owned_pets = (state or {}).get("pets", ())
    return [(pet, name) for pet, name in ROSTER
            if (pet not in NEEDS or installed(NEEDS[pet])) and (pet not in SECRET or pet in owned_pets)]


def owned(state):
    """Unlocked pets of this system (a Whale unlocked before kubectl was removed stays saved, not counted)."""
    shown = dict(roster(state))
    return [pet for pet in state["pets"] if pet in shown]

# Names of the three stages: unlocked, evolved (2 achievements), legendary (whole family).
STAGES = {
    "bat": ("Mouseling", "Bat", "Vampire"),
    "gremlin": ("Gremlin", "Goblin", "Orc"),
    "snail": ("Slug", "Snail", "Gary"),
    "frog": ("Tadpole", "Tree frog", "Toad"),
    "turtle": ("Hatchling", "Turtle", "Sea turtle"),
    "mushroom": ("Spore", "Mushroom", "Blob"),
    "slime": ("Droplet", "Slime", "Leaf slime", "Fire slime", "Rock slime", "Ice slime", "Cat slime", "Thunder slime", "King slime"),
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
    "cat": ("Hacker cat",),                      # secret, one form only
    "whale": ("Calf", "Whale", "Leviathan"),
    "meerkat": ("Pup", "Meerkat", "Sentinel"),
    "leopard": ("Snow cub", "Snow leopard", "Mountain ghost"),
    "duck": ("Duckling", "Duck", "White duck", "Mandarin duck"),
    "spark": ("Sparklings", "Spark", "Ember", "Candle", "Lantern", "Torch", "Campfire", "Beacon", "Blaze", "Phoenix"),
    "packet": ("Bit", "Byte", "Packet", "Datagram", "Socket", "Relay", "Router", "Uplink", "Satellite", "Constellation"),
}



# Each pet's first form. The sprite files link each form to the next (`"next"`): the last form has none.
FIRST_FORM = {
    "bat": "mouseling", "frog": "tadpole", "fox": "fennec", "owl": "pygmy_owl", "turtle": "hatchling",
    "mushroom": "spore", "octopus": "octopito", "sofa": "beanbag", "dragon": "dragon_egg", "snake": "snakelet",
    "ghost": "spirit", "spider": "spiderling", "ant": "ant", "axolotl": "larva", "gremlin": "gremlin",
    "snail": "slug", "squirrel": "squirrel", "beaver": "kit", "pigeon": "squab", "hedgehog": "hoglet",
    "bee": "brood", "cat": "hacker_cat", "slime": "droplet", "mole": "molekin", "whale": "calf",
    "meerkat": "pup", "leopard": "snow_cub", "duck": "duckling", "spark": "sparklings", "packet": "bit"
}


def forms(pet_id):
    """The sprite ids of a pet's forms, in order (one for a pet that never evolves)."""
    return FORMS.get(pet_id, (pet_id,))


def can_evolve(pet_id):
    """A pet (by its id) that has more than one form."""
    return PETS[forms(pet_id)[0]].can_evolve


def form(pet_id, stage):
    """The sprite id of a pet at a stage."""
    return FORMS.get(pet_id, (pet_id,) * 3)[stage - 1]


# Starters: chosen once, they level up with every 5 achievements and take a new shape at the levels
# of STARTER_LEVELS (one per form). Forms are added as their art is drawn (see doc/PLAN.md).
STARTER_FIRST = {"star": "stardust", "sprout": "seedling", "pebble": "sand_grain"}     # then the "next" links
STARTER_LEVELS = {line: (1, 3, 5, 8, 11, 15, 20) for line in STARTER_FIRST}
FORM_NAMES = {"stardust": "Stardust", "meteor": "Meteor", "comet": "Comet", "moon": "Moon", "planet": "Planet",
              "star": "Star", "red_giant": "Red giant",
              "seedling": "Seedling", "sprout": "Sprout", "grass": "Grass", "flower": "Flower", "fern": "Fern",
              "bush": "Bush", "tree": "Tree spirit",
              "sand_grain": "Sand grain", "gravel": "Gravel", "pebble": "Pebble", "stone": "Stone",
              "golem": "Rock golem", "crystal": "Crystal golem", "jade_golem": "Jade golem"}
STARTER_BLURBS = {
    "star": "Bright and curious. A speck of dust with big dreams.",
    "sprout": "Calm and patient. Grows scripts from tiny seeds.",
    "pebble": "Solid and loyal. Knows the filesystem rock by rock.",
}

PETS = {path.stem: load(path) for path in sorted(ART.glob("*.json"))}
LARGE = {path.stem: load(path) for path in sorted((ART / "large").glob("*.json"))}   # `bashou config size large`


def chain(first):
    """The forms from `first`, following each sprite's "next" link to the last form."""
    out = [first]
    while PETS[out[-1]].next:
        if PETS[out[-1]].next in out:
            raise ValueError(f"{out[-1]}.json: \"next\" loops back to {PETS[out[-1]].next}")
        out.append(PETS[out[-1]].next)
    return tuple(out)


FORMS = {pet: chain(first) for pet, first in FIRST_FORM.items()}          # pet -> the sprite of each stage
STARTERS = {line: chain(first) for line, first in STARTER_FIRST.items()}


def get(pet_id, size="small"):
    """A pet's sprite; with size "large", its big pixel art when it has one."""
    if size == "large" and pet_id in LARGE:
        return LARGE[pet_id]
    return PETS.get(pet_id, PETS["stardust"])


def main():
    """python3 -m bashou.creatures check | show <pet or fight id> [...]"""
    from . import render
    args = sys.argv[1:]
    if args[:1] == ["show"] and len(args) > 1:
        for pet_id in args[1:]:
            path = ART / f"{pet_id}.json"
            pet = load(path if path.exists() else ART.parent / "enemies" / f"{pet_id}.json")
            cells = [[True] * pet.width for _ in range(len(pet.base) // 2)]
            frames = [("base", [], 1)] + [(p, [p], 1) for p in pet.poses] + [(f"stage {n}", [], n) for n in pet.stages]
            print(f"\033[1m{pet.name}\033[0m ({pet_id})")
            for name, poses, stage in frames:
                print(f"  \033[2m{name}\033[0m")
                print("\n".join(render.lines(pet, poses, cells, stage)).replace(render.SKIP, " ") + "\n")
        return 0
    if args == ["check"]:
        enemies = sorted((ART.parent / "enemies").glob("*.json"))
        found = [p for path in sorted(ART.glob("*.json")) + sorted((ART / "large").glob("*.json")) + enemies
                 for p in problems(path)]
        print("\n".join(found) or f"{len(PETS)} pets OK, {len(LARGE)} large")
        return 1 if found else 0
    print(main.__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
