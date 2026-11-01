"""Owner, 2026-11-01: redrawn sprites keep their old look, and a key switches between old and new style."""
import inspect
import unittest
from unittest import mock

from bashou import creatures, state
from tests.test_regressions import TempState


def fake_classic(pet_id):
    """A copy of a pet's sprite with another name: tells the old look from the new one in tests."""
    pet = creatures.PETS[pet_id]
    return creatures.Pet(pet.id, "Old " + pet.name, pet.base, {k: (200, 0, 0) for k in pet.palette},
                         poses=pet.poses, stages=pet.stages)


class ClassicFilesTest(unittest.TestCase):
    def test_every_classic_sprite_is_an_old_look_of_a_pet(self):
        for pet_id, old in creatures.CLASSIC.items():
            new = creatures.PETS.get(pet_id)
            self.assertIsNotNone(new, f"classic/{pet_id}.json: no pet {pet_id}")
            self.assertEqual((len(old.base), old.width), (len(new.base), new.width), pet_id)
            self.assertEqual(set(old.poses), set(new.poses), pet_id)
            self.assertEqual(set(old.stages), set(new.stages), pet_id)

    def test_check_looks_at_the_classic_sprites(self):
        self.assertIn('"classic"', inspect.getsource(creatures.main))


class GetTest(unittest.TestCase):
    def test_style_picks_the_old_look_only_when_there_is_one(self):
        old = fake_classic("bat")
        with mock.patch.dict(creatures.CLASSIC, {"bat": old}, clear=True):
            self.assertIs(creatures.get("bat", style="classic"), old)
            self.assertIs(creatures.get("bat"), creatures.PETS["bat"])                  # new is the default
            self.assertIs(creatures.get("frog", style="classic"), creatures.PETS["frog"])  # never redrawn


class SettingTest(TempState):
    def test_style_is_a_setting_new_by_default(self):
        self.assertEqual(state.SETTINGS["style"].choices, ("new", "classic"))
        self.assertEqual(state.setting(state.load(), "style"), "new")


class BoardStyleTest(TempState):
    @mock.patch("bashou.which.installed", return_value=True)
    def test_s_switches_the_style_and_the_board_draws_it(self, _):
        from bashou import board as board_mod
        self.assertEqual(board_mod.KEYS.get("s"), "style")
        with state.locked() as s:
            s["pets"] += ["bat"]
        with mock.patch.dict(creatures.CLASSIC, {"mouseling": fake_classic("mouseling")}, clear=True):
            board = board_mod.Board()
            board.pos = board.ids.index("bat")
            new = board.preview()
            self.assertTrue(board.key("style"))                                       # board stays open
            self.assertEqual(state.setting(state.load(), "style"), "classic")
            self.assertIn("old", board.message.lower())
            self.assertNotEqual(board.preview(), new)
            board.key("style")
            self.assertEqual(state.setting(state.load(), "style"), "new")
            self.assertEqual(board.preview(), new)

    def test_every_sprite_lookup_passes_the_style(self):
        """A screen that calls creatures.get without the style would show the new look to an old-style player."""
        from bashou import board, companion, duel, evolve, pony, starter
        for mod in (board, companion, duel, evolve, pony, starter):
            for line in inspect.getsource(mod).splitlines():
                if "creatures.get(" in line:
                    self.assertIn("style", line, f"{mod.__name__}: {line.strip()}")
