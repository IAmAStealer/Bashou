import contextlib
import io
import json
import re
import tempfile
import unittest
import unittest.mock
from pathlib import Path

from bashou import achievements, creatures, dialogue, i18n, lesson, progress, project, state
from bashou.project import command


def run(*words):
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = command.main(list(words))
    return code, re.sub(r"\x1b\[[0-9;]*m", "", out.getvalue())


def flat(text):
    """Without spaces and line breaks: wrapped output can be compared with the texts of the files."""
    return re.sub(r"\s+", "", text)


class DataTest(unittest.TestCase):
    """Each project is one JSON file per language (doc/contributing/projects.md)."""

    def test_projects_are_complete(self):
        lessons = {le["id"] for le in lesson.english()}
        names = set()
        for p in project.english():
            self.assertIn(p["language"], project.LANGUAGES, p["id"])
            self.assertIn(p["difficulty"], project.LEVELS, p["id"])
            self.assertEqual(p["id"], f"{p['language']}_{p['name']}")
            self.assertNotIn((p["language"], p["name"]), names)
            names.add((p["language"], p["name"]))
            self.assertLessEqual(set(p["lessons"]), lessons, p["id"])
            self.assertTrue(p["title"] and p["pitch"])
            self.assertGreaterEqual(len(p["steps"]), 5, p["id"])
            for step in p["steps"]:
                self.assertEqual(set(step), set(project.TEXTS), p["id"])
                self.assertTrue(all(step[k].strip() for k in project.TEXTS), (p["id"], step))

    def test_every_language_has_its_projects(self):
        """Owner: Python, Shell, C and Rust, from very easy to hard, 13 projects in v0.8.0."""
        self.assertEqual(len(project.english()), 13)
        self.assertEqual({p["language"] for p in project.english()}, set(project.LANGUAGES))
        names = {n for n in re.search(r'^_bashou_projects="([^"]*)"', (Path(project.HERE).parents[1] / "bashou.bash")
                                      .read_text(), re.M).group(1).split()}
        self.assertEqual(names, {p["name"] for p in project.english()})   # Tab offers every project

    def test_translations_match_the_english_steps(self):
        for lang in i18n.LANGUAGES:
            if lang == "en":
                continue
            for p in project.english():
                path = project.HERE / lang / f"{p['id']}.json"
                self.assertTrue(path.exists(), path)
                tr = json.loads(path.read_text())
                self.assertEqual(len(tr["steps"]), len(p["steps"]), path)
                for step in tr["steps"]:
                    self.assertLessEqual(set(step), set(project.TEXTS), path)
                self.assertTrue(tr["title"] and tr["pitch"], path)

    def test_french_falls_back_to_english_where_missing(self):
        fr = {p["id"]: p for p in project.load("fr")}
        en = {p["id"]: p for p in project.english()}
        for pid, p in fr.items():
            self.assertEqual(len(p["steps"]), len(en[pid]["steps"]))
            self.assertTrue(all(s["do"] for s in p["steps"]))


class CommandTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = state.DATA, state.STATE
        state.DATA = Path(self.tmp.name)
        state.STATE = state.DATA / "state.json"
        i18n.use("en")

    def tearDown(self):
        state.DATA, state.STATE = self.saved
        i18n.use(None)
        self.tmp.cleanup()

    def test_one_step_at_a_time(self):
        """Owner: not overwhelming. `next` explains the step you finished, then shows only the next one."""
        code, out = run("start", "python", "photos")
        self.assertEqual(code, 0)
        self.assertIn("Step 1/14", out)
        self.assertNotIn("Step 2/", out)
        code, out = run("next")
        self.assertIn("Step 1 done", out)
        self.assertIn("Working on copies", out)                       # the why of step 1
        self.assertIn("Step 2/14", out)
        self.assertNotIn("Step 3/", out)
        self.assertEqual(state.load()["projects"]["done"], {"python_photos": 1})
        code, out = run("hint")
        self.assertIn("Hint for step 2", out)
        self.assertIn("makedirs", out)
        code, out = run("back")
        self.assertIn("Step 1/14", out)
        self.assertEqual(state.load()["projects"]["done"], {"python_photos": 0})

    def test_the_overview_starts_with_the_current_step(self):
        run("start", "rust", "todo")
        run("next")
        code, out = run()
        self.assertLess(out.index("Step 2/9"), out.index("Python"))
        self.assertIn("1/9", out)

    def test_several_projects_keep_their_own_step(self):
        run("start", "c", "pomodoro")
        run("next")
        run("next")
        run("start", "shell", "backup")
        run("next")
        code, out = run("start", "c", "pomodoro")
        self.assertIn("Welcome back", out)
        self.assertIn("Step 3/10", out)
        self.assertEqual(state.load()["projects"]["done"], {"c_pomodoro": 2, "shell_backup": 1})

    def test_a_finished_project_says_so_and_stops(self):
        p = next(p for p in project.english() if p["id"] == "shell_pdf")
        run("start", "shell", "pdf")
        for _ in p["steps"]:
            code, out = run("next")
        self.assertIn("finished", out)
        self.assertEqual(state.load()["projects"]["current"], "")
        self.assertIn("shell_pdf", project.finished(state.load()))
        code, out = run("next")
        self.assertEqual(code, 1)                                     # nothing started anymore

    def test_unknown_or_ambiguous_names(self):
        code, out = run("start", "cobol", "payroll")
        self.assertEqual(code, 1)
        self.assertIn("Which project", out)
        code, out = run("start", "pdf")                               # Python and Shell both have one
        self.assertEqual(code, 1)
        code, out = run("start", "pomodoro")                          # only C has it
        self.assertEqual(code, 0)
        code, out = run("next")
        self.assertIn("Step 2/10", out)

    def test_next_without_a_project(self):
        code, out = run("next")
        self.assertEqual(code, 1)
        self.assertIn("No project started", out)



