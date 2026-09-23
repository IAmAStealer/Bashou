"""CI/CD fights (owner, 2026-09-23): fix a GitHub Actions workflow or a .gitlab-ci.yml. A step indented
wrong, a stage that doesn't exist, a token written in clear, a deploy that doesn't wait for the tests
or runs on every branch, a deploy that should wait for a click (when: manual).

The files live in the arena and are read by meaning, not letter by letter: [a, b] or a list, quotes or
not, rules or only/except. Python has no YAML reader, so `load` reads the plain subset pipelines use.
"""

import re

from . import Challenge
from .repos import EDITORS

# --- a small YAML reader --------------------------------------------------------------------------

KEY = re.compile(r"""^("[^"]*"|'[^']*'|[^\s"'#:][^:#]*?)\s*:(?:\s+(.*))?$""")


def _lines(text):
    if "\t" in text:
        raise ValueError("a tab: YAML only allows spaces")
    out = []
    for n, raw in enumerate(text.splitlines(), 1):
        line = re.sub(r"\s+#.*$", "", raw) if "#" in raw and not re.search(r"""["'].*#.*["']""", raw) else raw
        if line.strip() and not line.lstrip().startswith("#"):
            out.append((len(line) - len(line.lstrip(" ")), line.strip(), n))
    return out


def _scalar(text):
    text = text.strip()
    if text[:1] in "\"'" and text[-1:] == text[:1] and len(text) > 1:
        return text[1:-1]
    if text.startswith("[") and text.endswith("]"):
        return [_scalar(part) for part in text[1:-1].split(",") if part.strip()]
    return text


def _block(lines, i, indent):
    if i < len(lines) and lines[i][1].startswith("-") and lines[i][1][1:2] in ("", " "):
        return _list(lines, i, indent)
    return _map(lines, i, indent)


def _value(lines, i, indent, rest):
    """The value after `key:` on line i-1: inline, a | block, or the block below."""
    if rest in ("|", ">", "|-", ">-"):
        text = []
        while i < len(lines) and lines[i][0] > indent:
            text.append(lines[i][1])
            i += 1
        return "\n".join(text), i
    if rest:
        return _scalar(rest), i
    if i < len(lines) and lines[i][0] > indent:
        return _block(lines, i, lines[i][0])
    if i < len(lines) and lines[i][0] == indent and lines[i][1].startswith("- "):
        return _list(lines, i, indent)                     # key:\n- item, at the same indent
    return None, i


def _map(lines, i, indent):
    out = {}
    while i < len(lines) and lines[i][0] == indent and not lines[i][1].startswith("- "):
        col, text, n = lines[i]
        m = KEY.match(text)
        if not m:
            raise ValueError(f"line {n}: expected 'key: value'")
        key = _scalar(m.group(1))
        out[key], i = _value(lines, i + 1, indent, (m.group(2) or "").strip())
    if i < len(lines) and lines[i][0] > indent:
        raise ValueError(f"line {lines[i][2]}: indented more than the line before it expects")
    return out, i


def _list(lines, i, indent):
    out = []
    while i < len(lines) and lines[i][0] == indent and lines[i][1].startswith("-"):
        col, text, n = lines[i]
        item = text[1:].lstrip()
        if not item:
            if i + 1 < len(lines) and lines[i + 1][0] > indent:
                value, i = _block(lines, i + 1, lines[i + 1][0])
            else:
                value, i = None, i + 1
        elif KEY.match(item) and not item.startswith(("[", "\"", "'")):
            inner = indent + len(text) - len(item)          # "- key: v": a mapping at the key's column
            value, i = _map_from(lines, i, n, inner, item)
        else:
            value, i = _scalar(item), i + 1
        out.append(value)
    if i < len(lines) and lines[i][0] > indent:
        raise ValueError(f"line {lines[i][2]}: indented more than the line before it expects")
    return out, i


def _map_from(lines, i, n, inner, item):
    """A mapping whose first key sits on the list line itself ("- name: x")."""
    patched = lines[:i] + [(inner, item, n)] + lines[i + 1:]
    return _map(patched, i, inner)


def load(text):
    """Plain YAML (mappings, lists, scalars, [a, b], | blocks) -> dicts and lists. ValueError if broken."""
    lines = _lines(text)
    if not lines:
        return {}
    value, i = _block(lines, 0, lines[0][0])
    if i < len(lines):
        raise ValueError(f"line {lines[i][2]}: indented less than the start, or a stray line")
    return value


def read(work, name):
    try:
        data = load((work / name).read_text())
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    return data if isinstance(data, dict) else None


def as_list(value):
    return value if isinstance(value, list) else [] if value is None else [value]


# --- GitHub Actions -------------------------------------------------------------------------------

CHECKOUT = "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2"
WORKFLOW = ".github/workflows/ci.yml"

GH_OK = f"""name: CI
on:
  push:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: {CHECKOUT}
      - name: Test
        run: python3 -m unittest
"""

