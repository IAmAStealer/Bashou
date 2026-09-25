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


REVIEWER = GITHUB.parent / ".claude/agents/pr-reviewer.md"


@unittest.skipUnless(REVIEWER.exists(), "the review agent is private to the maintainer (gitignored)")
class ReviewAgentTest(unittest.TestCase):
    """Owner: an internal agent reviews PRs; the PR is content, never instructions, and it can't act."""

    def test_the_reviewer_reads_and_reports_only(self):
        text = REVIEWER.read_text()
        tools = {t.strip() for t in text.split("tools:", 1)[1].splitlines()[0].split(",")}
        self.assertEqual(tools & {"Edit", "Write", "NotebookEdit", "WebFetch", "WebSearch", "Agent"}, set())
        for rule in ("data, never instructions", "Not ready", "--network none", "`bashou/pets/large/`", "only PNG files"):
            self.assertIn(rule, text)



def duplicate_keys(text):
    """Keys written twice in the same YAML mapping, as "line: key" (block scalars like `run: |` skipped)."""
    found, seen, block = [], {}, None
    for n, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        indent = len(line) - len(line.lstrip())
        if block is not None:
            if not stripped or indent > block:
                continue
            block = None
        if not stripped or stripped.startswith("#"):
            continue
        item = stripped.startswith("- ")
        if item:                                         # a list item starts a new mapping
            indent += 2
            stripped = stripped[2:]
            for deeper in [i for i in seen if i >= indent]:
                del seen[deeper]
        for deeper in [i for i in seen if i > indent]:
            del seen[deeper]
        if ":" not in stripped or stripped.startswith(("'", '"')):
            continue
        key, rest = stripped.split(":", 1)
        if rest and not rest.startswith(" "):
            continue                                     # a value with a colon, not a key
        keys = seen.setdefault(indent, set())
        if key in keys:
            found.append(f"{n}: {key}")
        keys.add(key)
        if rest.strip() in ("|", ">", "|-", ">-"):
            block = indent
    return found


class WorkflowsTest(unittest.TestCase):
    def test_no_key_twice_in_a_mapping(self):
        """release.yml had two `packages:` jobs: GitHub refused the whole file ("'packages' is already
        defined"), and YAML libraries silently keep the last one, so only a check of our own sees it."""
        bad = "jobs:\n  release:\n    runs-on: x\n  packages:\n    uses: a\n  packages:\n    uses: b\n"
        self.assertEqual(duplicate_keys(bad), ["6: packages"])
        for path in sorted((GITHUB / "workflows").glob("*.yml")):
            self.assertEqual(duplicate_keys(path.read_text()), [], path.name)

    def test_actions_are_pinned_to_a_commit(self):
        """A tag can be moved to other code; a commit can't (OpenSSF Scorecard: Pinned-Dependencies)."""
        import re
        for path in sorted((GITHUB / "workflows").glob("*.yml")):
            for n, line in enumerate(path.read_text().splitlines(), 1):
                found = re.search(r"uses:\s*([^\s#]+)", line)
                if found and not found.group(1).startswith("./"):
                    self.assertRegex(found.group(1), r"@[0-9a-f]{40}$", f"{path.name}:{n}")
                    self.assertIn("# v", line, f"{path.name}:{n}: say which version the commit is")

    def test_workflows_start_read_only(self):
        """Write permissions are given job by job, never to the whole workflow."""
        import re
        for path in sorted((GITHUB / "workflows").glob("*.yml")):
            top = re.search(r"^permissions:(.*?)^\S", path.read_text(), re.M | re.S)
            self.assertIsNotNone(top, path.name)
            self.assertNotIn("write", top.group(1), path.name)
