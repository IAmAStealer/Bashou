import re
import subprocess
import unittest
from pathlib import Path

from bashou import challenges
from bashou.creatures import ROSTER, SECRET

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
        self.assertEqual(words("_bashou_pets"), [p for p, _ in ROSTER if p not in SECRET])   # no secret pet
        self.assertEqual(set(words("_bashou_challenges")), {c.id for c in challenges.ALL})
        self.assertEqual(words("_bashou_security"), [str(i) for i in range(1, len(challenges.SECURITY) + 1)])
        parser_src = Path(cli.__file__).read_text()
        commands = re.findall(r'sub\.add_parser\("([\w-]+)"', parser_src)
        self.assertEqual(set(words("_bashou_commands")), set(commands))
        from bashou import explain
        for lang, topics in explain.NOTES.items():
            self.assertEqual(complete(f"bashou explain {lang} "), list(topics))
        self.assertEqual(complete("bashou explain "), list(explain.NOTES))
        dev = re.search(r'choices=\[("unlock-all".*?)\]', parser_src).group(1)
        self.assertEqual(words("_bashou_dev"), re.findall(r'"([\w-]+)"', dev))

    def test_completes(self):
        self.assertEqual(complete("bashou s"), ["swap", "stats", "start", "security"])
        self.assertEqual(complete("bashou swap st"), ["starter"])
        self.assertEqual(complete("bashou swap f"), ["frog", "fox"])
        self.assertEqual(complete("bashou dev st"), ["stage", "stage-all"])
        self.assertEqual(complete("bashou dev threat aw"), ["awk_golem"])
        self.assertEqual(complete("bashou dev stage fox "), ["1", "2", "3"])
        self.assertEqual(complete("bashou level "), [])


if __name__ == "__main__":
    unittest.main()
