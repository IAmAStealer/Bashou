"""`bashou project`: real programs to build, one small step at a time (owner, 2026-10-02).

For people who want to practise a language but don't know *what* to program. Each project starts very
small and grows: a step says what to do and when it's done, never how. Bashou doesn't read your code:
you say a step is done (`bashou project next`), it explains what that step taught you, then shows the
next one. `bashou project hint` nudges you, without the answer. Finished steps grow the Landscape.

Projects are JSON files (see doc/contributing/projects.md): en/<id>.json holds the project and its steps;
<lang>/<id>.json only translates title, pitch and steps (English fills the gaps).
"""

import functools
import json
from pathlib import Path

from .. import i18n

HERE = Path(__file__).resolve().parent
LANGUAGES = {"python": ("Python", "python"), "shell": ("Shell", "bash"), "c": ("C", "c"), "rust": ("Rust", "rust")}
LEVELS = ["very easy", "easy", "medium", "hard"]
TEXTS = ("do", "done", "hint", "why")


def load(lang=None):
    """Every project, in order (language, then difficulty), translated into `lang` where it can be."""
    lang = lang or i18n.language()
    found = []
    for path in sorted((HERE / "en").glob("*.json")):
        project = json.loads(path.read_text())
        local = HERE / lang / path.name
        if lang != "en" and local.exists():
            tr = json.loads(local.read_text())
            project.update({k: v for k, v in tr.items() if k in ("title", "pitch") and v})
            for step, t in zip(project["steps"], tr.get("steps", [])):
                step.update({k: v for k, v in t.items() if k in TEXTS and v})
        found.append(project)
    return sorted(found, key=lambda p: p["order"])


@functools.lru_cache(maxsize=1)
def english():
    """The English projects, read once: the achievements look at them after every command."""
    return tuple(load("en"))


def sizes():
    """project id -> number of steps."""
    return {p["id"]: len(p["steps"]) for p in english()}


def progress_of(s):
    p = s.setdefault("projects", {})
    p.setdefault("current", "")
    p.setdefault("done", {})
    p.setdefault("days", [])
    return p


def steps_done(s):
    """Steps finished, every project together."""
    known = sizes()
    return sum(min(n, known.get(pid, 0)) for pid, n in progress_of(s)["done"].items())


def finished(s):
    """Ids of the projects whose every step is done."""
    known = sizes()
    return [pid for pid, n in progress_of(s)["done"].items() if pid in known and n >= known[pid]]
