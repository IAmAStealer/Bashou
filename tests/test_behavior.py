import random
import unittest

from bashou import creatures, render
from bashou.behavior import Behavior


def moods_seen(stage, seconds=20000):
    b = Behavior(random.Random(1))
    b.stage = stage
    seen = set()
    for ms in range(0, seconds * 1000, 250):
        b.frame(ms, creatures.CAT)
        seen.add(b.mood)
    return seen


class BehaviorTest(unittest.TestCase):
    def test_stages_unlock_actions(self):
        self.assertEqual(moods_seen(1), {"awake", "look"})
        self.assertEqual(moods_seen(2), {"awake", "look", "wash", "hum"})
        self.assertEqual(moods_seen(3), {"awake", "look", "wash", "hum", "dance", "sparkle"})

    def test_sleeps_only_when_idle(self):
        b = Behavior(random.Random(3))
        for ms in range(0, 4 * 60_000, 250):            # active: never asleep
            b.frame(ms, creatures.CAT, idle=1000)
            self.assertNotEqual(b.mood, "sleep")
        b.frame(300_000, creatures.CAT, idle=b.sleep_after)
        self.assertEqual(b.mood, "sleep")
        poses, text = b.frame(302_500, creatures.CAT, idle=b.sleep_after + 2500)
        self.assertIn("closed", poses)
        b.frame(303_000, creatures.CAT, idle=0)           # a key wakes it up
        self.assertEqual(b.mood, "awake")
        self.assertGreaterEqual(b.sleep_after, 5 * 60_000)
        self.assertLessEqual(b.sleep_after, 15 * 60_000)

    def test_tadpole_tail_keeps_moving(self):
        b = Behavior(random.Random(4))
        swims = {"swim" in b.frame(ms, creatures.TADPOLE)[0] for ms in range(0, 3000, 250)}
        self.assertEqual(swims, {True, False})

    def test_every_pet_can_do_everything(self):
        for pet in creatures.PETS.values():
            b = Behavior(random.Random(2))
            b.stage = 3
            cells = render.mask(pet)
            for ms in range(0, 3000 * 1000, 250):
                poses, text = b.frame(ms, pet, threat=ms > 2_000_000, idle=ms % 1_200_000)
                self.assertLessEqual(render.width(text), 3)
                if ms % 5000 == 0:
                    render.lines(pet, poses, cells, 3)

    def test_particle_spot_is_empty(self):
        for pet in creatures.PETS.values():
            zr, zc = pet.z_at
            for c in range(zc, zc + 3):
                self.assertLess(c, pet.width, pet.id)
                self.assertEqual(pet.base[2 * zr][c] + pet.base[2 * zr + 1][c], "..", pet.id)


if __name__ == "__main__":
    unittest.main()
