"""What pets say: hints toward the next achievement, tips for their tool, and personality.

Personality = the pet's own voice + traits from the achievements you earned
(win a fight and your pets get bolder, run commands at 3 am and they get nocturnal…).
"""

import difflib
import random
import shutil

from . import achievements, creatures, safety
from .analyze import analyze
from .i18n import _

# Achievement -> an example that earns it.
EXAMPLES = {
    "historian": "history | tail", "loop": "for f in *; do echo $f; done",
    "reader": "while read -r l; do echo $l; done < file", "ranges": "for i in {1..3}; do echo $i; done",
    "capture": "echo \"today: $(date +%A)\"", "nested": "echo $(basename $(pwd))",
    "substitute": "diff <(ls /bin) <(ls /usr/bin)", "here": "cat <<EOF > note.txt\nhello\nEOF",
    "tally": "sort file | uniq -c", "ranking": "du -s * | sort -rn", "unique": "sort -u file",
    "plumber": "ps aux | grep bash | wc -l", "pipeline": "cat f | tr A-Z a-z | sort | uniq -c | sort -rn",
    "tee_time": "ls | tee list.txt", "merge": "make 2>&1 | less",
    "time_traveller": "find . -mtime -1", "executor": "find . -name '*.tmp' -exec rm {} +",
    "pruner": "find . -name .git -prune -o -type f -print",
    "field_reader": "awk -F: '{print $1}' /etc/passwd", "accountant": "awk '{s+=$1} END {print s}' f",
    "scribe": "awk '{printf \"%-10s %s\\n\", $1, $2}' f",
    "digger": "grep -rn TODO .", "regex": "grep -E 'cat|dog' f", "context": "grep -C2 error log",
    "builder": "mkdir -p camp/tent/bed", "copycat": "cp -r notes notes.bak", "shortcut": "ln -s ~/projects p",
    "inspector": "less install.sh", "checksum": "sha256sum install.sh",
    "save_first": "curl -fsSLo install.sh https://example.com/install.sh", "tight": "chmod u+x install.sh",
    "in_place": "sed -i 's/old/new/' f", "global": "sed 's/a/b/g' f", "printer": "sed -n '1,5p' f",
    "census": "ps aux", "seeker": "pgrep -a bash", "signal": "kill -TERM <pid>",
    "filter": "strace -e trace=openat ls", "follow": "strace -f bash -c ls", "summary": "strace -c ls",
    "placeholder": "ls | xargs -I{} echo {}", "parallel": "ls | xargs -P4 -n1 echo",
    "null": "find . -print0 | xargs -0 ls", "raw": "jq -r '.name' f.json",
    "selector": "jq '.[] | select(.ok)' f.json", "mapper": "jq 'map(.id)' f.json",
    "warrior": "bashou fight",
    "brancher": "git switch -c try-it", "stasher": "git stash", "grapher": "git log --oneline --graph",
    "bisector": "git bisect start", "packer": "tar -czf notes.tgz notes", "peeker": "tar -tf notes.tgz",
    "unpacker": "tar -xf notes.tgz -C /tmp", "squeezer": "xz -k big.log",
    "headers": "curl -I https://example.com", "poster": "curl -d 'a=1' https://httpbin.org/post",
    "tunneler": "ssh -L 8080:localhost:80 server", "mirror": "rsync -av notes/ backup/",
    "resolver": "dig +short example.com", "tracer": "dig +trace example.com",
    "interfaces": "ip -br addr", "six_sense": "ip -6 addr", "pathfinder": "ip route get 1.1.1.1",
    "listener": "ss -tlnp", "established": "ss -tn state established", "nsswitch": "getent hosts example.org",
    "reverse": "dig -x 1.1.1.1", "stub": "resolvectl status", "hops": "tracepath -n 1.1.1.1",
    "knocker": "nc -zv localhost 22", "capture_reader": "tcpdump -nn -r capture.pcap",
    "octal": "chmod 644 notes.txt", "symbolic": "chmod g+w notes.txt", "owner": "sudo chown $USER:$USER f",
    "mode_reader": "stat -c %a notes.txt", "status": "systemctl status cron", "logbook": "journalctl -u cron",
    "enabler": "sudo systemctl enable --now cron", "reload": "sudo systemctl daemon-reload",
    "pods": "kubectl get pods -A", "describer": "kubectl describe pod <name>", "tailer": "kubectl logs -f <pod>",
    "diver": "kubectl exec -it <pod> -- sh", "disk": "df -h", "sizer": "du -sh *", "memory": "free -h",
    "watcher": "watch -n 2 df -h",
    "quack": "bashou learn", "xray": "bash -x deploy.sh", "dry_run": "bash -n deploy.sh", "exit_code": "ls /nope; echo $?",
    "linter": "shellcheck deploy.sh",
    "sealed": "gpg -c notes.txt", "keymaker": "gpg --full-generate-key", "vault": "pass init <your key id>",
    "generator": "pass generate web/forum 24", "keeper": "curl -u \"admin:$(pass show web/admin)\" https://example.org",
}

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



def hint(state, pet, rng):
    """Next achievement of this pet's family, or any one left (the easiest first), with an example."""
    earned = set(state["achievements"])
    todo = [a for a in achievements.family(pet) if a.id not in earned and not a.state and not a.hidden]
    todo = todo or [a for a in achievements.usable() if a.id not in earned and not a.state]
    if not todo:
        return None
    easiest = min(a.level for a in todo)
    a = rng.choice([a for a in todo if a.level == easiest])
    example = EXAMPLES.get(a.id)
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
    from . import fight
    tools = [t for t in fight.to_discover(state) if t in DISCOVER]
    if not tools:
        return None
    from .adventure import lessons
    tool = rng.choice(tools)
    taught = any(le["tool"] == tool for le in lessons.LESSONS)
    return _(rng.choice(DISCOVER[tool])) + (" " + _("(bashou adventure teaches it too)") if taught else "")


def install(tool):
    """How to install a tool here, with this system's package manager."""
    from .challenges import family
    debian, redhat = PACKAGES[tool]
    if "debian" in family():
        return f"sudo apt install {debian}"
    if tool == "pass" and "rhel" in family():
        return "sudo dnf install epel-release && sudo dnf install pass"     # pass lives in EPEL on RHEL, Rocky, Alma
    if family() & {"rhel", "fedora", "centos"}:
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
    if rust_ok and not shutil.which("rustc"):
        todo.append("rust")
    if len(state["achievements"]) >= SECRETS_AT:          # at ease with the shell first
        if wanted(state, "linux"):
            todo += [tool for tool in ("gpg", "pass") if not shutil.which(tool)][:1]     # gpg first: pass needs it
        if wanted(state, "sql") and not shutil.which("sqlite3"):
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
    from . import lesson
    return rng.choice(INVITES["lesson"]) if lesson.new(state) else None


def line(state, pet, rng=random):
    """One thing for `pet` to say, with its voice. A waiting threat comes first."""
    from . import fight
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
    unknown = [n for n in names if not shutil.which(n) and n not in COMMON]
    if not unknown:
        return None
    word = unknown[0]
    candidates = sorted(set(COMMON) | set(state["tools"]))
    # Swapped letters first (`sl` → `ls`): too short for difflib to score well.
    close = [c for c in candidates if len(c) == len(word) and sorted(c) == sorted(word)][:1]
    close = close or difflib.get_close_matches(word, candidates, n=1, cutoff=0.6)
    template = rng.choice(TYPO_FIX if close else TYPO_NONE)
    return f"{_(creatures.FAMILIES[pet].voice)} " + _(template).format(typo=word[:20], fix=close[0] if close else "")
