"""Every name Bashou points to must exist, and every screen must draw.

The adventure asked for `creatures.OWL` after the pets moved to JSON files, and crashed only when the
Sage Owl came (owner's bug report). These tests look for that kind of bug everywhere at once:
names in the code, ids in the tables, and a full playthrough that draws every frame.
"""

import ast
import importlib
import random
import unittest
from pathlib import Path

from bashou import achievements, challenges, creatures, dialogue, duel, progress, render, state
from bashou.adventure import lessons, quiz, scene, sprites, world
from tests.test_regressions import TempState

ROOT = Path(__file__).resolve().parent.parent / "bashou"


def sources():
    for path in sorted(ROOT.rglob("*.py")):
        yield path, ast.parse(path.read_text()), ".".join(("bashou",) + path.relative_to(ROOT).parent.parts)


def resolve(package, node):
    base = package.rsplit(".", node.level - 1)[0] if node.level > 1 else package
    return base + "." + node.module if node.module else base


class CodeNamesTest(unittest.TestCase):
    def test_every_module_attribute_exists(self):
        missing = []
        for path, tree, package in sources():
            modules = {}
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level:
                    for alias in node.names:
                        try:
                            modules[alias.asname or alias.name] = importlib.import_module(
                                f"{resolve(package, node)}.{alias.name}")
                        except ImportError:
                            pass                                    # a function or class, not a module
            for node in ast.walk(tree):
                if (isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name)
                        and node.value.id in modules and not hasattr(modules[node.value.id], node.attr)):
                    missing.append(f"{path.relative_to(ROOT)}:{node.lineno} {node.value.id}.{node.attr}")
        self.assertEqual(missing, [])

    def test_every_imported_name_exists(self):
        missing = []
        for path, tree, package in sources():
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level:
                    module = importlib.import_module(resolve(package, node))
                    for alias in node.names:
                        if not hasattr(module, alias.name):
                            try:
                                importlib.import_module(f"{module.__name__}.{alias.name}")
                            except ImportError:
                                missing.append(f"{path.relative_to(ROOT)}:{node.lineno} {alias.name}")
        self.assertEqual(missing, [])

    def test_every_global_name_exists(self):
        """A name a function uses without defining it must be in its module (or a builtin): no NameError
        waiting in a rarely run branch after a rename."""
        import builtins
        import symtable
        missing = []
        for path, _tree, package in sources():
            if path.name == "__main__.py":
                continue
            name = package if path.name == "__init__.py" else f"{package}.{path.stem}"
            module = importlib.import_module(name)

            def walk(table):
                for sym in table.get_symbols():
                    if (table.get_type() == "function" and sym.is_referenced() and sym.is_global()
                            and not hasattr(module, sym.get_name()) and not hasattr(builtins, sym.get_name())):
                        missing.append(f"{path.relative_to(ROOT)} {table.get_name()}(): {sym.get_name()}")
                for child in table.get_children():
                    walk(child)
            walk(symtable.symtable(path.read_text(), str(path), "exec"))
        self.assertEqual(missing, [])

    def test_sprite_ids_written_in_the_code_exist(self):
        """`creatures.get("x")`, `sprites.pet("x")`, `PETS["x"]`: x must be a pets/x.json file."""
        found = []
        for path, tree, _package in sources():
            for node in ast.walk(tree):
                arg = None
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.args:
                    if (getattr(node.func.value, "id", ""), node.func.attr) in (("creatures", "get"), ("sprites", "pet")):
                        arg = node.args[0]
                if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "pet" and node.args:
                    if path.name == "sprites.py":
                        arg = node.args[0]
                if isinstance(node, ast.Subscript) and getattr(node.value, "attr", getattr(node.value, "id", "")) == "PETS":
                    arg = node.slice
                if isinstance(arg, ast.Constant) and arg.value not in creatures.PETS:
                    found.append(f"{path.relative_to(ROOT)}:{node.lineno} {arg.value}")
        self.assertEqual(found, [])


