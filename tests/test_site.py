"""The share page (doc/site): anyone can write the link it reads, so it must stay locked down."""

import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from bashou import share, state

SITE = Path(__file__).resolve().parent.parent / "doc/site"


class SharePageTest(unittest.TestCase):
    def setUp(self):
        self.html = (SITE / "share.html").read_text()
        self.js = (SITE / "share.js").read_text()

    def test_locked_page(self):
        csp = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', self.html).group(1)
        for rule in ("default-src 'none'", "script-src 'self'", "base-uri 'none'", "form-action 'none'"):
            self.assertIn(rule, csp)
        self.assertNotIn("unsafe", csp)
        self.assertIn('name="referrer" content="no-referrer"', self.html)
        self.assertNotRegex(self.html, r"<script>|<script [^>]*>[^<]")             # no inline code
        self.assertNotRegex(self.html, r"\son\w+=")                                  # no onclick=…
        self.assertNotRegex(self.html, r"https?://(?!github\.com/IAmAStealer/Bashou)")  # nothing loaded from elsewhere

    def test_no_dangerous_calls(self):
        for bad in ("innerHTML", "outerHTML", "insertAdjacentHTML", "eval(", "new Function", "document.write",
                    "setTimeout(\"", "localStorage", "cookie"):
            self.assertNotIn(bad, self.js)
        self.assertEqual(re.findall(r'fetch\("([^"]+)"', self.js), ["share-pets.json"])

    def test_same_keys_and_name_rule_as_bashou(self):
        keys = re.search(r"const KEYS = \[([^\]]+)\]", self.js).group(1)
        self.assertEqual(re.findall(r'"(\w+)"', keys), list(share.KEYS))
        self.assertIn(share.NAME.pattern.join("^$"), self.js.replace("\\/", "/"))

    def test_page_data_draws_every_family(self):
        data = share.page_data()
        for family, info in data["families"].items():
            self.assertEqual(len(info["forms"]), len(info["en"]))
            self.assertEqual(len(info["forms"]), len(info["fr"]))
            for sprite in info["forms"]:
                self.assertIn(sprite, data["sprites"])
        s = state.default()
        s["starter"] = "sprout"
        card = share.payload(s)
        self.assertIn(card["p"], data["families"])

    @unittest.skipUnless(shutil.which("node"), "node isn't installed")
    def test_hostile_links_are_refused(self):
        s = state.default()
        s["starter"] = "star"
        good = share.link(share.payload(s, "Alexis"))
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["python3", str(SITE.parent.parent / "tools/package.py"), "site", tmp], check=True)
            done = subprocess.run(["node", str(Path(__file__).with_name("share_page.js")), f"{tmp}/share.js",
                                   f"{tmp}/share-pets.json", good], capture_output=True, text=True)
        self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
