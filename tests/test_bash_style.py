"""The bash Bashou shows follows doc/contributing/bash-style.md (r/bash mods, 2026-10-22: "passable BASH, not good
BASH"; no line between bash typed at the prompt and bash in scripts). Every script a fight writes, the script
template, the code of lesson pages and our own shell code pass bash -n and ShellCheck; the text players read
never teaches the script habits the rules forbid."""

import importlib.util
import json
import os
import random
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from bashou import challenges, lesson

ROOT = Path(__file__).resolve().parent.parent
SHELLCHECK = shutil.which("shellcheck")
TEMPLATE = ROOT / "bashou" / "challenges" / "template.sh"
OURS = [ROOT / "bashou.bash", ROOT / "bashou" / "room.bash", ROOT / "bashou" / "handover.bash",
        *sorted((ROOT / "tools").glob("*.sh")), TEMPLATE]
QUESTIONS = ROOT / "bashou" / "adventure" / "questions" / "en"

# The bug a fight's file holds on purpose, since the player fixes it: what ShellCheck may say about it.
ON_PURPOSE = {
    "shebang_shade": {"SC2148", "SC1113"},  # the ! of #! is missing: the shell is unknown
    "nomatch_nymph": {"SC2034"},            # the loop counts turns: f is the bug's witness
    "newline_nixie": {"SC2045"},            # for f in $(ls ...): the bug
    "masked_mole": {"SC2155"},              # local x=$(cmd): the bug
}
# Files whose first line is the lesson: not #!/usr/bin/env bash, on purpose.
SHEBANG_ON_PURPOSE = {"shebang_shade"}
# Where set -e is taught with its holes (bash-style S4); nowhere else.
SET_E_TEACHES = {"script_errors", "errexit_eel"}


def shellcheck(path):
    """ShellCheck's codes for a file: as sh under #!/bin/sh, as bash otherwise."""
    shell = "sh" if path.read_text().startswith("#!/bin/sh") else "bash"
    done = subprocess.run([SHELLCHECK, "-s", shell, "-f", "gcc", str(path)], capture_output=True, text=True,
                          timeout=60)
    return set(re.findall(r"\[(SC\d+)\]", done.stdout)), done.stdout


def syntax(path):
    done = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True, timeout=10)
    return done.returncode == 0, done.stderr


def fight_scripts(seeds=range(3)):
    """(fight id, file name, text) of every bash script a fight or chest writes."""
    for c in challenges.ALL + challenges.TRIALS:
        if not c.available():               # a Linux-only fight on a Mac: its setup can wait for minutes
            continue
        for seed in seeds:
            with tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                try:
                    meta = c.setup(work, random.Random(seed))
                except (OSError, RuntimeError):     # no loopback here (a sandbox): these write no script
                    continue
                for p in sorted(work.rglob("*")):
                    if ".git" in p.relative_to(work).parts or not p.is_file() or p.is_symlink():
                        continue
                    try:
                        text = p.read_text()
                    except (UnicodeDecodeError, OSError):
                        continue
                    first = text.split("\n", 1)[0]
                    if p.suffix in (".sh", ".bash") or (first.startswith("#") and "bash" in first):
                        yield c.id, p.name, text
                if c.cleanup:
                    c.cleanup(meta)


def lessons(skill=None):
    return [le for le in lesson.load("en") if skill is None or le.get("skill") == skill]


def questions(topic):
    path = QUESTIONS / f"{topic}.json"
    return json.loads(path.read_text()) if path.exists() else []


class Lint(unittest.TestCase):
    def need_shellcheck(self):
        if SHELLCHECK:
            return
        if os.environ.get("BASHOU_REQUIRE_SHELLCHECK"):
            self.fail("ShellCheck is required here (BASHOU_REQUIRE_SHELLCHECK) and not installed")
        self.skipTest("ShellCheck not installed (apt install shellcheck)")

    def lint_file(self, path, allowed=frozenset()):
        ok, err = syntax(path)
        self.assertTrue(ok, f"bash -n {path}: {err}")
        codes, report = shellcheck(path)
        self.assertLessEqual(codes, set(allowed), report)


