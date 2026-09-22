"""Security rules for the code itself (also run by CI):

- only Python's standard library: no third-party package to trust or keep patched;
- no network code: the only thing that talks to GitHub is `git fetch` in update.py;
- no dynamic code or shell strings: no eval/exec/pickle/os.system/shell=True.
"""

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCES = sorted((ROOT / "bashou").rglob("*.py"))
NETWORK = {"socket", "ssl", "http", "urllib", "ftplib", "smtplib", "telnetlib", "xmlrpc", "asyncio"}
BANNED_CALLS = {"eval", "exec", "compile", "__import__"}
BANNED_MODULES = {"pickle", "marshal", "shelve"}


def imports(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            yield node.module.split(".")[0]


class SecurityTest(unittest.TestCase):
    def trees(self):
        return [(p.relative_to(ROOT), ast.parse(p.read_text())) for p in SOURCES]

    @unittest.skipUnless(hasattr(sys, "stdlib_module_names"), "needs Python 3.10+")
    def test_only_the_standard_library(self):
        for path, tree in self.trees():
            for name in imports(tree):
                self.assertIn(name, sys.stdlib_module_names, f"{path}: third-party import {name}")

    def test_no_network_or_unsafe_modules(self):
        for path, tree in self.trees():
            for name in imports(tree):
                self.assertNotIn(name, NETWORK | BANNED_MODULES, f"{path}: imports {name}")

    def test_no_dynamic_code_or_shell_strings(self):
        for path, tree in self.trees():
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if isinstance(func, ast.Name):                     # eval(), not re.compile()
                    self.assertNotIn(func.id, BANNED_CALLS, f"{path}:{node.lineno} calls {func.id}()")
                if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name) and func.value.id == "os":
                    self.assertNotIn(func.attr, {"system", "popen"}, f"{path}:{node.lineno} runs a shell string")
                for kw in node.keywords:
                    self.assertFalse(kw.arg == "shell" and getattr(kw.value, "value", False) is True,
                                     f"{path}:{node.lineno} uses shell=True")

    def test_only_update_talks_to_git(self):
        for path, tree in self.trees():
            text = (ROOT / path).read_text()
            if '["git"' in text:                               # an argv list that runs git
                self.assertEqual(path.name, "update.py", f"{path} runs git")


if __name__ == "__main__":
    unittest.main()
