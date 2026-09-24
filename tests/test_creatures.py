import unittest

from bashou import creatures, render
from bashou.creatures import ROSTER, STAGES


class CreaturesTest(unittest.TestCase):
    def test_sprites_render_in_every_pose_and_stage(self):
        for pet in creatures.PETS.values():
            self.assertEqual(len(pet.base), 12, pet.id)
            self.assertTrue(all(len(r) == pet.width for r in pet.base), pet.id)
            cells = render.mask(pet)
            for pose in list(pet.poses) + [None]:
                for stage in (1, 2, 3):
                    lines = render.lines(pet, [pose] if pose else [], cells, stage)
                    self.assertEqual(len(lines), 6)

    def test_palettes_cover_sprites(self):
        for pet in creatures.PETS.values():
            keys = {k for row in pet.base for k in row} - {"."}
            keys |= {k for px in [*pet.poses.values(), *pet.stages.values()] for _, _, k in px} - {"."}
            self.assertLessEqual(keys, set(pet.palette), pet.id)

    def test_every_pet_blinks_looks_and_fidgets(self):
        for pet in creatures.PETS.values():
            idle = ("inhale",) if pet.idle == "breathe" else ("swim_up", "swim_down")
            for pose in (*idle, "closed", "left", "right", "fidget"):
                self.assertIn(pose, pet.poses, f"{pet.id} has no {pose}")

    def test_pet_files_are_valid(self):
        for path in sorted(creatures.ART.glob("*.json")):
            self.assertEqual(creatures.problems(path), [], path.name)

    def test_check_explains_mistakes(self):
        import json, tempfile
        from pathlib import Path
        d = json.loads((creatures.ART / "fox.json").read_text())
        d["base"][5] = d["base"][5][:-1] + "Z"                           # a color missing from the palette
        del d["poses"]["closed"]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fox.json"
            path.write_text(json.dumps(d))
            found = " ".join(creatures.problems(path))
        self.assertIn("'Z' is used but not in the palette", found)
        self.assertIn("missing pose closed", found)

    def test_large_sprites_are_valid_and_have_a_small_one(self):
        for path in sorted((creatures.ART / "large").glob("*.json")):
            self.assertEqual(creatures.problems(path), [], path.name)
            self.assertIn(path.stem, creatures.PETS)
            big = creatures.LARGE[path.stem]
            self.assertTrue(set(creatures.POSES) <= set(big.poses), path.name)
            self.assertEqual(len(render.lines(big, ["inhale"], render.mask(big))), len(big.base) // 2)

    def test_size_picks_the_large_sprite_when_there_is_one(self):
        self.assertIs(creatures.get("tarantula", "large"), creatures.LARGE["tarantula"])
        self.assertIs(creatures.get("tarantula"), creatures.PETS["tarantula"])
        self.assertIs(creatures.get("fox", "large"), creatures.PETS["fox"])

    def test_roster_has_stage_names(self):
        from bashou.creatures import SECRET
        self.assertEqual(len([p for p, _ in ROSTER if p not in SECRET]), 27)
        self.assertEqual({p for p, _ in ROSTER}, set(STAGES))


# Symmetric designs (their outline, not their highlights). A one-pixel slip broke the Droplet, the
# Orc's tusk and the Snakelet (owner's bug report): they must stay mirror images.
SYMMETRIC = ["barn_owl", "basilisk", "bat", "beanbag", "brood", "dragon_egg", "droplet", "goblin", "gremlin",
             "king_slime", "kitsune", "kraken", "molekin", "octopito", "orc", "planet", "porcupine", "pup",
             "snakelet", "spider", "spiderling", "spirit", "star", "throne", "vampire"]


class SymmetryTest(unittest.TestCase):
    def test_symmetric_sprites_stay_symmetric(self):
        for pet_id in SYMMETRIC:
            for i, row in enumerate(creatures.PETS[pet_id].base):
                shape = "".join("." if k == "." else "x" for k in row)
                self.assertEqual(shape, shape[::-1], f"{pet_id} row {i}: {row}")


class MovingPetTest(unittest.TestCase):
    def test_the_sand_grain_is_never_in_two_places(self):
        """The wind poses run on top of the breathing hop, which moved the grain too (owner's bug)."""
        from bashou import render
        pet = creatures.PETS["sand_grain"]
        for pose in ("left", "right", "fidget"):
            for poses in ([pose], ["inhale", pose]):
                grid = render.grid(pet, poses)
                grains = [(r, c) for r, row in enumerate(grid) for c, k in enumerate(row) if k == "l"]
                self.assertEqual(len(grains), 1, f"{poses}: {grains}")


if __name__ == "__main__":
    unittest.main()