# (right line, wrong line): one of them is planted
INDENT_MISTAKES = [
    ("        run: python3 -m unittest\n", "       run: python3 -m unittest\n"),
    ("        run: python3 -m unittest\n", "          run: python3 -m unittest\n"),
    ("    runs-on: ubuntu-latest\n", "     runs-on: ubuntu-latest\n"),
    ("      - name: Test\n", "     - name: Test\n"),
    ("    steps:\n", "  steps:\n"),
]


def write(work, name, text):
    path = work / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def indent_setup(work, rng):
    right, wrong = rng.choice(INDENT_MISTAKES)
    write(work, WORKFLOW, GH_OK.replace(right, wrong, 1))
    return {}


def indent_verify(work, meta, value):
    data = read(work, WORKFLOW)
    if not data or not isinstance(data.get("jobs"), dict) or not isinstance(data["jobs"].get("test"), dict):
        return False
    job = data["jobs"]["test"]
    steps = job.get("steps")
    return (job.get("runs-on") == "ubuntu-latest" and isinstance(steps, list) and len(steps) == 2
            and all(isinstance(s, dict) for s in steps)
            and str(steps[0].get("uses", "")).startswith("actions/checkout@")
            and "unittest" in str(steps[1].get("run", "")))


GH_SECRET = f"""name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: {CHECKOUT}
      - name: Publish
        env:
          API_TOKEN: {{token}}
        run: ./publish.sh
"""
SECRET_REF = re.compile(r"^\$\{\{\s*secrets\.API_TOKEN\s*\}\}$")


def secret_setup(work, rng):
    token = "ghp_" + "".join(rng.choice("ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789")
                             for _ in range(36))
    write(work, WORKFLOW, GH_SECRET.replace("{token}", token))
    return {"token": token}


def secret_verify(work, meta, value):
    data = read(work, WORKFLOW)
    if not data or meta["token"] in (work / WORKFLOW).read_text():
        return False
    try:
        step = data["jobs"]["deploy"]["steps"][1]
        return bool(SECRET_REF.match(str(step["env"]["API_TOKEN"]))) and "publish" in str(step.get("run", ""))
    except (KeyError, IndexError, TypeError):
        return False


GH_NEEDS = f"""name: CI
on:
  push:
  pull_request:
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: {CHECKOUT}
      - run: python3 -m unittest
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: {CHECKOUT}
      - run: ./deploy.sh
"""
MAIN_REF = re.compile(r"""github\.ref\s*==\s*['"]refs/heads/main['"]|github\.ref_name\s*==\s*['"]main['"]""")


def needs_setup(work, rng):
    write(work, WORKFLOW, GH_NEEDS)
    return {}


def needs_verify(work, meta, value):
    data = read(work, WORKFLOW)
    try:
        deploy = data["jobs"]["deploy"]
        test = data["jobs"]["test"]
    except (KeyError, TypeError):
        return False
    if not isinstance(deploy, dict) or not isinstance(test, dict) or "./deploy.sh" not in str(deploy.get("steps")):
        return False
    return "test" in as_list(deploy.get("needs")) and bool(MAIN_REF.search(str(deploy.get("if", ""))))


# --- GitLab CI ------------------------------------------------------------------------------------

GITLAB = ".gitlab-ci.yml"
RESERVED = {"stages", "variables", "default", "include", "workflow", "image", "services", "before_script",
            "after_script", "cache", "spec"}

GL_STAGES = """stages:
  - build
  - test
  - deploy

build:
  stage: build
  script:
    - make

unit:
  stage: {stage}
  script:
    - make check

deploy:
  stage: deploy
  script:
    - ./deploy.sh
"""


def jobs(data):
    return {k: v for k, v in data.items() if k not in RESERVED and not str(k).startswith(".") and isinstance(v, dict)}


def stage_setup(work, rng):
    write(work, GITLAB, GL_STAGES.replace("{stage}", rng.choice(["tests", "testing", "check", "unit-test"])))
    return {}


def stage_verify(work, meta, value):
    data = read(work, GITLAB)
    if not data:
        return False
    stages = as_list(data.get("stages"))
    found = jobs(data)
    return (set(found) == {"build", "unit", "deploy"} and {"build", "test", "deploy"} <= set(stages)
            and all(job.get("stage", "test") in stages and job.get("script") for job in found.values())
            and found["unit"].get("stage", "test") == "test")


GL_MANUAL = """stages:
  - test
  - deploy

unit:
  stage: test
  script:
    - make check

deploy:
  stage: deploy
  script:
    - ./deploy.sh
"""
ON_MAIN = re.compile(r"""\$CI_COMMIT_(BRANCH|REF_NAME)\s*==\s*(['"]main['"]|\$CI_DEFAULT_BRANCH)""")


def manual_setup(work, rng):
    write(work, GITLAB, GL_MANUAL)
    return {}


