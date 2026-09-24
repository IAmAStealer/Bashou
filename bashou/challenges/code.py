"""Code fights (owner, 2026-09-23): fix a small Python or C file, or answer with a python3 one-liner.

Fix fights: the file starts with a comment saying what goes in, what should come out, how to run it
and which `bashou explain` note helps. Bashou then runs hidden tests on your version: Python through a
small harness, C built with AddressSanitizer when the compiler has it (leaks and overflows count).
The first level only asks to fix what stops the code from compiling.
"""

import base64
import functools
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import Challenge
from ..i18n import _

PYTHON = ("python3", "python")
COMPILERS = ("gcc", "cc", "clang", "make")
NAMES = ("ada", "bo", "casey", "dara", "eli", "fern", "gil", "hana", "ines", "joss", "kim", "lior",
         "mira", "nils", "omar", "pia", "quinn", "remy", "sana", "tao")
HOSTS = ("web1", "web2", "db1", "db2", "cache", "mail", "proxy", "backup", "auth", "queue")


def header(style, lines):
    lines = lines + [_("When it works, type: verify")]
    if style == "#":
        return "\n".join("# " + line for line in lines) + "\n"
    return "/*\n" + "".join(" * " + line + "\n" for line in lines) + " */\n"


def write(work, name, style, lines, code):
    (work / name).write_text(header(style, lines) + code)


# --- running your code --------------------------------------------------------

HARNESS = r"""
import copy, importlib.util, json, sys
path, func = sys.argv[1], sys.argv[2]
cases = json.load(sys.stdin)
spec = importlib.util.spec_from_file_location("fixed", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
for args, want in cases:
    given = copy.deepcopy(args)
    got = getattr(mod, func)(*given)
    if json.loads(json.dumps(got)) != want or given != args:
        sys.exit(1)
print("ok")
"""


def run(cmd, cwd, stdin="", timeout=10, env=None):
    try:
        return subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True, text=True, timeout=timeout,
                              env=env)
    except (subprocess.TimeoutExpired, OSError):
        return None


def py_tests(name, func):
    """verify(): call `func` from your file on the cases in meta["cases"] ([args, expected])."""
    def verify(work, meta, value):
        r = run([sys.executable, "-c", HARNESS, str(work / name), func], work, json.dumps(meta["cases"]), 5)
        return bool(r) and r.returncode == 0 and r.stdout.strip() == "ok"
    return verify


def py_output(name):
    """verify(): run your script, compare what it prints with meta["expected"]."""
    def verify(work, meta, value):
        r = run([sys.executable, name], work, timeout=5)
        return bool(r) and r.returncode == 0 and r.stdout == meta["expected"]
    return verify


@functools.lru_cache(maxsize=None)
def sanitizer():
    """The -fsanitize flags this gcc can build and run, or [] (no AddressSanitizer here)."""
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "t.c").write_text("int main(void) { return 0; }\n")
        flags = ["-fsanitize=address,undefined"]
        r = run(["gcc", *flags, "t.c", "-o", "t"], tmp)
        ok = r and r.returncode == 0 and run(["./t"], tmp)
        return flags if ok and ok.returncode == 0 else []


def c_tests(name):
    """verify(): build your file, run it on meta["runs"] ([args, stdin, expected stdout])."""
    def verify(work, meta, value):
        with tempfile.TemporaryDirectory() as tmp:
            built = run(["gcc", "-g", *sanitizer(), str(work / name), "-o", "prog"], tmp)
            if not built or built.returncode != 0:
                return False
            env = {**os.environ, "ASAN_OPTIONS": "detect_leaks=1", "UBSAN_OPTIONS": "halt_on_error=1"}
            for args, stdin, expected in meta["runs"]:
                r = run(["./prog", *args], tmp, stdin, env=env)
                if not r or r.returncode != 0 or r.stdout != expected:
                    return False
        return True
    return verify


PROGRAMS = {"hello", "shout", "average", "sum", "greet"}     # what the C fights build (./hello is "hello")


