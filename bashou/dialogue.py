"""What pets say: hints toward the next achievement, tips for their tool, and personality.

Personality = the pet's own voice + traits from the achievements you earned
(win a fight and your pets get bolder, run commands at 3 am and they get nocturnal…).
"""

import difflib
import random

from . import achievements, creatures, fight, lesson, safety, which
from .adventure import lessons
from .analyze import analyze
from .i18n import _

# Trait (an achievement you earned) -> lines any pet may say.
TRAITS = {
    "warrior": ["Any threats around? I'm ready.", "I sharpened my claws. `bashou fight`?"],
    "veteran": ["Ten fights won. The threats fear us now."],
    "legend": ["Legends don't wait for threats. They hunt them."],
    "night_owl": ["Late again? I like the quiet.", "The prompt glows nicer at night."],
    "explorer": ["So many tools already. What's next, `man -k`?"],
    "streak7": ["Another day together. Keep the streak!"],
    "sprinter": ["So many commands today. Coffee break?"],
    "plumber": ["Pipes are the best toys."],
    "tally": ["I like things counted and sorted."],
}



def next_step(state, pet):
    """The achievement a pet points you at: in its family, the first one left whose chain has come to
    it (the one before it is earned), the least deep first. It stays the same until you earn it, then
    the chain moves on. Once the family is done, the same among every pet's."""
    earned = set(state["achievements"])

    def ready(a):
        prev = achievements.PREV.get(a.id)
        return a.id not in earned and not a.state and not a.hidden and (prev is None or prev.id in earned
                                                                          or not prev.available())
    todo = [a for a in achievements.family(pet) if ready(a)] or [a for a in achievements.usable() if ready(a)]
    return min(todo, key=lambda a: a.depth, default=None)


def hint(state, pet, rng=None):
    """What to try next, with an example (see next_step)."""
    a = next_step(state, pet)
    if a is None:
        return None
    example = a.example
    if example:
        return _("Try `{example}` (achv: {name})").format(example=example.replace(chr(10), " ⏎ "), name=_(a.name))
    return _("Next: {how} (achv: {name})").format(how=_(a.how), name=_(a.name))


INVITES = {
    "adventure": ["Let's go on an adventure! `bashou adventure` (s to save & quit)",
                  "I want to see the world. Take me with you: `bashou adventure`",
                  "Grass, hills, dungeons… `bashou adventure` is waiting for us."],
    "security": ["Feel like a detective? `bashou arena security` has small investigations."],
    "lesson": ["The Sage Owl has a new lesson for you, with drawings: `bashou lesson`",
               "A new page opened in the owl's library. It shows how things work inside: `bashou lesson`"],
    "rust": ["You know your way around now. Want to learn Rust? `{cmd}` installs it, and Rust fights will come.",
             "Rust next? The compiler explains every mistake. Install it with `{cmd}`, then `bashou lesson`."],
    "gpg": ["Your files deserve a lock. `{cmd}` installs GnuPG, then `gpg -c notes.txt` locks a file.",
            "Downloads can be faked. GnuPG checks who signed them. Install it: `{cmd}`"],
    "pass": ["Passwords in scripts? Never in clear. `{cmd}` installs pass: scripts read `$(pass show db)`.",
             "pass keeps each password in its own file, encrypted with gpg. Install it: `{cmd}`"],
    "sqlite3": ["Want to learn SQL? `{cmd}` installs SQLite: a whole database in one file. SQL fights will come."],
}
RUST_AT = 15                    # achievements before the pets suggest Rust (owner)
SECRETS_AT = 5                  # … and gpg, then pass, when they're missing (owner: entice to install them)

# Packages that bring a tool: (Debian/Ubuntu, Red Hat family).
PACKAGES = {"rustc": ("rustc cargo", "rust cargo"), "gpg": ("gnupg", "gnupg2"), "pass": ("pass", "pass"),
            "sqlite3": ("sqlite3", "sqlite")}


# A first look at a tool, before its fight can come (see fight.to_discover).
DISCOVER = {
    "awk": ["Meet awk: `awk '{print $1}' file` prints the first word of each line.",
            "awk splits lines into columns: $1, $2… `awk -F, '{print $2}' data.csv` for CSV."],
    "uniq": ["`sort file | uniq -c` counts how many times each line appears."],
    "sed": ["sed replaces text: `sed 's/old/new/g' file` (add -i to edit the file)."],
    "|": ["Pipes chain commands: `ls | wc -l` counts the files here."],
    "find": ["`find . -name '*.log'` looks for files in every folder below."],
    "ps": ["`ps aux` lists every running process with its PID."],
    "python3": ["`python3 -c \"print(2 ** 10)\"` runs one line of Python, right from bash.",
                "Python reads JSON too: `python3 -m json.tool data.json` prints it neatly."],
    "gcc": ["`gcc hello.c -o hello && ./hello` builds a C program and runs it."],
    "gdb": ["A crash? `gcc -g prog.c -o prog && gdb -q ./prog`, then run and bt: gdb shows the line that died.",
            "gdb pauses a program wherever you want: `break main`, `run`, `next`, `print x`. `bashou lesson` "
            "has a lesson on it."],
    "rustc": ["`rustc main.rs && ./main` builds a Rust program. rustc's errors say what to change."],
    "gpg": ["`gpg -c notes.txt` locks a file with a passphrase; `gpg -d notes.txt.gpg` opens it again."],
    "pass": ["`pass show web/forum` prints a password from your store, so scripts never have to hold one."],
    "sqlite3": ["`sqlite3 shop.db .tables` lists the tables of a database: SQLite keeps it all in one file."],
}


