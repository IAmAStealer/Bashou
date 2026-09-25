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
    "squirrel": ("squirrel", "chipmunk", "flying_squirrel"),
    "beaver": ("kit", "beaver", "platypus"),
    "pigeon": ("squab", "pigeon", "messenger"),
    "hedgehog": ("hoglet", "hedgehog", "porcupine"),
    "bee": ("brood", "bee", "queen_bee"),
    "cat": ("hacker_cat",),
    "slime": ("droplet", "slime", "leaf_slime", "fire_slime", "rock_slime", "ice_slime", "cat_slime", "thunder_slime", "king_slime"),
    "mole": ("molekin", "mole", "mole_king"),
    "whale": ("calf", "whale", "leviathan"),
    "meerkat": ("pup", "meerkat", "sentinel"),
    "leopard": ("snow_cub", "snow_leopard", "mountain_ghost"),
    "duck": ("duckling", "duck", "white_duck", "mandarin_duck"),
    "spark": ("sparklings", "spark", "ember", "candle", "lantern", "torch", "campfire", "beacon", "blaze", "phoenix"),
    "packet": ("bit", "byte", "packet", "datagram", "socket", "relay", "router", "uplink", "satellite", "constellation"),
}


def form(pet_id, stage):
    """The sprite id of a pet at a stage."""
    return FORMS.get(pet_id, (pet_id,) * 3)[stage - 1]


# Starters: chosen once, they level up with every 5 achievements and take a new shape at the levels
# of STARTER_LEVELS (one per form). Forms are added as their art is drawn (see doc/PLAN.md).
STARTERS = {
    "star": ("stardust", "meteor", "comet", "moon", "planet", "star", "red_giant"),
    "sprout": ("seedling", "sprout", "grass", "flower", "fern", "bush", "tree"),
    "pebble": ("sand_grain", "gravel", "pebble", "stone", "golem", "crystal", "jade_golem"),
}
STARTER_LEVELS = {line: (1, 3, 5, 8, 11, 15, 20) for line in STARTERS}
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
