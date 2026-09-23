"""What pets say: hints toward the next achievement, tips for their tool, and personality.

Personality = the pet's own voice + traits from the achievements you earned
(win a fight and your pets get bolder, run commands at 3 am and they get nocturnal…).
"""

import difflib
import random
import shutil

from . import achievements, safety
from .analyze import analyze
from .i18n import _

VOICE = {
    "star": "*twinkle*", "sprout": "*rustle*", "pebble": "*clack*", "bat": "*flap*", "gremlin": "Hehehe.", "snail": "*slow bow*", "frog": "Ribbit.", "turtle": "…", "mushroom": "*puff*", "slime": "Blub.",
    "sofa": "*creak*", "octopus": "Glub!", "dragon": "Rawr!", "fox": "*sniff*", "owl": "Hoo.",
    "mole": "*dig dig*", "snake": "Sss…", "ghost": "Boo~", "spider": "*tik-tik*", "ant": "*click*",
    "axolotl": "*wiggle*", "beaver": "*chomp*", "squirrel": "*chitter*", "pigeon": "Coo.", "hedgehog": "*huff*",
    "bee": "Bzz.", "whale": "*whoosh*", "meerkat": "*peek*", "cat": "*purr*",
}

TIPS = {
    "star": ["Ctrl+R searches your history as you type.", "`cd -` jumps back to the previous folder.",
            "`sudo !!` reruns the last command with sudo.", "Ctrl+A / Ctrl+E: start / end of the line.",
            "Ctrl+W deletes the word before the cursor."],
    "sprout": ["Start scripts with `#!/usr/bin/env bash`.", "`set -euo pipefail` stops a script on errors.",
               "`chmod +x script.sh` makes it runnable.", "Functions: greet() { echo \"hi $1\"; }",
               "`bash -x script.sh` shows each line as it runs."],
    "pebble": ["`ls -lah` shows hidden files with human sizes.", "`du -sh *` : how big is each folder?",
               "`df -h` : how full are your disks?", "`ln -s target link` makes a shortcut.",
               "`chmod 644 file` : rw for you, read for others."],
    "snail": ["`mkdir -p a/b/c` builds a whole path at once.", "`cp -r src dst` copies a folder and its content.",
              "`ln -s target name` makes a shortcut.", "`mv old new` renames; `mv file dir/` moves.",
              "Onward! `bashou adventure` has more roads to walk."],
    "gremlin": ["Before running a script from the web: download, read, then run.",
                "`sha256sum file` shows a checksum: compare it with the one on the website.",
                "`chmod u+x script.sh` is enough to run it. No need for 777.",
                "`ls -l` shows who can read, write and run each file.",
                "Want to play detective? `bashou security` has small investigations."],
    "bat": ["`ctrl+L` clears the screen, like `clear`.", "`tail -f log` watches a file live.",
            "`nohup cmd &` keeps it running after you leave.", "`man -k word` searches every manual."],
    "frog": ["`!$` is the last argument of the previous command.", "`fc` opens the last command in your editor.",
             "`history | grep ssh` finds that command from last week.", "Press Ctrl+R again for older matches."],
    "turtle": ["`watch -n 5 df -h` reruns a command every 5 s.", "`time make` tells how long it took.",
               "`sleep 600 && echo done` waits 10 minutes.", "`crontab -e` runs things on a schedule."],
    "mushroom": ['for f in *.log; do gzip "$f"; done', 'while read -r l; do echo "$l"; done < file',
                 "for i in {1..5}; do echo $i; done", "until ping -c1 host; do sleep 1; done",
                 "`seq 0 5 20` counts by fives: 0 5 10 15 20."],
    "slime": ["today=$(date +%F) stores a command's output.", "diff <(ls a) <(ls b) compares two outputs.",
              "cat <<EOF > file writes several lines at once.", "echo $(( 6 * 7 )) does math in bash."],
    "sofa": ["sort | uniq -c | sort -rn makes a top list.", "`sort -u` sorts and dedupes in one go.",
             "sort -t, -k3 -n sorts a CSV by its 3rd column.", "`uniq -d` shows only the duplicates."],
    "octopus": ["cmd 2>&1 | less pages the errors too.", "cmd | tee out.txt shows AND saves.",
                "`set -o pipefail`: a pipe fails if any part fails.", "cmd |& grep x also pipes stderr."],
    "dragon": ["When a threat shows up, `bashou fight` opens the arena.", "Stuck in the arena? Type `hint`.",
               "A threat you ignore comes back later."],
    "fox": ["find . -name '*.log' -mtime +7 : week-old logs.", "find . -type f -size +100M : big files.",
            "find . -name '*.tmp' -delete cleans up.", "find . -newer ref.txt : changed since ref.txt."],
    "owl": ["awk '{print $1}' prints the first column.", "awk -F: '{print $1}' /etc/passwd lists users.",
            "awk 'NR==5' prints line 5.", "awk 'length > 80' finds long lines."],
    "mole": ["grep -rn TODO . shows file and line number.", "grep -v '^#' drops comment lines.",
             "grep -l pattern *.txt lists matching files.", "grep -i ignores case."],
    "snake": ["sed -n '10,20p' prints lines 10 to 20.", "sed -i.bak 's/a/b/g' f keeps a backup.",
              "sed '/^$/d' removes empty lines.", "sed 's/[[:space:]]*$//' trims trailing spaces."],
    "ghost": ["ps aux --sort=-%mem | head : memory hogs.", "pgrep -a python lists python processes.",
              "kill -TERM first; -KILL only as a last resort.", "Ctrl+Z then `bg`: resume a job in background."],
    "spider": ["strace -e trace=openat ls : files it opens.", "strace -c cmd : a syscall summary.",
               "strace -p PID attaches to a running process.", "strace -f follows child processes."],
    "ant": ["find . -name '*.bak' | xargs rm", "find . -print0 | xargs -0 : safe with spaces.",
            "xargs -P4 runs 4 jobs in parallel.", "ls *.txt | xargs -I{} cp {} {}.bak"],
    "axolotl": ["`jq .` pretty-prints JSON.", "jq -r '.[].name' : raw names, no quotes.",
                "jq 'map(select(.age > 30))' filters a list.", "curl -s url | jq '.items[0]'"],
    "beaver": ["`git add -p` picks changes piece by piece.", "`git commit --amend` fixes the last commit.",
               "`git diff --staged` shows what you're about to commit.", "`git restore file` drops your changes."],
    "squirrel": ["tar -czf backup.tgz dir/ packs a folder.", "tar -tf a.tgz lists it without unpacking.",
                 "tar -xf a.tgz -C /tmp unpacks somewhere else.", "`gzip -k file` keeps the original."],
    "pigeon": ["curl -I url : just the headers.", "curl -sS url : quiet, but still shows errors.",
               "rsync -av src/ dst/ : copies only what changed.", "ssh -L 8080:localhost:80 host : a tunnel."],
    "hedgehog": ["chmod 644 : rw for you, read for others.", "chmod 755 : scripts and folders everyone can enter.",
                 "`ls -l` : the 10 letters are the rights.", "`umask` : the rights new files get."],
    "bee": ["systemctl status nginx : is it running?", "journalctl -u nginx -f : its logs, live.",
            "systemctl list-units --failed : what broke.", "Edited a unit file? `systemctl daemon-reload`."],
    "whale": ["kubectl get pods -A : every pod everywhere.", "kubectl describe pod x : the Events explain why.",
              "kubectl logs -f pod : logs, live.", "kubectl config get-contexts : which cluster am I on?"],
    "meerkat": ["df -h : how full are the disks?", "du -sh * | sort -h : biggest last.",
                "free -h : memory at a glance.", "watch -n 2 cmd : rerun it every 2 s."],
    "cat": ["Only test what you're allowed to test. Written permission, always.",
            "Read the man page before the exploit.", "Keep your notes: half of security is notes.",
            "`nmap -sV host` tells you what's listening, and what version.",
            "A lab at home beats someone else's server."],
}

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
    "octal": "chmod 644 notes.txt", "symbolic": "chmod g+w notes.txt", "owner": "sudo chown $USER:$USER f",
    "mode_reader": "stat -c %a notes.txt", "status": "systemctl status cron", "logbook": "journalctl -u cron",
    "enabler": "sudo systemctl enable --now cron", "reload": "sudo systemctl daemon-reload",
    "pods": "kubectl get pods -A", "describer": "kubectl describe pod <name>", "tailer": "kubectl logs -f <pod>",
    "diver": "kubectl exec -it <pod> -- sh", "disk": "df -h", "sizer": "du -sh *", "memory": "free -h",
    "watcher": "watch -n 2 df -h",
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

