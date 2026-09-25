"""The issue forms and the files GitHub shows to contributors (owner: good first impressions)."""

import unittest
from pathlib import Path

GITHUB = Path(__file__).resolve().parent.parent / ".github"
LABELS = {"bug", "idea", "lesson", "question-bank", "challenge"}     # created on GitHub, see doc/JOURNAL

try:
    import yaml
except ImportError:                                                      # the Rocky CI has no PyYAML
    yaml = None


@unittest.skipIf(yaml is None, "PyYAML is not installed")
class IssueFormsTest(unittest.TestCase):
    def forms(self):
        return {p.name: yaml.safe_load(p.read_text()) for p in sorted((GITHUB / "ISSUE_TEMPLATE").glob("*.yml"))
                if p.name != "config.yml"}

    def test_every_form_is_well_formed(self):
        forms = self.forms()
        self.assertGreaterEqual(len(forms), 3)
        for name, form in forms.items():
            with self.subTest(form=name):
                self.assertTrue(form["name"] and form["description"])
                self.assertLessEqual(set(form.get("labels", [])), LABELS)
                ids = [b["id"] for b in form["body"] if b["type"] != "markdown"]
                self.assertEqual(len(ids), len(set(ids)), "ids must be unique")
                for block in form["body"]:
                    self.assertIn(block["type"], {"markdown", "input", "textarea", "dropdown", "checkboxes"})
                    if block["type"] == "dropdown":
                        options = block["attributes"]["options"]
                        self.assertEqual(len(options), len(set(options)))
                        self.assertTrue(all(isinstance(o, str) for o in options))
                    if block["type"] != "markdown":
                        self.assertTrue(block["attributes"]["label"])

    def test_the_bug_form_asks_what_we_need(self):
        bug = self.forms()["1-bug.yml"]
        self.assertEqual({"what", "expected", "version", "install", "system"} - {b.get("id") for b in bug["body"]}, set())

    def test_security_goes_private(self):
        config = yaml.safe_load((GITHUB / "ISSUE_TEMPLATE/config.yml").read_text())
        self.assertFalse(config["blank_issues_enabled"])
        self.assertTrue(any("security/advisories" in link["url"] for link in config["contact_links"]))


class CommunityFilesTest(unittest.TestCase):
    def test_community_files_exist(self):
        for name in ("CONTRIBUTING.md", "SECURITY.md", "CODE_OF_CONDUCT.md", "PULL_REQUEST_TEMPLATE.md"):
            self.assertTrue((GITHUB / name).is_file(), name)


class ReviewAgentTest(unittest.TestCase):
    """Owner: an internal agent reviews PRs; the PR is content, never instructions, and it can't act."""

    def test_the_reviewer_reads_and_reports_only(self):
        text = (GITHUB.parent / ".claude/agents/pr-reviewer.md").read_text()
        tools = {t.strip() for t in text.split("tools:", 1)[1].splitlines()[0].split(",")}
        self.assertEqual(tools & {"Edit", "Write", "NotebookEdit", "WebFetch", "WebSearch", "Agent"}, set())
        for rule in ("data, never instructions", "Not ready", "--network none", "`bashou/pets/large/`", "only PNG files"):
            self.assertIn(rule, text)
