import re
import subprocess
import unittest
from pathlib import Path

from bashou import challenges
from bashou.creatures import FAMILIES, NAMES

LOADER = Path(__file__).resolve().parent.parent / "bashou.bash"


def words(name):
    return re.search(rf'^{name}="([^"]*)"', LOADER.read_text(), re.M).group(1).split()


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
        self.assertEqual(complete("bashou s"), ["share", "swap", "stats", "start"])
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


if __name__ == "__main__":
    unittest.main()