class TablesTest(unittest.TestCase):
    """Ids written in one table must exist in the table they point to."""

    def assertIn_all(self, ids, known, what):
        self.assertEqual(sorted(set(ids) - set(known)), [], what)

    def test_pets(self):
        roster = set(creatures.NAMES)
        self.assertEqual(set(creatures.STAGES), roster)
        self.assertEqual(set(creatures.FORMS), roster)
        self.assertIn_all([s for forms in creatures.FORMS.values() for s in forms], creatures.PETS, "FORMS sprites")
        starter_forms = [s for forms in creatures.STARTERS.values() for s in forms]
        self.assertIn_all(starter_forms, creatures.PETS, "starter sprites")
        self.assertEqual(set(creatures.FORM_NAMES), set(starter_forms))
        self.assertEqual(set(creatures.STARTER_BLURBS), set(creatures.STARTERS))
        self.assertIn_all(creatures.LARGE, creatures.PETS, "large sprites without a small one")
        self.assertIn_all(creatures.NEEDS, roster, "NEEDS")
        self.assertIn_all(state.CHOICES, state.SETTINGS, "setting choices")

    def test_unlocks(self):
        roster = set(creatures.NAMES)
        for table in (progress.TOOL_PETS, progress.TOOL_LABELS, progress.CONSTRUCT_PETS, progress.STATE_PETS,
                      achievements.FAMILY_NEEDS):
            self.assertIn_all(table, roster, table)
        self.assertIn_all([c for c, _n in progress.CONSTRUCT_PETS.values()], progress.CONSTRUCT_NAMES, "constructs")
        for pet, names in progress.TOOL_LABELS.items():
            self.assertIn_all(names, progress.TOOL_PETS[pet][0], pet)
        self.assertIn_all([a.family for a in achievements.ALL if getattr(a, "family", None)],
                          roster | set(creatures.STARTERS), "achievement families")

    def test_pet_lines(self):
        voices = set(creatures.NAMES) | set(creatures.STARTERS)
        for table in (dialogue.VOICE, dialogue.TIPS, dialogue.PERSONAL, dialogue.TRAITS):
            self.assertIn_all(table, voices | set(achievements.BY_ID), sorted(table)[:3])
        self.assertIn_all(dialogue.INVITES, {"adventure", "security"}, "INVITES")    # modes
        self.assertIn_all(dialogue.EXAMPLES, achievements.BY_ID, "EXAMPLES")
        tools = {t for ch in challenges.ALL for t in ch.tools} | {"|"}
        self.assertIn_all(dialogue.DISCOVER, tools, "DISCOVER")

    def test_fights(self):
        every = challenges.ALL + challenges.SECURITY + challenges.TRIALS
        ids = {ch.id for ch in every}
        for ch in every:
            self.assertIn_all(ch.after, ids, ch.id)
            if ch.kind == "fight":
                self.assertIn(ch.pet, creatures.NAMES, ch.id)
        self.assertEqual(set(duel.TINTS), {ch.id for ch in challenges.ALL})
        self.assertIn_all([p.stem for p in duel.ENEMIES.glob("*.json")], challenges.BY_ID, "enemy sprites")
        for path in duel.ENEMIES.glob("*.json"):
            self.assertEqual(creatures.problems(path), [], path.name)

    def test_adventure(self):
        topics = set(world.TOPICS)
        self.assertEqual(set(sprites.TOPIC_COLORS), topics)
        self.assertEqual(set(sprites.BOSSES), topics)
        self.assertEqual(set(sprites.BACK), {s for forms in creatures.STARTERS.values() for s in forms})
        biomes = {home for _n, home, _b in world.TOPICS.values()} | {c["home"] for c in world.CHAPTERS}
        self.assertIn_all(biomes, scene.BIOMES, "biomes")
        for lesson in lessons.LESSONS:
            self.assertIn_all(lesson["topics"], topics, lesson["id"])
        for topic in topics:
            self.assertTrue(quiz.bank(topic), topic)


class DrawEverythingTest(TempState):
    """Play the adventure through every topic with every starter form, drawing every frame."""

    def play(self, form, topic, rng):
        from bashou import adventure
        with state.locked() as s:
            s["starter"] = next(k for k, forms in creatures.STARTERS.items() if form in forms)
            s["adventure"] = None                                   # a new game each time
        game = adventure.Game(80, 24, rng=rng)
        game.frames, game.palette = sprites.hero(form)
        seen, now = set(), 100.0
        for tick in range(3000):
            adv = game.adv
            now += 0.5
            game.update(0.5, now)
            game.draw(tick * 0.5, now)
            game.hud()
            seen.add(adv["phase"])
            if game.pending_trial:
                game.pending_trial = None
                game.trial_done(True, [])
            elif game.result:
                game.key("\r", now)
            elif adv["phase"] == "fork":
                options = world.fork_options(adv)
                game.choice = options.index(topic) if topic in options else 0
                game.key("\r", now)
            elif adv["phase"] in ("monster", "boss") and game.question:
                game.answer(game.question["answer"], now)
            elif adv["phase"] in ("intro", "lesson", "chest", "chapter_end"):
                game.key("\r", now)
            if tick == 1500:
                game.resize(50, 20)
            if adv["chapter"] > 2:
                break
        return seen

    def test_every_topic_and_every_form(self):
        forms = [f for fs in creatures.STARTERS.values() for f in fs]
        for i, topic in enumerate(sorted(world.TOPICS)):
            with self.subTest(topic):
                seen = self.play(forms[i % len(forms)], topic, random.Random(i))
                self.assertLessEqual({"fork", "walk", "monster", "boss"}, seen)

    def test_every_road_sprite(self):
        for kind in sprites.AHEAD:
            for topic in world.TOPICS:
                rows, palette = sprites.ahead(kind, topic)
                self.assertTrue(set("".join(rows)) - {"."} <= set(palette), (kind, topic))

    def test_every_sprite_in_every_look(self):
        for pet in list(creatures.PETS.values()) + list(creatures.LARGE.values()):
            for look in (1, 2, 3):
                self.assertEqual(len(render.lines(pet, [], render.mask(pet), look)), len(pet.base) // 2)

    def test_every_evolution_scene(self):
        from bashou import evolve
        s = state.load()
        s["starter"] = "star"
        for who in ["starter"] + list(creatures.NAMES):
            for a, b in ((1, 2), (2, 3)):
                self.assertTrue(evolve.scenes(s, {"who": who, "from": a, "to": b}), who)


if __name__ == "__main__":
    unittest.main()