PERSONAL = {
    "star": ["I'm made of stardust. And a bit of bash."], "sprout": ["Water me with commands."],
    "pebble": ["I'm a rock. You can count on me."], "bat": ["I like the terminal after dark."],
    "gremlin": ["Run it! What could go wrong? …Just kidding. Read it first."],
    "snail": ["Slowly but surely, hero.", "Every checkpoint is a small victory."], "frog": ["Hop hop. What's next?"],
    "turtle": ["Slow and steady. No rush."], "mushroom": ["Loops make me grow."],
    "slime": ["I can take the shape of any output."], "sofa": ["Sit down. Relax. Run a command."],
    "octopus": ["Eight arms, eight pipes."], "dragon": ["I guard your shell."],
    "fox": ["I can find anything. Anything."], "owl": ["Every line has fields, if you look closely."],
    "mole": ["I dig through text all day."], "snake": ["I rewrite what I touch."],
    "ghost": ["I see every process…"], "spider": ["I hear every syscall on my web."],
    "ant": ["Many small jobs make one big job."], "axolotl": ["JSON is my favourite pond."],
    "beaver": ["Commit often. A dam is built stick by stick."], "squirrel": ["I pack everything for winter."],
    "pigeon": ["I always find my way home. Even through a tunnel."], "hedgehog": ["Not everyone gets to touch my files."],
    "bee": ["Every service in the hive has its job."], "whale": ["So many containers on my back."],
    "meerkat": ["I keep watch. Disks, memory, all of it."],
    "cat": ["I saw what you ran. Your secret is safe with me.", "Curiosity, with permission.",
            "Nice tools. Mind the scope."],
}


