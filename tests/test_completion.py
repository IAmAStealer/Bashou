import re
import subprocess
import unittest
from pathlib import Path

from bashou import challenges
from bashou.creatures import FAMILIES, NAMES

LOADER = Path(__file__).resolve().parent.parent / "bashou.bash"
ZSH_LOADER = LOADER.with_suffix(".zsh")


def words(name, loader=LOADER):
    return re.search(rf'^{name}="([^"]*)"', loader.read_text(), re.M).group(1).split()


def complete(line):
    """Run the completion function on `line` (cursor at the end) in a real bash."""
    script = f"""
source <(sed -n '/^_bashou_commands=/,/^complete /p' {LOADER})
COMP_WORDS=({line}{' ""' if line.endswith(' ') else ''})
COMP_CWORD=$(( ${{#COMP_WORDS[@]}} - 1 ))
_bashou_complete
echo "${{COMPREPLY[*]}}"
"""
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True).stdout.split()


def complete_zsh(line):
    """The same in zsh: _bashou_words gets the words up to the cursor (the last may be empty) and sets
    reply to the candidates that start with the last one. compadd (the real Tab) only shows them."""
    from tests.test_shell import need
    need("zsh")
    script = f"""
source <(sed -n '/^_bashou_commands=/,/^_bashou_words_end/p' {ZSH_LOADER})
_bashou_words {line}{' ""' if line.endswith(' ') else ''}
print -r -- "${{reply[*]}}"
"""
    return subprocess.run(["zsh", "-c", script], capture_output=True, text=True).stdout.split()


class CompletionTest(unittest.TestCase):
    def test_lists_match_the_code(self):
        from bashou import cli
        self.assertEqual(words("_bashou_pets"), [p for p in NAMES if not FAMILIES[p].secret])   # no secret pet
        self.assertEqual(set(words("_bashou_challenges")), {c.id for c in challenges.ALL})
        self.assertEqual(words("_bashou_security"), [str(i) for i in range(1, len(challenges.SECURITY) + 1)])
        offered = [c.name for c in cli.COMMANDS if not c.hidden]
        self.assertEqual(set(words("_bashou_commands")), set(offered))     # hidden commands aren't offered
        self.assertEqual(len(offered + [c.name for c in cli.COMMANDS if c.hidden]), len({c.name for c in cli.COMMANDS}))
        from bashou import i18n
        self.assertEqual(words("_bashou_languages"), list(i18n.LANGUAGES))
        dev = next(c for c in cli.COMMANDS if c.name == "dev")
        self.assertEqual(words("_bashou_dev"), dev.args[0][1]["choices"])

    def test_completes(self):
        self.assertEqual(complete("bashou s"), ["spot", "share", "swap", "stats", "start"])
        self.assertEqual(complete("bashou swap st"), ["starter"])
        self.assertEqual(complete("bashou swap f"), ["frog", "fox"])
        self.assertEqual(complete("bashou dev st"), ["stage", "stage-all"])
        self.assertEqual(complete("bashou dev threat aw"), ["awk_golem"])
        self.assertEqual(complete("bashou dev stage fox "), ["1", "2", "3"])
        self.assertEqual(complete("bashou level "), [])
        self.assertEqual(complete("bashou config la"), ["language"])
        self.assertEqual(complete("bashou arena s"), ["security"])
        self.assertEqual(complete("bashou arena security "), words("_bashou_security"))
        self.assertEqual(complete("bashou config language f"), ["fr"])

    def test_zsh_has_the_same_lists(self):
        for name in ("_bashou_commands", "_bashou_pets", "_bashou_languages", "_bashou_dev", "_bashou_challenges",
                     "_bashou_security", "_bashou_projects", "_bashou_lessons"):
            self.assertEqual(words(name, ZSH_LOADER), words(name), name)

    def test_zsh_completes_like_bash(self):
        for line in ("bashou s", "bashou swap st", "bashou swap f", "bashou dev st", "bashou dev threat aw",
                     "bashou dev stage fox ", "bashou level ", "bashou config la", "bashou arena s",
                     "bashou arena security ", "bashou config language f", "bashou lesson pa", "bashou project start "):
            self.assertEqual(complete_zsh(line), complete(line), line)


if __name__ == "__main__":
    unittest.main()