def c_used(analysis):
    """Building counts, and so does running your program."""
    return bool(analysis.tools & (set(COMPILERS) | PROGRAMS))


# --- level 1: make it compile -------------------------------------------------

def colon_setup(work, rng):
    names = rng.sample(NAMES, 3)
    write(work, "greet.py", "#", [
        _("Fight: this script doesn't even start. Python says why, with the line number."),
        _("Input: the names in the list below."),
        _("Wanted: one line per name, like: hello ada"),
        _("Run it:") + " python3 greet.py",
        _("Help:") + " bashou explain python loop",
    ], "\n\ndef greet(names)\n    for name in names:\n        print(\"hello\", name)\n\n\n"
       f"greet({names!r})\n")
    return {"expected": "".join(f"hello {n}\n" for n in names)}


def semicolon_setup(work, rng):
    name = rng.choice(NAMES)
    write(work, "hello.c", "c", [
        _("Fight: gcc refuses to build this. Read its first error: file:line: what is missing."),
        _("Input: nothing."),
        _("Wanted: it prints one line, like: hello, ada"),
        _("Run it:") + " gcc hello.c -o hello && ./hello",
        _("Help: gcc's message names the line; the fix goes at the end of the line before."),
    ], "\n#include <stdio.h>\n\nint main(void)\n{\n"
       f"    printf(\"hello, {name}\\n\")\n    return 0;\n}}\n")
    return {"runs": [[[], "", f"hello, {name}\n"]]}


# --- level 2: Python data and loops -------------------------------------------

LIST_CODE = '''

def unique(hosts):
    for i, host in enumerate(hosts):
        if host in hosts[:i]:
            hosts.remove(host)
    return hosts


if __name__ == "__main__":
    print(unique({demo!r}))
'''


def list_setup(work, rng):
    demo = [rng.choice(HOSTS[:4]) for _i in range(7)]
    write(work, "hosts.py", "#", [
        _("Fight: unique() should keep each host once, in the order they first appear."),
        _("Input: a list of host names, some repeated."),
        _("Wanted: a new list, each name once, first-seen order. Don't change the list you were given."),
        _("Run it:") + " python3 hosts.py",
        _("Help:") + " bashou explain python list",
    ], LIST_CODE.format(demo=demo))
    cases = []
    for _i in range(8):
        xs = [rng.choice(HOSTS) for _i in range(rng.randint(0, 12))]
        cases.append([[xs], list(dict.fromkeys(xs))])
    return {"cases": cases}


DICT_CODE = '''

def count_levels(lines):
    counts = {}
    for line in lines:
        level = line.split()[1]
        counts[level] += 1
    return counts


if __name__ == "__main__":
    with open("app.log") as fh:
        print(count_levels(fh))
'''

LEVELS = ("INFO", "WARN", "ERROR", "DEBUG")


def log_lines(rng, n):
    return [f"12:{rng.randint(0, 59):02d} {rng.choice(LEVELS)} {rng.choice(('login', 'retry', 'timeout', 'saved'))}"
            for _i in range(n)]


def dict_setup(work, rng):
    lines = log_lines(rng, rng.randint(20, 40))
    (work / "app.log").write_text("\n".join(lines) + "\n")
    write(work, "tally.py", "#", [
        _("Fight: count_levels() should count how many lines have each level."),
        _("Input: log lines like '12:04 ERROR timeout' (the level is the second word)."),
        _("Wanted: a dict like {'INFO': 12, 'ERROR': 3}."),
        _("Run it:") + " python3 tally.py",
        _("Help:") + " bashou explain python dict",
    ], DICT_CODE)
    cases = []
    for _i in range(6):
        ls = log_lines(rng, rng.randint(0, 15))
        want = {}
        for line in ls:
            want[line.split()[1]] = want.get(line.split()[1], 0) + 1
        cases.append([[ls], want])
    return {"cases": cases, "args": {"level": lines[0].split()[1]}}


LOOP_CODE = '''

def delays(tries):
    waits = []
    delay = 1
    i = 0
    while i < tries:
        waits.append(delay)
        delay = delay * 2
    return waits


if __name__ == "__main__":
    print(delays({n}))
'''