class TemplateTest(Lint):
    def test_the_template_is_clean(self):
        self.need_shellcheck()
        self.lint_file(TEMPLATE)

    def test_the_template_checks_its_arguments(self):
        no_args = subprocess.run(["bash", str(TEMPLATE)], capture_output=True, text=True, timeout=10)
        self.assertEqual(no_args.returncode, 2, "usage error: status 2")
        self.assertIn("usage:", no_args.stderr)
        self.assertEqual(no_args.stdout, "", "errors go to stderr")
        missing = subprocess.run(["bash", str(TEMPLATE), "/nonexistent/x"], capture_output=True, text=True,
                                 timeout=10)
        self.assertEqual(missing.returncode, 1)
        self.assertIn("not a file: /nonexistent/x", missing.stderr)
        with tempfile.NamedTemporaryFile(prefix="-n ") as f:
            fine = subprocess.run(["bash", str(TEMPLATE), f.name], capture_output=True, text=True, timeout=10)
            self.assertEqual(fine.returncode, 0, fine.stderr)

    def test_the_template_has_no_set_e(self):
        self.assertNotIn("set -e", TEMPLATE.read_text(), "S4: set -e is its own lesson, chosen knowingly")


class OurCodeTest(Lint):
    def test_our_shell_code_is_clean(self):
        self.need_shellcheck()
        for path in OURS:
            with self.subTest(path.name):
                self.lint_file(path, {"SC1091"})    # a note: sourced files are linted on their own


class FightScriptTest(Lint):
    def test_every_script_a_fight_writes_parses(self):
        with tempfile.TemporaryDirectory() as tmp:
            for cid, name, text in fight_scripts():
                with self.subTest(cid, file=name):
                    path = Path(tmp) / name
                    path.write_text(text)
                    ok, err = syntax(path)
                    self.assertTrue(ok, f"{cid} {name}: {err}")

    def test_every_script_a_fight_writes_is_shellcheck_clean(self):
        self.need_shellcheck()
        with tempfile.TemporaryDirectory() as tmp:
            for cid, name, text in fight_scripts(range(1)):
                with self.subTest(cid, file=name):
                    path = Path(tmp) / name
                    path.write_text(text)
                    codes, report = shellcheck(path)
                    self.assertLessEqual(codes, ON_PURPOSE.get(cid, set()), f"{cid}:\n{report}")

    def test_fights_this_machine_cant_run_are_skipped(self):
        """CI macOS (v0.10.5): loopback_lurker's setup waited 3 min for a port its Mac couldn't see."""
        from unittest import mock
        fight = challenges.BY_ID["loopback_lurker"]
        with mock.patch.object(type(fight), "available", lambda self: self.id != "loopback_lurker"), \
                mock.patch.object(fight, "setup", side_effect=AssertionError("setup ran")):
            self.assertNotIn("loopback_lurker", {cid for cid, _, _ in fight_scripts(range(1))})

    def test_scripts_name_bash_portably(self):
        for cid, name, text in fight_scripts(range(1)):
            if cid in SHEBANG_ON_PURPOSE:
                continue
            with self.subTest(cid, file=name):
                self.assertIn(text.split("\n", 1)[0], ("#!/usr/bin/env bash", "#!/bin/sh"),
                              "S1: /bin/bash is 3.2 on a Mac; plain sh scripts may say #!/bin/sh")