def hint(state, pet, rng):
    """Next achievement of this pet's family, or any one left (the easiest first), with an example."""
    earned = set(state["achievements"])
    todo = [a for a in achievements.family(pet) if a.id not in earned and not a.state and not a.hidden]
    todo = todo or [a for a in achievements.usable() if a.id not in earned and not a.state]
    if not todo:
        return None
    easiest = min(map(achievements.difficulty, todo))
    a = rng.choice([a for a in todo if achievements.difficulty(a) == easiest])
    example = EXAMPLES.get(a.id)
    if example:
        return _("Try `{example}` (achv: {name})").format(example=example.replace(chr(10), " ⏎ "), name=_(a.name))
    return _("Next: {how} (achv: {name})").format(how=_(a.how), name=_(a.name))


INVITES = {
    "adventure": ["Let's go on an adventure! `bashou adventure` (s to save & quit)",
                  "I want to see the world. Take me with you: `bashou adventure`",
                  "Grass, hills, dungeons… `bashou adventure` is waiting for us."],
    "security": ["Feel like a detective? `bashou security` has small investigations."],
    "rust": ["You know your way around now. Want to learn Rust? `{cmd}` installs it, and Rust fights will come.",
             "Rust next? The compiler explains every mistake. Install it with `{cmd}`, then `bashou explain rust mut`."],
}
RUST_AT = 15                    # achievements before the pets suggest Rust (owner)


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
    "rustc": ["`rustc main.rs && ./main` builds a Rust program. rustc's errors say what to change."],
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


def rust_install():
    """How to install Rust here: the distro's packages, or rustup (read the script before running it)."""
    from .challenges import family
    if "debian" in family():
        return "sudo apt install rustc cargo"
    if family() & {"rhel", "fedora", "centos"}:
        return "sudo dnf install rust cargo"
    return "curl -sSf https://sh.rustup.rs -o rustup.sh && less rustup.sh && sh rustup.sh"


def invite(state, rng):
    """Suggest a mode you haven't tried yet (None once you tried them all), or Rust once you're at ease."""
    todo = [mode for mode, tried in (("adventure", state.get("adventure")), ("security", state.get("security")))
            if not tried]
    if len(state["achievements"]) >= RUST_AT and not shutil.which("rustc"):
        todo.append("rust")
    if not todo:
        return None
    mode = rng.choice(todo)
    if mode == "rust":
        return _(rng.choice(INVITES["rust"])).format(cmd=rust_install())
    return rng.choice(INVITES[mode])


def line(state, pet, rng=random):
    """One thing for `pet` to say, with its voice. A waiting threat comes first."""
    from . import fight
    threat = fight.announcement(state)
    if threat:
        return f"{_(VOICE[pet])} {threat}"
    earned = set(state["achievements"])
    traits = [t for trait, lines in TRAITS.items() if trait in earned for t in lines]
    pools = [(hint(state, pet, rng), 4), (rng.choice(TIPS[pet]), 4),
             (rng.choice(traits + PERSONAL[pet]), 2), (invite(state, rng), 3), (discover(state, rng), 4)]
    pools = [(text, w) for text, w in pools if text]
    text = rng.choices([t for t, w in pools], [w for t, w in pools])[0]
    return f"{_(VOICE[pet])} {_(text)}"


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
    return f"{_(VOICE[pet])} ⚠ " + " ".join(_(p) for p in parts)


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
    return f"{_(VOICE[pet])} " + _(template).format(typo=word[:20], fix=close[0] if close else "")
