"""Bash scripts, a skill of their own (r/bash mods, 2026-10-22; owner: split prompt bash and script bash, with
lessons, questions, fights and an adventure path, and a small template for scripts). Each fight hands you a
script built on the template with one bug that only bites on real-life input; verify runs your script again,
on fresh tricky input, so only a real fix wins."""

import json
import random
import tempfile
import unittest
from pathlib import Path

from bashou import challenges, lesson, skills, state
from bashou.adventure import lessons as road, sprites, world

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = (ROOT / "bashou" / "challenges" / "template.sh").read_text()

LESSONS = ["scripts", "prompt_script", "script_errors", "script_files", "script_data", "script_cleanup"]
AFTER = {"scripts": "quotes", "prompt_script": "scripts", "script_errors": "prompt_script",
         "script_files": "script_errors", "script_data": "script_files", "script_cleanup": "script_errors"}

# fight: (its lesson, its script, the buggy line(s), the fix)
FIGHTS = {
    "dash_demon": ("script_files", "tidy.sh",
                   '    mv "$f" trash/ || die "cannot move $f"',
                   '    mv -- "$f" trash/ || die "cannot move $f"'),
    "nomatch_nymph": ("script_files", "count.sh",
                      "    n=$((n + 1))",
                      "    [[ -e $f ]] || continue\n    n=$((n + 1))"),
    "newline_nixie": ("script_files", "size.sh",
                      '  for f in $(ls "$dir"); do\n    total=$((total + $(wc -c < "$dir/$f")))',
                      '  for f in "$dir"/*; do\n    [[ -f $f ]] || continue\n    total=$((total + $(wc -c < "$f")))'),
    "stdin_siren": ("script_files", "check.sh",
                    '    ./remote "$host" uptime',
                    '    ./remote "$host" uptime < /dev/null'),
    "masked_mole": ("script_errors", "stamp.sh",
                    '  local sum=$(cksum < "$1") || die "cannot read $1"',
                    '  local sum\n  sum=$(cksum < "$1") || die "cannot read $1"'),
    "errexit_eel": ("script_errors", "errors.sh",
                    "      ((count++))",
                    "      count=$((count + 1))"),
    "echo_echidna": ("script_data", "names.sh",
                     '    echo "$name"',
                     "    printf '%s\\n' \"$name\""),
    "trap_troll": ("script_cleanup", "report.sh",
                   "tmp=/tmp/bashou-report.tmp",
                   "tmp=$(mktemp) || exit 1\ntrap 'rm -f -- \"$tmp\"' EXIT"),
}


class SkillTest(unittest.TestCase):
    def test_scripts_come_right_after_the_prompt(self):
        self.assertEqual(list(skills.SKILLS)[:2], ["bash", "script"])
        self.assertIn("prompt", skills.SKILLS["bash"].text.lower())
        self.assertIn("script", skills.SKILLS["script"].text.lower())

    def test_scripts_are_an_adventure_topic_with_a_boss(self):
        self.assertIn("script", world.TOPICS)
        self.assertIsNotNone(sprites.boss("script"))

    def migrated(self, picks, version=6):
        s = state.default()
        s["skills"], s["version"] = picks, version
        return state.migrate(s, dict(s))["skills"]

    def test_bash_learners_get_scripts_too(self):
        self.assertEqual(self.migrated(["bash", "python"]), ["bash", "script", "python"])
        self.assertEqual(self.migrated(["python"]), ["python"])
        self.assertEqual(self.migrated("all"), "all")

    def test_scripts_turned_off_stay_off(self):
        self.assertEqual(self.migrated(["bash"], version=state.SAVE_VERSION), ["bash"])


class LessonTest(unittest.TestCase):
    def setUp(self):
        self.by_id = {le["id"]: le for le in lesson.load("en")}

    def test_the_script_path(self):
        for lid in LESSONS:
            with self.subTest(lid):
                le = self.by_id[lid]
                self.assertEqual(le.get("skill"), "script")
                self.assertIn(AFTER[lid], le["after"])
                self.assertIn("bash", le.get("tools", []), "reading it opens the script fights (fight.ready)")

    def test_french_has_every_page(self):
        fr = {le["id"]: le for le in lesson.load("fr")}
        for lid in LESSONS:
            with self.subTest(lid):
                self.assertEqual(len(fr[lid]["pages"]), len(self.by_id[lid]["pages"]))
                self.assertNotEqual(fr[lid]["title"], self.by_id[lid]["title"])

    def test_every_script_fight_has_its_lesson(self):
        for cid, (lid, *_rest) in FIGHTS.items():
            with self.subTest(cid):
                self.assertIn(cid, self.by_id[lid].get("fights", []))

    def test_shebang_shade_moved_to_scripts(self):
        self.assertEqual(challenges.BY_ID["shebang_shade"].skill, "script")


class FightTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def fight(self, cid, seed):
        work = Path(self.tmp.name) / f"{cid}-{seed}"
        work.mkdir()
        c = challenges.BY_ID[cid]
        meta = c.setup(work, random.Random(seed))
        meta = json.loads(json.dumps(meta))                     # as the arena stores it
        return c, work, meta

    def test_every_script_fight_is_a_script_fight(self):
        for cid, (_lid, script, _bug, _fix) in FIGHTS.items():
            with self.subTest(cid):
                c = challenges.BY_ID[cid]
                self.assertEqual(c.skill, "script")
                self.assertTrue(c.fix)
                self.assertEqual(c.file, script)
                self.assertIn("bash", c.tools)
                self.assertTrue(c.hints and c.why)

    def test_the_starter_is_the_template(self):
        for cid, (_lid, script, bug, _fix) in FIGHTS.items():
            with self.subTest(cid):
                _c, work, _meta = self.fight(cid, 0)
                text = (work / script).read_text()
                self.assertTrue(text.startswith("#!/usr/bin/env bash\n# "))
                self.assertIn("die() { printf '%s: %s\\n' \"${0##*/}\" \"$*\" >&2; exit 1; }", text)
                self.assertTrue(text.endswith('\nmain "$@"\n'))
                self.assertIn(bug, text)

    def test_the_bug_loses(self):
        for cid in FIGHTS:
            for seed in range(3):
                with self.subTest(cid, seed=seed):
                    c, work, meta = self.fight(cid, seed)
                    self.assertFalse(c.verify(work, meta, ""))
                    self.assertTrue(c.why(work), "says what went wrong")

    def test_the_fix_wins(self):
        for cid, (_lid, script, bug, fix) in FIGHTS.items():
            for seed in range(3):
                with self.subTest(cid, seed=seed):
                    c, work, meta = self.fight(cid, seed)
                    path = work / script
                    path.write_text(path.read_text().replace(bug, fix))
                    self.assertTrue(c.verify(work, meta, ""), c.why(work))

    def test_doing_the_job_by_hand_loses(self):
        """Only the script counts: verify runs it again on fresh input, it doesn't look at what's left here."""
        for cid, (_lid, script, _bug, _fix) in FIGHTS.items():
            with self.subTest(cid):
                c, work, meta = self.fight(cid, 1)
                (work / script).write_text("#!/usr/bin/env bash\nexit 0\n")
                self.assertFalse(c.verify(work, meta, ""))


class QuestionTest(unittest.TestCase):
    def bank(self, lang):
        return json.loads((ROOT / "bashou" / "adventure" / "questions" / lang / "script.json").read_text())

    def test_a_bank_on_every_level(self):
        qs = self.bank("en")
        self.assertGreaterEqual(len(qs), 24)
        for level in (1, 2, 3):
            self.assertGreaterEqual(sum(q["level"] == level for q in qs), 6, level)
        self.assertTrue(all(q["id"].startswith(f"script-{q['level']}-") for q in qs))

    def test_french_matches(self):
        en, fr = self.bank("en"), self.bank("fr")
        self.assertEqual([(q["id"], q["level"], q["answer"]) for q in en],
                         [(q["id"], q["level"], q["answer"]) for q in fr])


class RoadTest(unittest.TestCase):
    def test_the_owl_teaches_scripts_on_the_road_and_a_chest_follows(self):
        mine = [le for le in road.LESSONS if "script" in le["topics"]]
        self.assertGreaterEqual(len(mine), 2)
        for le in mine:
            with self.subTest(le["id"]):
                self.assertTrue(any(le["tool"] in t.tools for t in challenges.TRIALS), "a chest practices it")
