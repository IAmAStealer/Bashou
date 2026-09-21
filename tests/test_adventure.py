import tempfile
import unittest
from pathlib import Path

from bashou import adventure, state
from bashou.adventure import canvas, scene, sprites


class CanvasTest(unittest.TestCase):
    def test_only_changes_are_redrawn(self):
        c = canvas.Canvas(10, 6)
        self.assertIn("▀", c.render().replace(" ", "▀"))
        self.assertEqual(c.render(), "")                 # nothing changed
        c.set(3, 1, (255, 0, 0))
        out = c.render()
        self.assertEqual(out.count("m▀"), 1)              # one cell
        self.assertIn("\x1b[1;4H", out)


class SceneTest(unittest.TestCase):
    def test_same_place_same_picture(self):
        for biome in scene.BIOMES:
            a, b = canvas.Canvas(60, 30), canvas.Canvas(60, 30)
            scene.draw(a, biome, 42.0, 1.0)
            scene.draw(b, biome, 42.0, 1.0)
            self.assertEqual(a.px, b.px)

    def test_walking_moves_the_ground(self):
        a, b = canvas.Canvas(60, 30), canvas.Canvas(60, 30)
        scene.draw(a, "meadow", 10.0)
        scene.draw(b, "meadow", 10.6)
        self.assertNotEqual(a.px[25], b.px[25])

    def test_every_hero_has_a_back_view(self):
        for form in ["kitten", "cat", "lion", "seedling", "sprout", "tree", "pebble", "golem", "crystal"]:
            frames, palette = sprites.hero(form)
            for frame in frames:
                self.assertEqual(len(frame), 12, form)
                self.assertTrue(all(len(r) == 17 for r in frame), form)
                self.assertTrue(set("".join(frame)) - {"."} <= set(palette), form)


class GameTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = state.DATA, state.STATE
        state.DATA = Path(self.tmp.name)
        state.STATE = state.DATA / "state.json"
        with state.locked() as s:
            s["starter"] = "pebble"

    def tearDown(self):
        state.DATA, state.STATE = self.saved
        self.tmp.cleanup()

    def test_walk_and_save(self):
        game = adventure.Game(80, 24)
        game.key("\x1b[A", 100.0)
        game.update(0.2, 100.1)
        self.assertAlmostEqual(game.adv["distance"], 1.0)
        game.update(1.0, 101.0)                           # key released: stops
        self.assertAlmostEqual(game.adv["distance"], 1.0)
        game.key(" ", 101.0)                              # auto-walk
        game.update(1.0, 102.0)
        self.assertAlmostEqual(game.adv["distance"], 6.0)
        self.assertTrue(game.draw(1.0))
        adventure.save(game.adv)
        self.assertAlmostEqual(adventure.Game(80, 24).adv["distance"], 6.0)

    def test_keys(self):
        self.assertEqual(adventure.split_keys("\x1b[Aw \x1b[B"), ["\x1b[A", "w", " ", "\x1b[B"])
        for k in ("s", "q", "\x1b", "\x03", "\x04"):
            game = adventure.Game(80, 24)
            game.key(k, 0)
            self.assertTrue(game.quit, repr(k))


if __name__ == "__main__":
    unittest.main()
