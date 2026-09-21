import random
import tempfile
import unittest
from pathlib import Path

from bashou import adventure, state
from bashou.adventure import canvas, quiz, scene, sprites, world


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
        self.game = adventure.Game(80, 24, rng=random.Random(0))

    def tearDown(self):
        state.DATA, state.STATE = self.saved
        self.tmp.cleanup()

    def go(self, *keys, now=100.0):
        for k in keys:
            self.game.key(k, now)

    def walk_to_event(self):
        g = self.game
        g.key(" ", 0)                                     # auto-walk
        for _ in range(200):
            g.update(0.5, 0)
            if g.adv["phase"] != "walk":
                return g.adv["phase"]
        self.fail("no event")

    def test_intro_fork_walk(self):
        g = self.game
        self.assertEqual(g.adv["phase"], "intro")
        self.go("\r")
        self.assertEqual(g.adv["phase"], "fork")
        self.go("\x1b[C", "\r")                          # second path
        self.assertEqual(g.adv["topic"], world.fork_options(g.adv | {"leg": 0})[1])
        self.assertEqual(self.walk_to_event(), "monster")  # every path starts with a monster
        self.assertTrue(g.draw(1.0, 0))

    def test_monster_right_and_wrong(self):
        g = self.game
        self.go("\r", "\r")
        self.walk_to_event()
        g.answer(g.question["answer"], 0)
        self.assertTrue(g.result[0])
        self.assertEqual(g.adv["hearts"], 3)
        g.close_result(0)
        self.assertEqual((g.adv["phase"], g.adv["segment"]), ("walk", 1))

    def test_last_heart_goes_back_to_the_checkpoint(self):
        g = self.game
        self.go("\r", "\r")
        g.adv["hearts"] = 1
        self.walk_to_event()
        g.answer((g.question["answer"] + 1) % 4, 0)
        self.assertFalse(g.result[0])
        self.assertEqual((g.adv["phase"], g.adv["hearts"], g.adv["distance"]), ("fork", 3, 0.0))

    def test_boss_is_a_checkpoint(self):
        g = self.game
        self.go("\r", "\r")
        topic = g.adv["topic"]
        g.adv["segment"] = len(world.events(g.adv)) - 1    # skip to the boss
        self.assertEqual(self.walk_to_event(), "boss")
        for _ in range(world.boss_questions(g.adv)):
            g.answer(g.question["answer"], 0)
            g.close_result(0)
        self.assertEqual(g.adv["phase"], "fork")
        self.assertEqual(g.adv["leg"], 1)
        self.assertEqual(world.level(g.adv, topic), 2)
        self.assertEqual(g.adv["leg_start"], g.adv["distance"])     # the new checkpoint
        self.assertEqual(adventure.load()["leg"], 1)                  # saved right away

    def test_boss_timeout_is_a_defeat(self):
        g = self.game
        self.go("\r", "\r")
        g.adv["segment"] = len(world.events(g.adv)) - 1
        self.walk_to_event()
        g.update(0, 0 + adventure.BOSS_SECONDS + 1)
        self.assertFalse(g.result[0])
        self.assertIn("Too slow", " ".join(g.result[1]))
        self.assertEqual((g.adv["phase"], g.adv["distance"]), ("fork", 0.0))

    def test_chapter_end_and_new_quest(self):
        adv = world.new()
        adv["phase"] = "fork"
        for _ in range(world.chapter(1)["legs"]):
            world.choose(adv, world.fork_options(adv)[0])
            world.boss_won(adv)
        self.assertEqual(adv["phase"], "chapter_end")
        world.next_chapter(adv)
        self.assertEqual((adv["chapter"], adv["leg"], adv["phase"]), (2, 0, "intro"))
        self.assertEqual(len(world.fork_options(adv)), 3)

    def test_old_save_keeps_its_meters(self):
        with state.locked() as s:
            s["adventure"] = {"distance": 42.0}
        self.assertEqual(adventure.load()["walked"], 42.0)
        self.assertEqual(adventure.load()["chapter"], 1)

    def test_keys(self):
        self.assertEqual(adventure.split_keys("\x1b[Aw \x1b[B"), ["\x1b[A", "w", " ", "\x1b[B"])
        for k in ("s", "q", "\x1b", "\x03", "\x04"):
            game = adventure.Game(80, 24)
            game.key(k, 0)
            self.assertTrue(game.quit, repr(k))


class QuizTest(unittest.TestCase):
    def test_banks_are_valid(self):
        for topic in world.TOPICS:
            items = quiz.bank(topic, "en")
            self.assertEqual(quiz.problems(items), [], topic)
            self.assertEqual({q["level"] for q in items} >= {1, 2}, True, topic)

    def test_no_repeats_until_all_seen(self):
        rng = random.Random(1)
        pool = [q["id"] for q in quiz.bank("bash", "en") if q["level"] == 1]
        seen = []
        for _ in pool:
            seen.append(quiz.pick("bash", 1, seen, rng)["id"])
        self.assertEqual(sorted(seen), sorted(pool))

    def test_choices_are_shuffled_and_answer_follows(self):
        for seed in range(20):
            q = quiz.pick("linux", 1, [], random.Random(seed))
            original = next(o for o in quiz.bank("linux", "en") if o["id"] == q["id"])
            self.assertEqual(q["choices"][q["answer"]], original["choices"][original["answer"]])

    def test_level_above_the_bank_uses_the_highest(self):
        self.assertEqual(quiz.pick("rust", 9, [], random.Random(0))["level"], quiz.max_level("rust"))


if __name__ == "__main__":
    unittest.main()