def loop_setup(work, rng):
    write(work, "retry.py", "#", [
        _("Fight: delays() should give the wait before each retry, doubling each time."),
        _("Input: how many tries, like 4."),
        _("Wanted: [1, 2, 4, 8] for 4 tries, [] for 0."),
        _("Run it:") + " python3 retry.py   (Ctrl+C stops it if it hangs)",
        _("Help:") + " bashou explain python loop",
    ], LOOP_CODE.format(n=rng.randint(3, 6)))
    return {"cases": [[[n], [2 ** i for i in range(n)]] for n in (0, 1, 4, rng.randint(5, 12))]}


TREE_CODE = '''

def total(tree):
    size = 0
    for name, item in tree.items():
        if isinstance(item, dict):
            total(item)
        else:
            size += item
    return size


if __name__ == "__main__":
    import json
    with open("tree.json") as fh:
        print(total(json.load(fh)))
'''


def tree(rng, depth):
    t = {}
    for i in range(rng.randint(1, 4)):
        if depth and rng.random() < 0.5:
            t[f"dir{i}"] = tree(rng, depth - 1)
        else:
            t[f"file{i}.txt"] = rng.randint(1, 900)
    return t


def size(t):
    return sum(size(v) if isinstance(v, dict) else v for v in t.values())


def tree_setup(work, rng):
    demo = {"notes.txt": rng.randint(10, 99), "photos": tree(rng, 2), "src": tree(rng, 2)}
    (work / "tree.json").write_text(json.dumps(demo, indent=2) + "\n")
    write(work, "du.py", "#", [
        _("Fight: total() should add up every file of a folder tree, subfolders included."),
        _("Input: folders are dicts, files are sizes: {'a.txt': 10, 'src': {'b.c': 5}}."),
        _("Wanted: the sum of every size, at every depth (15 above)."),
        _("Run it:") + " python3 du.py",
        _("Help:") + " bashou explain python recursion",
    ], TREE_CODE)
    cases = [[[t], size(t)] for t in (tree(rng, 3) for _i in range(6))]
    return {"cases": cases + [[[demo], size(demo)]]}


# --- level 2: python3 one-liners ----------------------------------------------

