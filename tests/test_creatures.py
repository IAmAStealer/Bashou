import unittest

from bashou import creatures, duel, render


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
        self.assertEqual(set(creatures.NAMES), set(creatures.FORMS))

    def test_family_files_are_valid(self):
        for path in sorted(creatures.FAMILY_DIR.glob("*.json")):
            self.assertEqual(creatures.family_problems(path), [], path.name)
        pets = [f for f in creatures.FAMILIES.values() if not f.starter]
        starters = [f for f in creatures.FAMILIES.values() if f.starter]
        for group in (pets, starters):                                   # one place each on the board
            self.assertEqual(sorted(f.order for f in group), list(range(1, len(group) + 1)))

    def test_every_sprite_is_a_form_of_one_pet(self):
        """Each sprite links to the form it evolves into ("next"): following the links from each first form
        reaches every sprite exactly once, and a last form has no link."""
        chains = list(creatures.FORMS.values()) + list(creatures.STARTERS.values())
        sprites = [s for chain in chains for s in chain]
        self.assertEqual(sorted(sprites), sorted(creatures.PETS))
        for chain in chains:
            self.assertFalse(creatures.PETS[chain[-1]].can_evolve, chain)
            self.assertTrue(all(creatures.PETS[s].can_evolve for s in chain[:-1]), chain)
        for pet, forms in creatures.FORMS.items():
            self.assertEqual(creatures.can_evolve(pet), len(forms) > 1, pet)


class SymmetryTest(unittest.TestCase):
    def test_symmetric_sprites_stay_symmetric(self):
        """A one-pixel slip broke the Droplet, the Orc's tusk and the Snakelet (owner's bug report): a sprite
        whose file says "symmetric" must stay a mirror image."""
        for pet in [*creatures.PETS.values(), *creatures.LARGE.values()]:
            if pet.symmetric:
                self.assertEqual(creatures.mirror_breaks(pet.base), [], pet.id)


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


class LonePixelTest(unittest.TestCase):
    def test_no_stray_pixel(self):
        """The Ember had a lost pixel at its top right (owner's report, 0.6.0): a pixel touching no other,
        unless the sprite's file says its lone pixels are on purpose (sparkles, spores, bubbles)."""
        for pet in [*creatures.PETS.values(), *creatures.LARGE.values(), *map(creatures.load, sorted(duel.ENEMIES.glob("*.json")))]:
            if not pet.lone_pixels:
                self.assertEqual(creatures.lone(pet.base), [], pet.id)


if __name__ == "__main__":
    unittest.main()