def discover(state, rng):
    tools = [t for t in fight.to_discover(state) if t in DISCOVER]
    if not tools:
        return None
    tool = rng.choice(tools)
    taught = any(le["tool"] == tool for le in lessons.LESSONS)
    return _(rng.choice(DISCOVER[tool])) + (" " + _("(bashou adventure teaches it too)") if taught else "")


def install(tool):
    """How to install a tool here, with this system's package manager."""
    debian, redhat = PACKAGES[tool]
    if which.system() == "debian":
        return f"sudo apt install {debian}"
    if tool == "pass" and "rhel" in which.os_family():
        return "sudo dnf install epel-release && sudo dnf install pass"     # pass lives in EPEL on RHEL, Rocky, Alma
    if which.system() == "rocky":
        return f"sudo dnf install {redhat}"
    if tool == "rustc":
        return "curl -sSf https://sh.rustup.rs -o rustup.sh && less rustup.sh && sh rustup.sh"
    return _("your package manager (package {name})").format(name=debian)


def rust_install():
    return install("rustc")


def wanted(state, skill):
    return state.get("skills", "all") == "all" or skill in state["skills"]


def invite(state, rng):
    """Suggest a mode you haven't tried yet (None once you tried them all), or Rust once you're at ease."""
    todo = [mode for mode, tried in (("adventure", state.get("adventure")), ("security", state.get("security")))
            if not tried]
    rust_ok = state.get("skills", "all") == "all" and len(state["achievements"]) >= RUST_AT or \
        state.get("skills", "all") != "all" and "rust" in state["skills"]
    if rust_ok and not which.installed("rustc"):
        todo.append("rust")
    if len(state["achievements"]) >= SECRETS_AT:          # at ease with the shell first
        if wanted(state, "linux"):
            todo += [tool for tool in ("gpg", "pass") if not which.installed(tool)][:1]     # gpg first: pass needs it
        if wanted(state, "sql") and not which.installed("sqlite3"):
            todo.append("sqlite3")
    if not todo:
        return None
    mode = rng.choice(todo)
    if mode == "rust":
        return _(rng.choice(INVITES["rust"])).format(cmd=rust_install())
    if mode in PACKAGES:
        return _(rng.choice(INVITES[mode])).format(cmd=install(mode))
    return rng.choice(INVITES[mode])


def new_lesson(state, rng):
    """A lesson you unlocked and haven't opened yet: the Sage Owl's library is waiting."""
    return rng.choice(INVITES["lesson"]) if lesson.new(state) else None


def line(state, pet, rng=random):
    """One thing for `pet` to say, with its voice. A waiting threat comes first."""
    threat = fight.announcement(state)
    if threat:
        return f"{_(creatures.FAMILIES[pet].voice)} {threat}"
    earned = set(state["achievements"])
    traits = [t for trait, lines in TRAITS.items() if trait in earned for t in lines]
    pools = [(hint(state, pet, rng), 4), (rng.choice(creatures.FAMILIES[pet].tips), 4),
             (rng.choice(traits + creatures.FAMILIES[pet].personal), 2), (invite(state, rng), 3), (discover(state, rng), 4),
             (new_lesson(state, rng), 3)]
    pools = [(text, w) for text, w in pools if text]
    text = rng.choices([t for t, w in pools], [w for t, w in pools])[0]
    return f"{_(creatures.FAMILIES[pet].voice)} {_(text)}"


COMMON = ("ls cd cat grep find awk sed sort uniq head tail less more echo printf pwd mkdir rmdir rm cp mv "
          "touch chmod chown ln ps kill top htop df du free tar gzip zip unzip curl wget ssh scp git make "
          "python3 pip vim nano man which whereis history clear exit sudo apt xargs jq tr cut wc tee diff "
          "strace watch time date cal file stat env export source alias type").split()

TYPO_FIX = ["Hehe, `{typo}`? I think you meant `{fix}`.", "`{typo}`… so close! `{fix}`?",
            "Fat paws again? `{typo}` → `{fix}`", "I won't tell anyone about `{typo}`. Try `{fix}`.",
            "*giggles* `{fix}` has fewer typos than `{typo}`."]
TYPO_NONE = ["`{typo}`? Never heard of it. Hehe.", "`{typo}` isn't a command… yet.",
             "*tilts head* `{typo}`?"]


def risky(pet, command, rng=random):
    """A warning in the pet's voice when a command is risky (`curl … | sh`, `chmod 777`…), else None."""
    parts = safety.warning(command, rng)
    if not parts:
        return None
    return f"{_(creatures.FAMILIES[pet].voice)} ⚠ " + " ".join(_(p) for p in parts)


def typo(state, pet, command, rng=random):
    """A kind laugh at a "command not found", with the closest real command if there is one."""
    names = [name for name, args in analyze(command).commands]
    unknown = [n for n in names if not which.installed(n) and n not in COMMON]
    if not unknown:
        return None
    word = unknown[0]
    candidates = sorted(set(COMMON) | set(state["tools"]))
    # Swapped letters first (`sl` → `ls`): too short for difflib to score well.
    close = [c for c in candidates if len(c) == len(word) and sorted(c) == sorted(word)][:1]
    close = close or difflib.get_close_matches(word, candidates, n=1, cutoff=0.6)
    template = rng.choice(TYPO_FIX if close else TYPO_NONE)
    return f"{_(creatures.FAMILIES[pet].voice)} " + _(template).format(typo=word[:20], fix=close[0] if close else "")