def json_setup(work, rng):
    ports = rng.sample(range(1024, 9999), 4)
    config = {"app": {"name": "shop", "port": ports[0]},
              "cache": {"host": "cache.internal", "port": ports[1]},
              "database": {"host": "db.internal", "port": ports[2], "user": rng.choice(NAMES)},
              "metrics": {"enabled": True, "port": ports[3]}}
    (work / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    return {"answer": ports[2]}


def b64_setup(work, rng):
    word = rng.choice(("lantern", "harbor", "pebble", "thistle", "compass", "ember", "orchid", "falcon"))
    note = f"the vault word is {word}\n"
    (work / "secret.txt").write_text(base64.b64encode(note.encode()).decode() + "\n")
    return {"answer": word}


def url_verify(work, meta, value):
    """shadow, /etc/shadow or etc/shadow."""
    return value.strip().rstrip("/").rsplit("/", 1)[-1] == meta["answer"]


def url_setup(work, rng):
    target = rng.choice(("passwd", "shadow", "sudoers", "hosts", "crontab", "fstab"))
    ips = [f"10.1.{rng.randint(0, 9)}.{rng.randint(1, 254)}" for _i in range(8)]
    queries = ("red%20shoes", "caf%C3%A9", "50%25%20off", "a%2Bb", "size%3D42")
    lines = [f"{rng.choice(ips)} GET /search?q={rng.choice(queries)} 200" for _i in range(rng.randint(30, 50))]
    attack = "".join(f"%{b:02x}" for b in f"../../../etc/{target}".encode())
    lines.insert(rng.randint(5, len(lines) - 5), f"{rng.choice(ips)} GET /download?file={attack} 200")
    (work / "access.log").write_text("\n".join(lines) + "\n")
    return {"answer": target}


# --- level 3 ------------------------------------------------------------------

INJECT_CODE = '''
import os


def main():
    with open("hosts.txt") as fh:
        for host in fh.read().split("\\n"):
            if host:
                os.system("echo checking " + host)


if __name__ == "__main__":
    main()
'''

EVIL = ("; touch pwned", "$(touch pwned)", "`touch pwned`", " && touch pwned", " | touch pwned")


def inject_setup(work, rng):
    hosts = rng.sample(HOSTS, 3) + [rng.choice(HOSTS) + rng.choice(EVIL)]
    (work / "hosts.txt").write_text("\n".join(hosts) + "\n")
    write(work, "check_hosts.py", "#", [
        _("Fight: hosts.txt comes from a web form. One line hides a command, and this script runs it."),
        _("Input: hosts.txt, one host per line."),
        _("Wanted: 'checking <line>' for each line, exactly as written, and nothing else run."),
        _("Run it:") + " python3 check_hosts.py   (then ls: a new file means the attack worked)",
        _("Help:") + " bashou explain python subprocess",
    ], INJECT_CODE)
    return {}


def inject_verify(work, meta, value):
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copy(work / "check_hosts.py", tmp)
        hosts = list(HOSTS[:2]) + [h + e for h, e in zip(HOSTS[2:], EVIL)] + ["-n", "$HOME"]
        Path(tmp, "hosts.txt").write_text("\n".join(hosts) + "\n")
        r = run([sys.executable, "check_hosts.py"], tmp, timeout=10)
        clean = sorted(os.listdir(tmp)) == ["check_hosts.py", "hosts.txt"]
        return bool(r) and r.returncode == 0 and clean and r.stdout == "".join(f"checking {h}\n" for h in hosts)


def b64url(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def jwt_setup(work, rng):
    user = rng.choice(NAMES) + rng.choice(("", "_ops", "-admin", "42"))
    head = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = b64url(json.dumps({"sub": user, "role": rng.choice(("admin", "viewer", "deploy")),
                              "exp": rng.randint(1_790_000_000, 1_800_000_000)}).encode())
    sig = b64url(bytes(rng.randrange(256) for _i in range(32)))
    (work / "token.txt").write_text(f"{head}.{body}.{sig}\n")
    return {"answer": user}


# --- C ------------------------------------------------------------------------

LEAK_CODE = r'''
#include <ctype.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char *shout(const char *line)
{
    size_t len = strlen(line);
    char *loud = malloc(len + 1);
    if (!loud)
        return NULL;
    for (size_t i = 0; i < len; i++)
        loud[i] = toupper((unsigned char)line[i]);
    loud[len] = '\0';
    return loud;
}

int main(void)
{
    char line[256];
    while (fgets(line, sizeof line, stdin)) {
        char *loud = shout(line);
        if (!loud)
            return 1;
        fputs(loud, stdout);
    }
    return 0;
}
'''


def leak_setup(work, rng):
    names = rng.sample(NAMES, 5)
    (work / "names.txt").write_text("\n".join(names) + "\n")
    write(work, "shout.c", "c", [
        _("Fight: the output is right, but memory leaks: AddressSanitizer reports it at the end."),
        _("Input: lines on stdin (names.txt)."),
        _("Wanted: each line in capitals, and every malloc freed."),
        _("Run it:") + " gcc -g -fsanitize=address shout.c -o shout && ./shout < names.txt",
        _("Help:") + " bashou explain c malloc",
    ], LEAK_CODE)
    runs = []
    for _i in range(3):
        text = "".join(n + "\n" for n in rng.sample(NAMES, rng.randint(1, 8)))
        runs.append([[], text, text.upper()])
    return {"runs": runs}


FENCE_CODE = r'''
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
    int count = argc - 1;
    if (count == 0) {
        fprintf(stderr, "usage: ./average N...\n");
        return 1;
    }
    int *values = malloc(count * sizeof *values);
    if (!values)
        return 1;
    for (int i = 0; i < count; i++)
        values[i] = atoi(argv[i + 1]);
    long total = 0;
    for (int i = 0; i <= count; i++)
        total += values[i];
    printf("%ld\n", total / count);
    free(values);
    return 0;
}
'''


def fence_setup(work, rng):
    nums = [rng.randint(1, 99) for _i in range(4)]
    write(work, "average.c", "c", [
        _("Fight: the average is wrong, or AddressSanitizer stops it: a loop reads one box too far."),
        _("Input: whole numbers as arguments."),
        _("Wanted: their average, rounded down: ./average 2 4 9 prints 5."),
        _("Run it:") + " gcc -g -fsanitize=address average.c -o average && ./average " + " ".join(map(str, nums)),
        _("Help:") + " bashou explain c array",
    ], FENCE_CODE)
    runs = []
    for _i in range(4):
        xs = [rng.randint(0, 999) for _i in range(rng.randint(1, 9))]
        runs.append([[str(x) for x in xs], "", f"{sum(xs) // len(xs)}\n"])
    return {"runs": runs}


STACK_CODE = r'''
#include <stdio.h>
#include <stdlib.h>

static long sum_to(long n)
{
    return n + sum_to(n - 1);
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: ./sum N\n");
        return 1;
    }
    printf("%ld\n", sum_to(atol(argv[1])));
    return 0;
}
'''


def stack_setup(work, rng):
    write(work, "sum.c", "c", [
        _("Fight: sum_to() calls itself forever, until the stack overflows (segfault)."),
        _("Input: a number N >= 0."),
        _("Wanted: 1 + 2 + ... + N: ./sum 4 prints 10, ./sum 0 prints 0."),
        _("Run it:") + " gcc -g sum.c -o sum && ./sum 4",
        _("Help:") + " bashou explain c recursion",
    ], STACK_CODE)
    return {"runs": [[[str(n)], "", f"{n * (n + 1) // 2}\n"] for n in (0, 1, 4, rng.randint(50, 2000))]}


OVERFLOW_CODE = r'''
#include <stdio.h>
#include <string.h>

int main(int argc, char **argv)
{
    char name[8];
    if (argc != 2) {
        fprintf(stderr, "usage: ./greet NAME\n");
        return 1;
    }
    strcpy(name, argv[1]);
    printf("Hello, %s!\n", name);
    return 0;
}
'''


def overflow_setup(work, rng):
    write(work, "greet.c", "c", [
        _("Fight: a long name writes past the 8-byte buffer. In real code that is how attackers get in."),
        _("Input: a name as the only argument, of any length."),
        _("Wanted: Hello, <the whole name>! for any name, with no memory error."),
        _("Run it:") + " gcc -g -fsanitize=address greet.c -o greet && ./greet averyveryverylongname",
        _("Help:") + " bashou explain c string",
    ], OVERFLOW_CODE)
    long = "".join(rng.choice("abcdefghij") for _i in range(rng.randint(300, 2000)))
    return {"runs": [[[n], "", f"Hello, {n}!\n"] for n in (rng.choice(NAMES), "averyveryverylongname", long)]}


# --- the fights -----------------------------------------------------------------

PY = dict(tools=PYTHON, requires=["python3"], skill="python")
C = dict(tools=COMPILERS, uses=c_used, requires=["gcc"], skill="c")

ALL = [
    Challenge(level=1, id="colon_cobra", fix=True, pet="snake", threat="Colon Cobra", **PY,
              task="The Colon Cobra swallowed a character in greet.py: Python stops at a SyntaxError.\n"
                   "Fix greet.py (its first lines say what it must do). Run it: python3 greet.py\n"
                   "When it works, type: verify",
              hints=["Read the error from the bottom: the last line names the problem, the lines above "
                     "point at where. A def or a for line ends with something.",
                     "Add the missing : at the end of the def line, then run python3 greet.py."],
              setup=colon_setup, verify=py_output("greet.py")),
    Challenge(level=1, id="semicolon_slug", fix=True, pet="beaver", threat="Semicolon Slug", **C,
              task="The Semicolon Slug ate a character in hello.c: gcc refuses to build it.\n"
                   "Fix hello.c (its first lines say what it must do). Run it: gcc hello.c -o hello && ./hello\n"
                   "When it works, type: verify",
              hints=["gcc prints file:line:column: error. In C every statement ends with the same character.",
                     "Add the missing ; after the printf(...) line, then build and run again."],
              setup=semicolon_setup, verify=c_tests("hello.c")),
    Challenge(level=2, id="list_leech", fix=True, pet="snake", threat="List Leech", **PY,
              task="The List Leech clings to hosts.py: unique() leaves duplicates and changes its input.\n"
                   "Fix hosts.py (its first lines say what it must do). Run it: python3 hosts.py\n"
                   "When it works, type: verify",
              hints=["Removing items from a list while a for loop walks over it makes the loop skip some. "
                     "Build a new list instead: bashou explain python list",
                     "Try: seen = [] then for host in hosts: if host not in seen: seen.append(host), "
                     "and return seen."],
              setup=list_setup, verify=py_tests("hosts.py", "unique")),
    Challenge(level=2, id="dict_djinn", fix=True, pet="snake", threat="Dict Djinn", **PY,
              task="The Dict Djinn hid a key: tally.py crashes with KeyError: '{level}'.\n"
                   "Fix tally.py (its first lines say what it must do). Run it: python3 tally.py\n"
                   "When it works, type: verify",
              hints=["counts[level] += 1 reads counts[level] first, and the first time it isn't there. "
                     "bashou explain python dict",
                     "Try: counts[level] = counts.get(level, 0) + 1"],
              setup=dict_setup, verify=py_tests("tally.py", "count_levels")),
    Challenge(level=2, id="loop_lich", fix=True, pet="snake", threat="Loop Lich", **PY,
              task="The Loop Lich traps retry.py in a loop that never ends.\n"
                   "Fix retry.py (its first lines say what it must do). Run it: python3 retry.py\n"
                   "When it works, type: verify",
              hints=["A while loop stops when its condition turns false. What in the loop changes i? "
                     "bashou explain python loop",
                     "Add i += 1 inside the loop (or write: for i in range(tries):)."],
              setup=loop_setup, verify=py_tests("retry.py", "delays")),
    Challenge(level=2, id="ouroboros", fix=True, pet="snake", threat="Ouroboros", **PY,
              task="The Ouroboros bites its own tail: du.py forgets the files in subfolders.\n"
                   "Fix du.py (its first lines say what it must do). Run it: python3 du.py\n"
                   "When it works, type: verify",
              hints=["total(item) is called for each subfolder, but where does its result go? "
                     "bashou explain python recursion",
                     "Write: size += total(item)"],
              setup=tree_setup, verify=py_tests("du.py", "total")),
    Challenge(level=2, id="json_jinn", pet="snake", threat="JSON Jinn", **PY,
              task="The JSON Jinn guards config.json. Read it with python3, not by eye.\n"
                   "Which port does the database use? Answer with: answer <port>",
              hints=["python3 -c runs one line of Python. json.load turns the file into dicts: "
                     "bashou explain python json",
                     "Try: python3 -c \"import json; print(json.load(open('config.json'))['database']['port'])\""],
              setup=json_setup),
    Challenge(level=2, id="base64_banshee", pet="snake", threat="Base64 Banshee", **PY,
              task="The Base64 Banshee wails in secret.txt: it's base64, not a secret code.\n"
                   "Decode it with python3. What is the vault word?",
              hints=["base64 is an encoding, anyone can undo it: bashou explain python base64",
                     "Try: python3 -c \"import base64; print(base64.b64decode(open('secret.txt').read()).decode())\""],
              setup=b64_setup),
    Challenge(level=2, id="percent_poltergeist", pet="snake", threat="Percent Poltergeist", **PY,
              task="The Percent Poltergeist hides an attack in access.log behind %XX codes.\n"
                   "Decode the log with python3. Which file under /etc was the attacker after?",
              hints=["urllib.parse.unquote turns %2e%2e%2f back into ../ : bashou explain python url",
                     "Try: python3 -c \"import urllib.parse; print(urllib.parse.unquote(open('access.log').read()))\""
                     " | grep etc"],
              setup=url_setup, verify=url_verify),
    Challenge(level=3, id="injection_imp", fix=True, pet="snake", threat="Injection Imp", after=("list_leech",), **PY,
              task="The Injection Imp slipped a command into hosts.txt, and check_hosts.py runs it.\n"
                   "Fix check_hosts.py (its first lines say what it must do). Run it: python3 check_hosts.py\n"
                   "When it works, type: verify",
              hints=["os.system hands the whole string to a shell, so ; $( ) | in the data become commands. "
                     "bashou explain python subprocess",
                     "Try: subprocess.run(['echo', 'checking', host]) (import subprocess), or just print."],
              setup=inject_setup, verify=inject_verify),
    Challenge(level=3, id="token_trickster", pet="snake", threat="Token Trickster", after=("base64_banshee",), **PY,
              task="The Token Trickster flashes a JWT in token.txt. Signed is not secret: read it.\n"
                   "Which user (sub) is the token for? Decode it with python3.",
              hints=["A JWT is header.payload.signature, each part base64url without padding. "
                     "bashou explain python base64",
                     "Try: python3 -c \"import base64; p = open('token.txt').read().split('.')[1]; "
                     "print(base64.urlsafe_b64decode(p + '=='))\""],
              setup=jwt_setup),
    Challenge(level=2, id="leak_lurker", fix=True, works=lambda: bool(sanitizer()), pet="beaver", threat="Leak Lurker", **C,
              task="The Leak Lurker feeds on memory nobody frees in shout.c.\n"
                   "Fix shout.c (its first lines say what it must do). "
                   "Run it: gcc -g -fsanitize=address shout.c -o shout && ./shout < names.txt\n"
                   "When it works, type: verify",
              hints=["AddressSanitizer names the line where the leaked memory was allocated. "
                     "Who should free it once it's printed? bashou explain c malloc",
                     "Add free(loud); right after fputs(loud, stdout);"],
              setup=leak_setup, verify=c_tests("shout.c")),
    Challenge(level=2, id="fencepost_fiend", fix=True, works=lambda: bool(sanitizer()), pet="beaver", threat="Fencepost Fiend", **C,
              task="The Fencepost Fiend moved a fence post in average.c: a loop goes one step too far.\n"
                   "Fix average.c (its first lines say what it must do). "
                   "Run it: gcc -g -fsanitize=address average.c -o average && ./average 2 4 9\n"
                   "When it works, type: verify",
              hints=["An array of count items goes from 0 to count - 1. Compare the two loops. "
                     "bashou explain c array",
                     "In the second loop, write i < count instead of i <= count."],
              setup=fence_setup, verify=c_tests("average.c")),
    Challenge(level=2, id="stack_specter", fix=True, pet="beaver", threat="Stack Specter", **C,
              task="The Stack Specter haunts sum.c: sum_to() never stops calling itself.\n"
                   "Fix sum.c (its first lines say what it must do). Run it: gcc -g sum.c -o sum && ./sum 4\n"
                   "When it works, type: verify",
              hints=["Every recursion needs a case that returns without calling itself. "
                     "bashou explain c recursion",
                     "Add at the start of sum_to: if (n <= 0) return 0;"],
              setup=stack_setup, verify=c_tests("sum.c")),
    Challenge(level=3, id="overflow_ogre", fix=True, pet="beaver", threat="Overflow Ogre", after=("leak_lurker",), **C,
              task="The Overflow Ogre stuffs long names into an 8-byte box in greet.c.\n"
                   "Fix greet.c (its first lines say what it must do). "
                   "Run it: gcc -g -fsanitize=address greet.c -o greet && ./greet averyveryverylongname\n"
                   "When it works, type: verify",
              hints=["strcpy never checks the size of the target. Does the name need copying at all? "
                     "bashou explain c string",
                     "Simplest: printf(\"Hello, %s!\\n\", argv[1]); or malloc(strlen(argv[1]) + 1) and free it."],
              setup=overflow_setup, verify=c_tests("greet.c")),
]
