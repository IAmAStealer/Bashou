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

    def test_roster_has_stage_names(self):
        self.assertEqual(len(ROSTER), 16)
        self.assertEqual({p for p, _ in ROSTER}, set(STAGES))


if __name__ == "__main__":
    unittest.main()
