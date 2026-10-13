"""macOS (owner, 2026-10-13): Bashou runs on a Mac, and what you learn follows the OS.

Content may say "os": "linux" or "macos" (no "os": for everyone). The OS is read when Bashou runs, never
at install; `bashou config os linux|macos|both` changes what you learn (a Mac user who runs Linux
servers turns Linux on). Fights always follow the machine itself: a Linux fight can't run on a Mac.
"""

import json
import os
import pty
import random
import re
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

from bashou import challenges, setup, skills, state, which
from bashou.adventure import quiz, world
from bashou.lesson import reader

ROOT = Path(__file__).resolve().parent.parent
MAC = {"settings": {}}                  # a save with no `bashou config os`: the OS it runs on


def on(platform):
    return mock.patch("bashou.which.platform", return_value=platform)


class PlatformTest(unittest.TestCase):
    def test_the_os_is_read_from_python(self):
        with mock.patch.object(sys, "platform", "darwin"):
            self.assertEqual(which.platform(), "macos")
        with mock.patch.object(sys, "platform", "linux"):
            self.assertEqual(which.platform(), "linux")

    def test_what_you_learn_follows_the_os_unless_you_say_otherwise(self):
        with on("macos"):
            self.assertEqual(skills.oses(MAC), {"macos"})
            self.assertEqual(skills.oses({"settings": {"os": "linux"}}), {"linux"})
            self.assertEqual(skills.oses({"settings": {"os": "both"}}), {"linux", "macos"})
        with on("linux"):
            self.assertEqual(skills.oses(MAC), {"linux"})
            self.assertEqual(skills.oses({"settings": {"os": "macos"}}), {"macos"})

    def test_bashou_config_os(self):
        setting = state.SETTINGS["os"]
        self.assertEqual(setting.default, "auto")
        for value in ("linux", "macos", "both"):
            self.assertEqual(state.parse("os", value), value)
        with self.assertRaises(ValueError):
            state.parse("os", "windows")
        for loader in ("bashou.bash", "bashou.zsh"):
            text = (ROOT / loader).read_text()
            self.assertRegex(text, r'2:config:\*\)\s+words="[^"]*\bos\b', loader)
            self.assertIn('3:config:os)      words="linux macos both default"', text, loader)


class QuestionsTest(unittest.TestCase):
    BANK = [{"id": "t-1-01", "level": 1, "q": "everyone"}, {"id": "t-1-02", "level": 1, "q": "linux", "os": "linux"},
            {"id": "t-1-03", "level": 1, "q": "mac", "os": "macos"}, {"id": "t-2-01", "level": 2, "q": "l2", "os": "linux"}]

    def bank(self, topic, lang=None):
        return [dict(q, choices=["a", "b", "c", "d"], answer=0, explain="x") for q in self.BANK]

    def test_a_question_of_another_os_never_comes(self):
        with mock.patch.object(quiz, "bank", side_effect=self.bank):
            for seed in range(30):
                q = quiz.pick("t", 1, [], random.Random(seed), {"macos"})
                self.assertIn(q["q"], ("everyone", "mac"))
                q = quiz.pick("t", 1, [], random.Random(seed), {"linux"})
                self.assertIn(q["q"], ("everyone", "linux"))
            self.assertEqual(quiz.max_level("t", {"macos"}), 1)       # level 2 is Linux only
            self.assertEqual(quiz.max_level("t", {"linux", "macos"}), 2)
            self.assertEqual(quiz.for_os(self.bank("t"), {"linux", "macos"}), self.bank("t"))

    def test_os_tags_are_checked(self):
        q = dict(self.bank("t")[0], os="windows")
        self.assertTrue(any("os" in p for p in quiz.problems([q])))
        self.assertEqual(quiz.problems(self.bank("t")), [])

    def test_translations_keep_the_os_of_each_question(self):
        for path in sorted((quiz.HERE / "en").glob("*.json")):
            en = {q["id"]: q.get("os") for q in json.loads(path.read_text())}
            for other in sorted(quiz.HERE.glob(f"*/{path.name}")):
                for q in json.loads(other.read_text()):
                    with self.subTest(f"{other.parent.name} {q['id']}"):
                        self.assertEqual(q.get("os"), en.get(q["id"]))

    LINUX_ONLY = re.compile(r"\b(systemctl|journalctl|apt|dnf|dpkg|rpm|ss -\w+|ip (addr|route|-br)|getent|nproc|"
                            r"resolvectl|free -h|/etc/fstab|/proc)\b")

    def test_questions_about_linux_only_commands_say_so(self):
        """systemd, Debian and Rocky are Linux topics (their skill says so); elsewhere each question
        that needs a Linux-only command is tagged."""
        for path in sorted((quiz.HERE / "en").glob("*.json")):
            topic = path.stem
            for q in json.loads(path.read_text()):
                text = q["q"] + " " + q["choices"][q["answer"]]          # the point; an aside in explain is fine
                if skills.SKILLS[topic].os or not self.LINUX_ONLY.search(text):
                    continue
                with self.subTest(q["id"]):
                    self.assertEqual(q.get("os"), "linux", self.LINUX_ONLY.search(text).group(0))


