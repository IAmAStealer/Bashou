"""The hidden ponies (owner, 2026-10-09): a herd of secret pets, each hiding somewhere real.

`bashou pony` alone brings the Foal (only `bashou --help` mentions it), then hints at where the others
hide, without ever giving their word. Six of them need a short word that only their hiding place shows:
the changelog, doc/easter_egg in the repository, the apt/dnf description, the site's source, a closed
issue on GitHub and the bug report form (owner, 2026-10-10). The words
are only stored as hashes, so reading the code spoils nothing. The others come by themselves when the pet
sees you type a famous terminal joke (cowsay, apt moo, make love...).
"""

import hashlib
import re

from . import creatures, progress, render, state
from .i18n import _
from .render import BOLD, DIM, RESET

FOAL = "pony_foal"


def digest(word):
    return hashlib.sha256(word.strip().lower().encode()).hexdigest()[:16]


PONIES = {                       # digest of the word -> the pony it brings
    "9212e9c844fc6553": "pony_wrecking",      # CHANGELOG.md: the "Breaking change" line of every release
    "897abbb178d59a98": "pony_explorer",      # doc/easter_egg
    "4e30ea25cda1c18c": "pony_package",       # tools/package.py: the packages' short description
    "0470cc4e7d943c45": "pony_web",           # doc/install.html and doc/install.fr.html: an HTML comment
    "d3cb20eb37275c8c": "pony_detective",     # a closed issue on GitHub (not in the repository)
    "c5924fae93560d14": "pony_form",          # .github/ISSUE_TEMPLATE bug forms: an HTML comment in "Anything else"
}

# Terminal jokes the pet notices: the pony comes right away. Failures count too: `make love` and `:wq`
# always fail, that's the joke.
JOKES = [
    ("pony_jealous", re.compile(r"(^|[\s|;&(])cowsay\b")),
    ("pony_moo", re.compile(r"(^|[\s;&(])apt(-get)?\s+moo\b")),
    ("pony_heart", re.compile(r"(^|[\s;&(])make\s+love\s*$")),
    ("pony_library", re.compile(r"(^|[\s;&(])man\s+woman\s*$")),
    ("pony_chef", re.compile(r"(^|[\s;&(])sudo\s+make\s+me\s+a\s+sandwich\s*$")),
    ("pony_vim", re.compile(r"^\s*:(wq?|x|q)!?\s*$")),
]


def arrivals():
    """What the pet says when a joke brings a pony."""
    return {
        "pony_jealous": _("A pony peeks in, a little jealous of the cow, and joins your herd. Meet it: bashou pets"),
        "pony_moo": _("Moo? A pony answers the cow and joins your herd. Meet it: bashou pets"),
        "pony_heart": _("No rule to make love… but a pony comes for a hug and joins your herd. Meet it: bashou pets"),
        "pony_library": _("No manual for that, but a pony brings you a book and joins your herd. Meet it: bashou pets"),
        "pony_chef": _("Okay, a sandwich: a pony in a chef's hat brings it and joins your herd. Meet it: bashou pets"),
        "pony_vim": _("You're not in vim anymore! A pony who knows the feeling joins your herd. Meet it: bashou pets"),
    }


def where():
    """What a pony claimed with `bashou pony` says: where you found it, and what that teaches."""
    return {
        "pony_foal": _("You found me in `bashou --help`. Most programs answer to `--help` with a summary of "
                       "their options, so curious people try it first. Keep doing that with every new tool."),
        "pony_wrecking": _("You found me in the changelog. Every Bashou release lists what changed, and a "
                           "\"breaking change\" is one that stops an old habit from working. Reading the "
                           "changelog before updating saves you surprises."),
        "pony_explorer": _("You found me in doc/easter_egg, in the documentation of Bashou's repository. RTFM, "
                           "\"Read The F*** Manual\", is the oldest advice in computing: most answers are already "
                           "written in the docs, so read them before asking."),
        "pony_package": _("You found me in the package description that `apt search` and `dnf search` show. "
                          "Those searches read the name and short description of every package they know."),
        "pony_web": _("You found me in an HTML comment in the source of Bashou's site. Browsers hide comments, "
                      "but View source (Ctrl+U) shows everything a page is made of."),
        "pony_detective": _("You found me in a closed issue on GitHub. Before you report a problem, search the "
                            "issues, closed ones too: someone may already have asked, and the answer is waiting."),
        "pony_form": _("You found me in the bug report form. A form asks the right questions: what you did, what "
                       "you expected and what happened. Answer them all, and your bug gets fixed faster."),
    }