class PackageShellTest(Lint):
    """The sh the .deb and .rpm install: the wrapper, the profile hook, postinst and prerm."""

    def scripts(self):
        spec = importlib.util.spec_from_file_location("package", ROOT / "tools/package.py")
        package = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(package)
        return {"wrapper": package.WRAPPER, "profile": "#!/bin/sh\n" + package.PROFILE,
                "postinst": f"#!/bin/sh\nset -e\n{package.COMPILE}\n", "prerm": f"#!/bin/sh\nset -e\n{package.CLEAN}\n"}

    def test_package_scripts_are_plain_sh(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name, text in self.scripts().items():
                with self.subTest(name):
                    path = Path(tmp) / name
                    path.write_text(text)
                    done = subprocess.run(["sh", "-n", str(path)], capture_output=True, text=True, timeout=10)
                    self.assertEqual(done.returncode, 0, done.stderr)
                    if SHELLCHECK:
                        codes, report = shellcheck(path)
                        self.assertLessEqual(codes, {"SC1091"}, report)   # the sourced files are installed ones


class LessonCodeTest(Lint):
    def test_script_code_is_drawn_on_its_page(self):
        for le in lessons():
            for n, page in enumerate(le["pages"], 1):
                if "script" in page:
                    with self.subTest(le["id"], page=n):
                        drawn = "\n".join(page.get("scheme", []))
                        for line in page["script"]:
                            self.assertIn(line.strip(), drawn, "the page shows the code it checks")

    def test_script_code_of_lessons_is_clean(self):
        self.need_shellcheck()
        with tempfile.TemporaryDirectory() as tmp:
            for le in lessons():
                for n, page in enumerate(le["pages"], 1):
                    if "script" not in page:
                        continue
                    with self.subTest(le["id"], page=n):
                        code = "\n".join(page["script"]) + "\n"
                        if not code.startswith("#!"):
                            code = "#!/usr/bin/env bash\n" + code
                        path = Path(tmp) / f"{le['id']}-{n}.sh"
                        path.write_text(code)
                        self.lint_file(path, set(page.get("shellcheck_ok", [])))

    def test_every_script_lesson_checks_its_code(self):
        for le in lessons("script"):
            with self.subTest(le["id"]):
                self.assertTrue(any("script" in p for p in le["pages"]), "a page with a \"script\" field")


# --- the text players read -------------------------------------------------------------------------------

BANNED_IN_SCRIPTS = [
    (r"#!/bin/bash\b", "S1: #!/usr/bin/env bash"),
    (r"\$\(ls\b", "S7: globs, never ls output"),
    (r"for \w+ in \$\(cat\b", "S8: while IFS= read -r"),
    (r"while (?!IFS= )read\b", "S8: while IFS= read -r"),
    (r"\b(?:local|export|readonly) \w+=[\"']?\$\(", "S5: declare apart, then assign"),
    (r"\bfunction \w+", "S15: name() {"),
]
BANNED_EVERYWHERE = [
    (r"\b(?:local|export|readonly) \w+=[\"']?\$\(", "S5: the builtin hides the command's status"),
    (r"\b\w+=\"?\$\(pass show [^)]*\)\"?(?!\s*(?:\|\||&&))", "S2: a password read by pass is checked (|| exit 1)"),
]


def texts_of_lesson(le):
    for n, page in enumerate(le["pages"], 1):
        for line in page.get("scheme", []) + page.get("text", []):
            yield f"{le['id']} page {n}", line


def texts_of_question(q):
    """The right answer and its explanation: the question itself may show the bug, wrong choices too."""
    yield q["id"], q["choices"][q["answer"]]
    yield q["id"], q.get("explain", "")


def texts_of_fight(c):
    for t in [c.task, c.help, c.needs, c.zsh, *c.hints]:
        for line in t.split("\n"):
            yield c.id, line


def projects(language=None):
    for path in sorted((ROOT / "bashou" / "project" / "en").glob("*.json")):
        project = json.loads(path.read_text())
        if language is None or project["language"] == language:
            yield project


def texts_of_project(project):
    for n, step in enumerate(project["steps"], 1):
        for key in ("do", "done", "hint", "why"):
            yield f"{project['id']} step {n}", step.get(key, "")


def script_texts():
    for project in projects("shell"):
        yield from texts_of_project(project)
    for le in lessons("script"):
        yield from texts_of_lesson(le)
    for q in questions("script"):
        yield from texts_of_question(q)
    for c in challenges.ALL + challenges.TRIALS:
        if c.skill == "script":
            yield from texts_of_fight(c)


def all_texts():
    for le in lessons():
        yield le["id"], texts_of_lesson(le)
    by_lesson = {qid: le["id"] for le in lessons() for qid in le.get("recall", []) + le.get("questions", [])}
    for path in sorted(QUESTIONS.glob("*.json")):
        for q in json.loads(path.read_text()):
            yield by_lesson.get(q["id"], q["id"]), texts_of_question(q)
    for c in challenges.ALL + challenges.TRIALS:
        yield c.id, texts_of_fight(c)
    for project in projects():
        yield project["id"], texts_of_project(project)


class TextTest(unittest.TestCase):
    def test_script_content_teaches_script_habits(self):
        for where, line in script_texts():
            if "✘" in line:
                continue
            for pattern, rule in BANNED_IN_SCRIPTS:
                with self.subTest(where, rule=rule):
                    self.assertIsNone(re.search(pattern, line), f"{where}: {line!r}")

    def test_no_habit_that_hides_failures(self):
        for owner, lines in all_texts():
            for where, line in lines:
                if "✘" in line:
                    continue
                for pattern, rule in BANNED_EVERYWHERE:
                    with self.subTest(where, rule=rule):
                        self.assertIsNone(re.search(pattern, line), f"{where}: {line!r}")

    def test_road_lessons_check_pass_too(self):
        # (achievement examples are prompt lines: there pass's error shows on the screen)
        for path in (ROOT / "bashou/adventure/lessons.py",):
            for n, line in enumerate(path.read_text().split("\n"), 1):
                for pattern, rule in BANNED_EVERYWHERE:
                    with self.subTest(path.name, line=n, rule=rule):
                        self.assertIsNone(re.search(pattern, line.replace('\\"', '"')), line)

    def test_set_e_only_where_its_holes_are_taught(self):
        for owner, lines in all_texts():
            if owner in SET_E_TEACHES:
                continue
            for where, line in lines:
                with self.subTest(where):
                    self.assertNotIn("set -e", line, f"S4: {where}: {line!r}")


# --- bugs the first bash-judge pass found (2026-10-22) ----------------------------------------------------

class ReviewFixesTest(unittest.TestCase):
    def bash(self, script, **env):
        return subprocess.run(["bash", "-c", script], capture_output=True, text=True, timeout=10,
                              env={**os.environ, **env})

    def test_a_write_that_fails_stays_quiet(self):
        """`echo 0 > "$f" 2>/dev/null` still prints the error: the file is opened before 2> applies."""
        done = self.bash(f'source "{ROOT}/bashou/room.bash"; _bashou_room=/nonexistent/x/room; '
                         '_bashou_erase=/nonexistent/x/erase; _bashou_hide')
        self.assertEqual(done.stderr, "")
        for path in (ROOT / "bashou.bash", ROOT / "bashou" / "room.bash"):
            for n, line in enumerate(path.read_text().split("\n"), 1):
                with self.subTest(path.name, line=n):
                    self.assertIsNone(re.search(r'(?<!\{) (?:>|>\||>>) "\$\w+"(?: [^;{]*)? 2>/dev/null', line), line)

    def test_a_bad_height_file_is_not_code(self):
        """room.bash reads the pet's height from a file into (( )): junk there must not run."""
        with tempfile.TemporaryDirectory() as tmp:
            height = Path(tmp) / "height"
            height.write_text(f"a[$(touch {tmp}/ran)]\n")
            done = self.bash(f'source "{ROOT}/bashou/room.bash"; _bashou_height={height}; _bashou_below')
            self.assertFalse((Path(tmp) / "ran").exists())
            self.assertEqual(done.stdout, "\x1b[7B", "the default height")

    def test_the_door_keeps_regex_and_options_out(self):
        """grep -qx "$1" read the name as a pattern: '.*' got in, and -v made grep wait for the keyboard."""
        from bashou.challenges import logic
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            meta = logic.door_setup(work, random.Random(0))
            door = work / "door.sh"
            self.assertIn('grep -qxF -- "$1" guests.txt', door.read_text())
            door.write_text(door.read_text().replace("if ! grep -qxF --", "if grep -qx"))
            self.assertFalse(logic.door_verify(work, meta, ""), "a regex guard lets '.*' in")
            door.write_text(door.read_text().replace("if grep -qx", "if grep -qxF --"))
            self.assertTrue(logic.door_verify(work, meta, ""))