class SkillsTest(unittest.TestCase):
    def test_linux_skills(self):
        self.assertEqual({k for k, sk in skills.SKILLS.items() if sk.os == "linux"}, {"systemd", "debian", "rocky"})

    def test_a_mac_learns_no_linux_skill_until_asked(self):
        with on("macos"):
            self.assertFalse(skills.wanted(MAC, "systemd"))
            self.assertTrue(skills.wanted(MAC, "bash"))
            self.assertNotIn("debian", skills.picked(MAC))
            self.assertIn("debian", skills.picked({"settings": {"os": "both"}}))
            self.assertIn("bashou config os", skills.note("systemd", MAC))
        with on("linux"):
            self.assertTrue(skills.wanted(MAC, "systemd"))
            self.assertFalse(skills.wanted({"settings": {"os": "macos"}}, "rocky"))

    def test_the_forks_of_a_mac_offer_no_linux_path(self):
        with on("macos"):
            for chapter in range(1, 6):
                for leg in range(3):
                    adv = dict(world.new(), chapter=chapter, leg=leg)
                    options = world.fork_options(adv, ["bash"], skills.topics(MAC))
                    self.assertFalse(set(options) & {"systemd", "debian", "rocky"}, options)
                    self.assertIn("bash", options)


class LessonsTest(unittest.TestCase):
    def test_pages_and_lessons_of_another_os_are_left_out(self):
        lessons = [{"id": "a", "pages": [{"text": ["all"]}, {"text": ["linux"], "os": "linux"},
                                         {"text": ["mac"], "os": "macos"}]},
                   {"id": "b", "os": "linux", "pages": [{"text": ["x"]}]}]
        mac = reader.for_os(lessons, {"macos"})
        self.assertEqual([le["id"] for le in mac], ["a"])
        self.assertEqual([p["text"] for p in mac[0]["pages"]], [["all"], ["mac"]])
        self.assertEqual(len(reader.for_os(lessons, {"linux", "macos"})[0]["pages"]), 3)

    def test_every_lesson_keeps_a_page_on_every_os(self):
        from bashou import lesson
        for lang in ("en", "fr"):
            for le in reader.for_os(lesson.load(lang), {"macos"}):
                with self.subTest(f"{lang} {le['id']}"):
                    self.assertTrue(le["pages"])
                    self.assertIn(le.get("os"), (None, "macos"))

    def test_lesson_os_tags_match_between_languages(self):
        from bashou import lesson
        en = {le["id"]: [p.get("os") for p in le["pages"]] for le in lesson.load("en")}
        for le in lesson.load("fr"):
            with self.subTest(le["id"]):
                self.assertEqual([p.get("os") for p in le["pages"]], en[le["id"]])

    def test_the_warm_up_skips_questions_of_another_os(self):
        from bashou import lesson
        net = lesson.by_id()["tcp"]
        with on("macos"):
            for seed in range(10):
                for q in reader.warmup({"skills": "all", "settings": {}}, net, random.Random(seed)):
                    self.assertNotEqual(q.get("os"), "linux", q["id"])


class FightsTest(unittest.TestCase):
    def test_a_linux_fight_never_comes_on_a_mac(self):
        ch = next(c for c in challenges.ALL if c.os == "linux")
        with on("macos"):
            self.assertFalse(ch.available())

    def test_fights_that_need_linux_say_so(self):
        """The reference solutions show what a fight needs: one with a Linux-only command is a Linux fight
        (or its skill is: systemd, Debian, Rocky)."""
        from tests.test_fight import SOLUTIONS
        linux = re.compile(r"\b(systemctl|journalctl|apt|dnf|dpkg|rpm|ss|ip|getent|nproc|resolvectl|free -h|"
                           r"useradd|/proc|stat -c|timeout|tac|shuf|numfmt)\b")
        for ch in challenges.ALL + challenges.SECURITY + challenges.TRIALS:
            cmd = SOLUTIONS[ch.id][0]
            if linux.search(cmd) and not skills.SKILLS[ch.skill].os:
                with self.subTest(ch.id):
                    self.assertEqual(ch.os, "linux", linux.search(cmd).group(0))

    def test_mac_players_learn_the_bsd_sed_i(self):
        ch = challenges.BY_ID["sed_serpent"]
        meta = ch.setup(Path(self.tmp()), random.Random(0))
        mac = ch.hint_list({**meta, "platform": "macos"})
        self.assertIn("sed -i ''", mac[-1])
        self.assertNotIn("sed -i ''", " ".join(ch.hint_list({**meta, "platform": "linux"})))
        plain = challenges.BY_ID["line_moth"]
        meta = plain.setup(Path(self.tmp()), random.Random(0))
        self.assertEqual(plain.hint_list({**meta, "platform": "macos"}), plain.hint_list(meta))

    def tmp(self):
        import tempfile
        d = tempfile.TemporaryDirectory()
        self.addCleanup(d.cleanup)
        return d.name