class EveryCommandTest(unittest.TestCase):
    """Owner: every command on every project, in every language, answers without an error; then a few
    exact answers in English and in French."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = state.DATA, state.STATE
        state.DATA = Path(self.tmp.name)
        state.STATE = state.DATA / "state.json"

    def tearDown(self):
        state.DATA, state.STATE = self.saved
        i18n.use(None)
        self.tmp.cleanup()

    def ok(self, *words):
        code, out = run(*words)
        self.assertEqual(code, 0, (words, out))
        self.assertTrue(out.strip(), words)
        return out

    def test_every_project_from_start_to_end(self):
        for lang in i18n.LANGUAGES:
            i18n.use(lang)
            for p in project.load(lang):
                with self.subTest(lang=lang, project=p["id"]):
                    steps = p["steps"]
                    out = self.ok(p["language"], p["name"])            # no `start` needed
                    self.assertIn(flat(p["pitch"]), flat(out))
                    self.assertIn(flat(steps[0]["do"]), flat(out))
                    self.assertIn(flat(steps[0]["done"]), flat(out))
                    for n, step in enumerate(steps):
                        self.assertIn(flat(step["hint"]), flat(self.ok("hint")))
                        self.assertIn(flat(step["do"]), flat(self.ok()))        # the overview shows the step
                        out = self.ok("next")
                        self.assertIn(flat(step["why"]), flat(out))
                        if n + 1 < len(steps):
                            self.assertIn(flat(steps[n + 1]["do"]), flat(out))
                            self.assertNotIn(flat(steps[n + 1]["why"]), flat(out))   # one step at a time
                        if n == 1:                                          # back, then forward again
                            self.assertIn(flat(step["do"]), flat(self.ok("back")))
                            self.assertIn(flat(step["why"]), flat(self.ok("next")))
                    self.assertIn(p["id"], project.finished(state.load()))
                    self.assertEqual(run("next")[0], 1)                     # finished: nothing current
                    self.assertEqual(run("hint")[0], 1)
                    self.assertIn(flat(steps[-1]["do"]), flat(self.ok("start", p["language"], p["name"])))
                    self.ok()
            self.assertEqual(sorted(project.finished(state.load())), sorted(p["id"] for p in project.english()))
            state.STATE.unlink()

    def test_wrong_words_answer_with_help(self):
        for lang in i18n.LANGUAGES:
            i18n.use(lang)
            for words in (["start"], ["start", "cobol"], ["python"], ["pdf"], ["dance"], ["start", "python", "x"],
                          ["next"], ["hint"], ["back"]):
                with self.subTest(lang=lang, words=words):
                    code, out = run(*words)
                    self.assertEqual(code, 1, (words, out))
                    self.assertTrue(out.strip())

    def test_english_answers(self):
        i18n.use("en")
        out = self.ok("python", "pdf")
        self.assertIn("Step 1/11 · Merge or split PDFs", out)
        self.assertIn("Done when: the folder holds 2 or 3 PDFs", out)
        self.assertIn("💡 Hint for step 1:", self.ok("hint"))
        out = self.ok("next")
        self.assertIn("✔ Step 1 done.", out)
        self.assertIn("Step 2/11", out)
        self.assertIn("Back one step: it's not done yet.", self.ok("back"))
        self.assertIn("You're on the first step already.", self.ok("back"))
        self.assertIn("Done? bashou project next · Stuck? bashou project hint", self.ok())
        self.assertIn("Which project? For example: bashou project start python photos", run("pdf")[1])
        self.ok("next")
        self.assertIn("Welcome back: you stopped here.", self.ok("start", "python", "pdf"))
        self.assertIn("bashou project [start <language> <project> | next | hint | back]", run("dance")[1])

    def test_french_answers(self):
        i18n.use("fr")
        out = self.ok("python", "pdf")
        self.assertIn("Étape 1/11 · Fusionner ou découper des PDF", out)
        self.assertIn("Terminé quand : le dossier contient 2 ou 3 PDF", out)
        self.assertIn("💡 Indice pour l'étape 1 :", self.ok("hint"))
        out = self.ok("next")
        self.assertIn("✔ Étape 1 terminée.", out)
        self.assertIn("Travailler sur des copies", out)
        self.assertIn("Étape 2/11", out)
        self.assertIn("Une étape en arrière : elle n'est pas encore faite.", self.ok("back"))
        self.assertIn("Fini ? bashou project next · Bloqué ? bashou project hint", self.ok())
        self.assertIn("très facile", self.ok())
        self.assertIn("Quel projet ? Par exemple : bashou project start python photos", run("pdf")[1])
        self.ok("start", "shell", "pdf")
        for _ in range(10):
            out = self.ok("next")
        self.assertIn("Fusionner ou découper des PDF avec un script : terminé !", out)
        self.assertIn("Aucun projet commencé", run("next")[1])

class LandscapeTest(unittest.TestCase):
    """Owner: lots of rewards to keep the motivation; the Landscape grows from a hill to a town."""

    def setUp(self):
        self.s = state.default()

    def finish_steps(self, pid, n, day="2026-10-02"):
        prog = project.progress_of(self.s)
        prog["done"][pid] = prog["done"].get(pid, 0) + n
        if day not in prog["days"]:
            prog["days"].append(day)
        return progress.check(self.s)

    def test_the_first_step_brings_the_landscape(self):
        self.assertNotIn("landscape", self.s["pets"])
        notes = self.finish_steps("python_pdf", 1)
        self.assertIn("landscape", self.s["pets"])
        self.assertIn("first_brick", self.s["achievements"])
        self.assertTrue(any("Hillock" in n for n in notes), notes)

    def test_one_language_is_enough_for_the_town(self):
        """A player who only learns Python (or only Shell, the smallest set) still reaches the Town."""
        for lang in project.LANGUAGES:
            self.s = state.default()
            seen = []
            for p in [p for p in project.english() if p["language"] == lang]:
                for i in range(len(p["steps"])):
                    self.finish_steps(p["id"], 1, f"2026-10-{1 + (i % 7):02d}")
                    seen.append(creatures.form("landscape", progress.reached(self.s, "landscape")))
            self.assertEqual(seen[-1], "town", lang)
            self.assertEqual(seen[0], "hillock", lang)

    def test_forms_come_fast_at_first(self):
        seen = []
        for _ in range(10):
            self.finish_steps("python_photos", 1)
            seen.append(creatures.form("landscape", progress.reached(self.s, "landscape")))
        self.assertEqual(seen[0], "hillock")
        self.assertEqual(seen[2], "cabin")                             # 3 steps
        self.assertEqual(seen[4], "garden")                            # 5 steps
        self.assertEqual(seen[9], "river")                             # 10 steps
        self.assertEqual(len(creatures.FORMS["landscape"]), 10)

    def test_every_project_and_language_has_an_achievement(self):
        ids = {a.id for a in achievements.family("landscape")}
        self.assertEqual(len(ids), 32)
        for p in project.english():
            self.finish_steps(p["id"], len(p["steps"]))
        self.assertLessEqual(ids - {"steady_builder"}, set(self.s["achievements"]))
        self.assertEqual(project.steps_done(self.s), 150)

    def test_each_project_has_its_achievement(self):
        self.assertEqual({pid for pid, *_ in achievements.PROJECT_ACHIEVEMENTS}, {p["id"] for p in project.english()})

    def test_a_week_of_steps_in_a_row(self):
        for day in range(1, 8):
            self.s["projects"]["days"].append(f"2026-10-{day:02d}")
        self.s["projects"]["done"]["rust_todo"] = 7
        with unittest.mock.patch("bashou.achievements.date") as d:
            from datetime import date
            d.today.return_value = date(2026, 10, 7)
            progress.check(self.s)
        self.assertIn("steady_builder", self.s["achievements"])

    def test_the_pet_reminds_you_of_your_project(self):
        import random
        self.assertIsNone(dialogue.project_nudge(self.s, random.Random(1)))
        self.s["projects"] = {"current": "python_photos", "done": {"python_photos": 3}, "days": []}
        self.assertIn("step 4", dialogue.project_nudge(self.s, random.Random(1)))

    def test_old_saves_get_an_empty_project_list(self):
        s = state.read(json.dumps({"language": "en", "starter": "star"}))
        self.assertEqual(s["projects"], {"current": "", "done": {}, "days": []})
        s = state.read(json.dumps({"projects": {"current": 3, "done": {"a": "x", "b": 2}, "days": "no"}}))
        self.assertEqual(s["projects"], {"current": "", "done": {"b": 2}, "days": []})


if __name__ == "__main__":
    unittest.main()