def hints():
    """Where the missing ponies hide, in words that never give the word away: {pony: hint}."""
    return {
        "pony_explorer": _("A pony explores Bashou's source code. Clone the repository and look around its "
                           "doc folder."),
        "pony_package": _("A pony hides in Bashou's package description. Ask your package manager to search "
                          "for Bashou."),
        "pony_web": _("A pony hides on Bashou's home page, but not where the browser shows it. Look at the "
                      "page's source."),
        "pony_wrecking": _("A pony hides where each new version of Bashou says what changed. Read it to the "
                           "very end, where things break."),
        "pony_detective": _("A pony solved a case on Bashou's GitHub. Search the issues, and don't forget the "
                            "closed ones."),
        "pony_form": _("A pony waits where you report a bug. Open Bashou's bug report form on GitHub and read it "
                       "to the very last box."),
        "jokes": _("Some ponies love old terminal jokes: a talking cow, a mooing package manager, a manual "
                   "nobody wrote, a sandwich, vim… Try a few."),
    }


def herd():
    """The ponies, in board order."""
    return [pet for pet in creatures.NAMES if creatures.FAMILIES[pet].herd == "pony"]


def joke(s, line):
    """A terminal joke that brings a pony you don't have yet: it joins the save now. Returns what the pet
    says (the arrival first), or []."""
    for pony, pattern in JOKES:
        if pony not in s["ponies"] and pattern.search(line):
            s["ponies"].append(pony)
            return ["🐴 " + arrivals()[pony]] + progress.check(s)
    return []


def hint(s):
    """The next hiding place to look for, or None when the whole herd is here."""
    for pony, text in hints().items():
        if pony in s["ponies"] or (pony == "jokes" and all(p in s["ponies"] for p, _rx in JOKES)):
            continue
        return text
    return None


def show(pony):
    """The pony, then where it was found."""
    pet = creatures.get(creatures.FAMILIES[pony].first)
    cells = [[True] * pet.width for _ in range(len(pet.base) // 2)]
    print()
    for line in render.lines(pet, [], cells):
        print("  " + line.replace(render.SKIP, " "))
    print(f"\n  {BOLD}{_(creatures.NAMES[pony])}{RESET} {DIM}{_(creatures.FAMILIES[pony].voice)}{RESET}")
    for line in render.wrap(where()[pony], max(30, min(render.columns(), 80) - 3), 8):
        print("  " + line)


def main(word=None):
    pony = FOAL if not word else PONIES.get(digest(word))
    if not pony:
        print("  " + _("No pony answers to that name."))
        return 1
    with state.locked() as s:
        new = pony not in s["ponies"]
        notes = []
        if new:
            s["ponies"].append(pony)
            notes = progress.check(s)
        mine, next_hint = sum(p in s["ponies"] for p in herd()), hint(s)
    show(pony)
    print()
    for note in notes:
        print("  " + note)
    if not new:
        print("  " + _("{name} is already in your herd.").format(name=_(creatures.NAMES[pony])))
    print(f"  {DIM}" + _("Ponies found: {n}/{total}.").format(n=mine, total=len(herd())) + RESET)
    if next_hint:
        for line in render.wrap("🐴 " + next_hint, max(30, min(render.columns(), 80) - 3), 4):
            print(f"  {DIM}{line}{RESET}")
    return 0