class ProcessesTest(unittest.TestCase):
    """macOS has no /proc: the parent of a process, its command line and whether its shell is at the prompt
    come from ps and the terminal itself."""

    def test_parent_and_command_without_proc(self):
        from bashou import procs
        with mock.patch.object(procs, "PROC", False):
            ppid, name = procs.parent(os.getpid())
            self.assertEqual(ppid, os.getppid())
            self.assertIn("python", name)
            self.assertIn("python", procs.command(os.getpid()))
            self.assertIsNone(procs.parent(2 ** 22 + 7))

    def test_parent_and_command_agree_with_proc(self):
        from bashou import procs
        if not procs.PROC:
            self.skipTest("no /proc here")
        with mock.patch.object(procs, "PROC", False):
            slow = procs.parent(os.getpid()), procs.command(os.getpid()).split()[0]
        self.assertEqual((procs.parent(os.getpid()), procs.command(os.getpid()).split()[0]), slow)

    def test_at_prompt_without_proc(self):
        """The shell owns the terminal (foreground process group) at its prompt; not while a command runs.
        A child on its own pseudo-terminal plays the shell: it hands the terminal to a command, then back."""
        code = (
            "import os, signal, subprocess, sys\n"
            "from unittest import mock\n"
            "from bashou import procs\n"
            "with mock.patch.object(procs, 'PROC', False):\n"
            "    seen = [procs.at_prompt(os.getpid(), 0)]\n"
            "    signal.signal(signal.SIGTTOU, signal.SIG_IGN)\n"
            "    cmd = subprocess.Popen(['sleep', '5'], process_group=0) if sys.version_info >= (3, 11) else "
            "subprocess.Popen(['sleep', '5'], preexec_fn=lambda: os.setpgid(0, 0))\n"
            "    os.tcsetpgrp(0, cmd.pid)\n"
            "    seen.append(procs.at_prompt(os.getpid(), 0))\n"
            "    seen.append(procs.at_prompt(cmd.pid, 0))\n"
            "    os.tcsetpgrp(0, os.getpgrp())\n"
            "    seen.append(procs.at_prompt(os.getpid(), 0))\n"
            "    seen.append(procs.at_prompt(2 ** 22 + 7, 0))\n"
            "    cmd.kill()\n"
            "print('SEEN', seen)\n")
        pid, fd = pty.fork()
        if pid == 0:
            os.chdir(ROOT)
            os.execv(sys.executable, [sys.executable, "-c", code])
        out = b""
        while True:
            try:
                chunk = os.read(fd, 1024)
            except OSError:
                break
            if not chunk:
                break
            out += chunk
        os.waitpid(pid, 0)
        os.close(fd)
        self.assertIn("SEEN [True, False, True, True, False]", out.decode(), out.decode())

    def test_no_proc_outside_procs(self):
        """Only bashou/procs.py and the Linux-only network fights read /proc."""
        for path in (ROOT / "bashou").rglob("*.py"):
            if path.name == "procs.py" or path.name == "network.py":
                continue
            with self.subTest(path.name):
                self.assertNotIn('"/proc', path.read_text())
                self.assertNotIn("f\"/proc", path.read_text())


class SetupTest(unittest.TestCase):
    def test_an_old_bash_gets_no_line(self):
        """macOS's own bash is 3.2: too old for Bashou (PS0 came in 4.4). Its ~/.bashrc stays untouched."""
        import tempfile
        with tempfile.TemporaryDirectory() as home, mock.patch.dict(os.environ, {"HOME": home}), \
                mock.patch("bashou.setup.bash_version", return_value=(3, 2)), \
                mock.patch("shutil.which", return_value="/bin/bash"):
            self.assertFalse(setup.bash_ok())
            self.assertFalse(setup.add_other("bash", data=home))
            self.assertFalse((Path(home) / ".bashrc").exists())
            setup.run(shell="zsh", off=Path(home) / "off")
            self.assertFalse((Path(home) / ".bashrc").exists())
            self.assertTrue((Path(home) / ".zshrc").exists())
        with mock.patch("bashou.setup.bash_version", return_value=(5, 2)):
            self.assertTrue(setup.bash_ok())

    def test_bash_version(self):
        self.assertGreaterEqual(setup.bash_version(), (4, 4))       # Linux and CI have a recent bash

    def test_the_bash_loader_stops_on_an_old_bash(self):
        text = (ROOT / "bashou.bash").read_text()
        head = text[:text.index("BASHOU_DIR")]
        self.assertIn("BASH_VERSINFO", head)
        self.assertIn("return", head)


class DocsTest(unittest.TestCase):
    def test_the_readme_says_how_to_install_on_a_mac(self):
        for name in ("README.md", "README.fr.md"):
            text = (ROOT / name).read_text()
            with self.subTest(name):
                self.assertIn("macOS", text)
                self.assertIn("xcode-select --install", text)
                self.assertIn("git clone -b macos https://github.com/IAmAStealer/Bashou.git ~/.bashou", text)
                self.assertIn("source ~/.bashou/bashou.zsh' >> ~/.zshrc", text)

    def test_ci_runs_the_tests_on_a_mac(self):
        text = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertIn("runs-on: macos-latest", text)
        self.assertRegex(text, r"branches: \[main, macos\]")


if __name__ == "__main__":
    unittest.main()