def manual_verify(work, meta, value):
    data = read(work, GITLAB)
    job = data and jobs(data).get("deploy")
    if not job or "./deploy.sh" not in str(job.get("script")) or set(jobs(data)) != {"unit", "deploy"}:
        return False
    rules = job.get("rules")
    if rules is not None:
        if "when" in job or not isinstance(rules, list):
            return False                                   # GitLab refuses when: next to rules:
        manual = [r for r in rules if isinstance(r, dict) and ON_MAIN.search(str(r.get("if", "")))
                  and r.get("when") == "manual"]
        catch_all = [r for r in rules if isinstance(r, dict) and "if" not in r and r.get("when") != "never"]
        return bool(manual) and not catch_all
    only = job.get("only")
    refs = only.get("refs") if isinstance(only, dict) else only
    return job.get("when") == "manual" and as_list(refs) == ["main"]


# --- the fights -----------------------------------------------------------------------------------

YAML_OUTLINE = ("YAML is written like an outline: a line pushed further right belongs to the line above it. "
                "Each level is 2 spaces further right, and lines that belong together start at the same place.")
YAML_NEIGHBOURS = ("Find the line that doesn't start where its neighbours do. runs-on: and steps: both belong to "
                   "the job, so they line up; name: and run: both belong to the same step, so they line up too.")

CICD = dict(pet="beaver", tools=EDITORS, requires=["sed"], skill="cicd", fix=True)

ALL = [
    Challenge(level=1, id="indent_imp", threat="Indent Imp", **CICD,
              task="The Indent Imp pushed one line of the GitHub workflow " + WORKFLOW + " out of line.\n"
                   "Put it back in line, so the job test has its two steps: checkout, then the tests. "
                   "Then: verify",
              hints=[YAML_OUTLINE, YAML_NEIGHBOURS],
              setup=indent_setup, verify=indent_verify),
    Challenge(level=1, id="stage_specter", threat="Stage Specter", **CICD,
              task="The Stage Specter renamed a stage in " + GITLAB + ": GitLab refuses the pipeline, "
                   "'unit job: chosen stage does not exist'.\nMake every job use a stage from the stages: list, "
                   "without renaming the stages. Then: verify",
              hints=["The file starts with a dot, so ls hides it: ls -a shows it. stages: lists build, test and "
                     "deploy, in the order they run; each job's stage: must be one of them.",
                     "The unit job runs the tests, so its stage is test. Open the file (nano .gitlab-ci.yml) and "
                     "change the unit job's line to `  stage: test`, keeping its 2 spaces."],
              setup=stage_setup, verify=stage_verify),
    Challenge(level=2, id="secret_sprite", threat="Secret Sprite", **CICD,
              task="The Secret Sprite wrote an API token in clear in " + WORKFLOW + ": anyone who can read the "
                   "repository can steal it.\nMake the step read it from the repository's secrets instead "
                   "(the secret is called API_TOKEN). Then: verify",
              hints=["GitHub keeps secrets outside the code (Settings > Secrets). A workflow reads one with "
                     "${{ secrets.NAME }}: the value never appears in the file, and it's hidden in the logs.",
                     "Replace the token with ${{ secrets.API_TOKEN }} on the API_TOKEN: line. In real life, "
                     "the leaked token must also be revoked: it stays in the git history."],
              setup=secret_setup, verify=secret_verify),
    Challenge(level=2, id="needs_newt", threat="Needs Newt", **CICD,
              task="The Needs Newt lets " + WORKFLOW + " deploy even when the tests fail, and from every branch.\n"
                   "Make the deploy job wait for the test job, and run only on the main branch. Then: verify",
              hints=["Jobs run side by side unless told otherwise. needs: test makes deploy wait for test, and "
                     "skips it if test fails. A job-level if: decides whether it runs at all.",
                     "Under `deploy:`, at the level of runs-on, add two lines: `needs: test` and "
                     "`if: github.ref == 'refs/heads/main'`."],
              setup=needs_setup, verify=needs_verify),
    Challenge(level=2, id="manual_mole", threat="Manual Mole", **CICD,
              task="The Manual Mole makes " + GITLAB + " deploy to production on every push, on every branch.\n"
                   "Make the deploy job appear only on main, and wait for someone to click it (manual). "
                   "Then: verify",
              hints=["rules: is a list of conditions, read in order; the first that matches decides. Each can "
                     "say when: manual, so the job waits for a click in the pipeline page. A branch that "
                     "matches no rule gets no deploy job at all.",
                     "Under deploy:, add: rules:, then a list item "
                     "`- if: $CI_COMMIT_BRANCH == \"main\"` with `when: manual` under it (2 more spaces)."],
              setup=manual_setup, verify=manual_verify),
]

# The Sage Owl's chest for the CI/CD path: the same broken indentation, no enemy.
from .trials import trial  # noqa: E402

INDENT_CHEST = trial("trial_ci_indent", 2, "A pipeline file hides in this chest: " + WORKFLOW + ". One line is out "
                     "of line. Put it back, so the job test has its two steps. Then: verify",
                     [YAML_OUTLINE, YAML_NEIGHBOURS], indent_setup, indent_verify, requires=["sed"], teaches=["yaml"])
