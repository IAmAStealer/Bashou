"""`bashou learn`: take a command apart (the last one your pet suggested, or yours) and explain each piece."""

import re
import shlex
import sys

from . import state
from .i18n import _

BOLD, DIM, CYAN, RESET = "\x1b[1m", "\x1b[2m", "\x1b[36m", "\x1b[0m"

# What each command does. Flags: "-x" -> meaning; FLAG_VALUE: flags followed by a value.
COMMANDS = {
    "awk": "reads text line by line and splits each line into columns ($1, $2…)",
    "bash": "the shell itself: runs commands or a script",
    "basename": "keeps only the last part of a path",
    "bashou": "your pet",
    "cat": "prints files (or what comes in)",
    "cd": "changes the current folder",
    "chmod": "changes who can read, write or run a file",
    "chown": "changes who owns a file",
    "cp": "copies files",
    "curl": "talks to a web server: downloads, sends, shows headers",
    "date": "prints the date and time",
    "df": "shows how full the disks are",
    "diff": "shows the lines that differ between two files",
    "dig": "asks the DNS where a name points",
    "du": "measures how much space files and folders take",
    "echo": "prints its arguments",
    "find": "looks for files and folders, going down every folder",
    "free": "shows the memory in use and free",
    "git": "version control: saves the history of a project",
    "grep": "prints the lines that match a pattern",
    "head": "prints the first lines",
    "history": "lists the commands you ran",
    "jq": "reads and reshapes JSON",
    "journalctl": "reads the system logs",
    "kill": "sends a signal to a process (by default: stop)",
    "kubectl": "controls a Kubernetes cluster",
    "less": "shows a file one screen at a time (q quits)",
    "ln": "creates a link to a file or folder",
    "ls": "lists the files in a folder",
    "make": "builds a project with the steps in its Makefile",
    "mkdir": "creates a folder",
    "pgrep": "finds processes by their name",
    "ps": "lists the running processes",
    "pwd": "prints the current folder",
    "read": "reads one line into a variable",
    "rm": "deletes files",
    "rsync": "copies only what changed, locally or to another machine",
    "sh": "a simple shell",
    "sed": "edits text as it flows: replace, delete, print lines",
    "sha256sum": "computes a fingerprint to check a file wasn't changed",
    "sort": "sorts lines",
    "ssh": "opens a shell on another machine, encrypted",
    "stat": "shows a file's details",
    "strace": "shows the system calls a program makes",
    "sudo": "runs the rest of the line as the administrator (root)",
    "systemctl": "controls the services (systemd)",
    "tail": "prints the last lines",
    "tar": "packs files into one archive, or unpacks it",
    "tee": "writes what comes in to a file and passes it on",
    "tr": "replaces or deletes characters",
    "uniq": "merges lines that repeat one after the other",
    "watch": "runs a command again every few seconds",
    "wc": "counts lines, words and bytes",
    "xargs": "turns the lines that come in into arguments of a command",
    "xz": "compresses a file (very small, a bit slow)",
}

FLAGS = {
    "awk": {"-F": "the column separator (here: {value})"},
    "bash": {"-c": "run this text as a command: {value}"},
    "chmod": {},
    "cp": {"-r": "recursive: copy the folder and everything in it"},
    "curl": {"-f": "fail on HTTP errors instead of saving the error page", "-s": "silent: no progress bar",
             "-S": "still show errors", "-L": "follow redirects", "-o": "save to this file: {value}",
             "-I": "only the headers of the answer", "-d": "send this data (a POST): {value}"},
    "date": {"+%A": "the format: %A is the day of the week"},
    "dig": {"+short": "only the answer", "+trace": "follow the question from the root servers down"},
    "df": {"-h": "human sizes (G, M)"},
    "du": {"-s": "one total per argument", "-h": "human sizes (G, M)"},
    "find": {"-mtime": "modified days ago: {value} (-1 = less than a day)", "-name": "the name matches {value}",
             "-exec": "runs a command on each result; {{}} is the file", "-prune": "don't go into it",
             "-o": "or", "-type": "only this kind: {value} (f = file, d = folder)", "-print": "print the result",
             "-print0": "print the results separated by a null byte (safe with any name)"},
    "free": {"-h": "human sizes (G, M)"},
    "git": {"-c": "create the branch", "--oneline": "one line per commit", "--graph": "draw the branches"},
    "grep": {"-r": "recursive: every file in every folder", "-n": "show line numbers",
             "-E": "extended regex: | means or", "-C": "{value} lines of context around each match"},
    "jq": {"-r": "raw: strings without their quotes"},
    "journalctl": {"-u": "only the logs of this service: {value}"},
    "kill": {"-TERM": "the signal to send: TERM asks it to stop cleanly"},
    "kubectl": {"-A": "in every namespace", "-f": "follow: keep printing new lines",
                "-i": "interactive: keep the input open", "-t": "give it a terminal",
                "--": "the rest is the command to run inside"},
    "ln": {"-s": "symbolic: a shortcut to the path"},
    "mkdir": {"-p": "create the missing parent folders too"},
    "pgrep": {"-a": "show the full command line too"},
    "read": {"-r": "keep backslashes as they are"},
    "rsync": {"-a": "archive: keep permissions, dates, links, and go into folders", "-v": "verbose: list the files"},
    "sed": {"-i": "in place: change the file itself", "-n": "print nothing unless asked (p)"},
    "sort": {"-r": "reverse order", "-n": "compare as numbers", "-u": "only one of each line"},
    "ssh": {"-L": "forward a local port to the other side: {value}"},
    "stat": {"-c": "the format: {value} (%a = permissions in octal)"},
    "strace": {"-e": "only these calls: {value}", "-f": "follow the child processes too",
               "-c": "count the calls instead of printing them"},
    "systemctl": {"--now": "and start it right away"},
    "tar": {"-c": "create an archive", "-z": "compressed with gzip", "-f": "the archive file: {value}",
            "-t": "list what's inside", "-x": "extract", "-C": "extract into this folder: {value}"},
    "uniq": {"-c": "count how many times each line repeats"},
    "wc": {"-l": "only the number of lines"},
    "watch": {"-n": "every {value} seconds"},
    "xargs": {"-I": "{value} stands for each line in the command", "-P": "run {value} at a time, in parallel",
              "-n": "{value} argument per run", "-0": "lines separated by a null byte (safe with any name)"},
    "xz": {"-k": "keep the original file"},
}
FLAG_VALUE = {"awk": {"F"}, "bash": {"c"}, "curl": {"o", "d"}, "find": {"mtime", "name", "type"}, "grep": {"C"},
              "journalctl": {"u"}, "ssh": {"L"}, "stat": {"c"}, "strace": {"e"}, "tar": {"f", "C"},
              "watch": {"n"}, "xargs": {"I", "P", "n"}}

# Words right after a command that pick what it does (git switch, systemctl status…).
SUBCOMMANDS = {
    "bashou": {"fight": "enter the arena"},
    "git": {"switch": "go to a branch", "stash": "put your changes aside for later", "log": "show the history",
            "bisect": "find the commit that broke something, by halves", "start": "begin"},
    "kubectl": {"get": "list objects", "describe": "show the details and events of an object",
                "logs": "print what a pod wrote", "exec": "run a command inside a pod",
                "pods": "the kind of object: pods", "pod": "the kind of object: a pod"},
    "systemctl": {"status": "is the service running? its last logs", "enable": "start it at every boot",
                  "daemon-reload": "reload the unit files after you edited one"},
}

# The plain words after these commands have a job of their own, in order (the last one repeats).
ARGS = {
    "awk": ["the awk program, run on every line ($1 = first column)", "the file"],
    "chmod": ["the new permissions", "the file"],
    "chown": ["the new owner:group", "the file"],
    "cp": ["what to copy", "the copy"],
    "grep": ["the pattern to look for", "where to look"],
    "jq": ["the filter: what to take from the JSON", "the file"],
    "ln": ["what the link points to", "the link's name"],
    "cat": ["the file"], "dig": ["the name to look up"], "git": ["the name"], "less": ["the file"],
    "ls": ["the folder to list"], "mkdir": ["the folder to create"], "pgrep": ["the name to look for"],
    "sha256sum": ["the file"], "sort": ["the file"], "stat": ["the file"], "systemctl": ["the service"],
    "tar": ["what goes into the archive"], "tee": ["the file"], "xz": ["the file"],
    "ps": ["a u x: every process, with its user, even those without a terminal"],
    "read": ["the variable that gets the line"],
    "rsync": ["what to copy (a / at the end: its content)", "where to"],
    "sed": ["the sed script: s/old/new/ replaces, g = every time, p = print", "the file"],
    "ssh": ["the machine to connect to"],
    "tr": ["the characters to replace (A-Z: every capital letter)", "what they become"],
}

SYNTAX = {
    "|": "pipe: the output of the left command goes into the next one",
    ">": "writes the output to this file (replaces it)",
    "<": "reads the input from this file",
    ">>": "adds the output at the end of this file",
    "$(": "runs the command inside and puts its output here",
    "<<": "heredoc: the next lines, up to the end word, are the input",
    "2>&1": "errors (2) go where the output (1) goes",
    "<(": "runs a command and hands its output over like a file",
    ")": "end of the inner command",
    ";": "then run the next command",
    "for": "loop: for each value…", "in": "…taken from this list", "do": "the loop body starts",
    "done": "the loop ends", "while": "loop as long as the next command succeeds",
    "{}": "stands for each file or line", "+": "run the command once with many files",
    "*": "every file here", ".": "the current folder", "~": "your home folder",
}


def remember(text):
    """Keep the first `command` a pet line suggests, for `bashou learn` (last one wins)."""
    found = re.search(r"`([^`]+)`", text or "")
    if found and not found.group(1).startswith("bashou learn"):
        try:
            state.CACHE.mkdir(parents=True, exist_ok=True)
            (state.CACHE / "learn").write_text(found.group(1).replace(" ⏎ ", "\n"))
        except OSError:
            pass


def tokens(command):
    """Words and operators; <placeholders> kept whole, heredoc bodies and newlines become ;."""
    command = re.sub(r"<(\w+)>", r"‹\1›", command.replace(" ⏎ ", "\n")).replace("\n", " ; ")
    lex = shlex.shlex(command, posix=True, punctuation_chars="|&;<>()")
    lex.whitespace_split = True
    lex.wordchars += "$:{}*.~+%=,/-[]!?@‹›^#"
    try:
        words = list(lex)
    except ValueError:                 # an open quote
        words = command.split()
    split = []
    for w in words:                    # "))" -> ")", ")"; "$" "(" -> "$("
        split += list(w) if set(w) == {")"} else [w]
    words, out, i = split, [], 0
    while i < len(words):              # glue 2 >& 1 and $ ( back together
        if words[i] == "$" and words[i + 1:i + 2] == ["("]:
            out.append("$(")
            i += 2
            continue
        if words[i] == "2" and words[i + 1:i + 3] == [">&", "1"]:
            out.append("2>&1")
            i += 3
            continue
        out.append(words[i])
        i += 1
    return out


REDIRECTS = ("<", ">", ">>")
RUNNERS = {"xargs", "strace", "watch", "sudo", "time"}      # their first plain word is a command to run


def explain(command):
    """[(piece, meaning)] for a command line."""
    rows, cmd, nth, words, i = [], None, 0, tokens(command), 0
    listing = heredoc = None
    while i < len(words):
        w, nxt = words[i], (words[i + 1] if i + 1 < len(words) else "")
        i += 1
        if heredoc and w == ";":                           # the heredoc's text, up to its end word
            text = []
            while i < len(words) and words[i] != heredoc:
                if words[i] != ";":
                    text.append(words[i])
                i += 1
            rows.append((" ".join(text) or "…", _("the text")))
            if i < len(words):
                rows.append((heredoc, _("end of the text")))
                i += 1
            heredoc, cmd = None, None
            continue
        if w in REDIRECTS or w == "<<":
            rows.append((w, _(SYNTAX[w])))
            if nxt:
                rows.append((nxt, _("the end word") if w == "<<" else _("the file")))
                i += 1
                heredoc = nxt if w == "<<" else heredoc
            continue
        if listing and w != ";":
            rows.append((w, argument(None, w, 1)))
            continue
        listing = None
        if cmd is None:                                    # expecting a command
            if w in SYNTAX:
                rows.append((w, _(SYNTAX[w])))
                if w == "for" and nxt:
                    rows.append((nxt, _("the loop variable")))
                    i += 1
                listing = w == "in" or None
            elif "=" in w or "$(" in w:
                rows.append((w, _("text; $( ) inside runs a command and puts its output here")))
            else:
                about = COMMANDS.get(w)
                rows.append((w, _(about) if about else
                             _("a command I have no notes on yet: `man {cmd}` explains it").format(cmd=w)))
                cmd, nth = (None if w == "sudo" else w), 0
            continue
        if w in ("|", ";", "<(", "$(", "do", "then"):
            rows.append((w, _(SYNTAX.get(w, "then run the next command"))))
            cmd = None
            continue
        if w in SYNTAX and w not in ".*~+{}":
            rows.append((w, _(SYNTAX[w])))
            continue
        if cmd in RUNNERS and not w.startswith("-") or (cmd == "kubectl" and rows[-1][0] == "--"):
            cmd = None
            i -= 1
            continue
        if cmd == "find" and rows[-1][0] == "-exec":
            about = COMMANDS.get(w)
            rows.append((w, _(about) if about else _("the command to run")))
            continue
        if w in SUBCOMMANDS.get(cmd, {}):
            rows.append((w, _(SUBCOMMANDS[cmd][w])))
            continue
        if re.match(r"^(--?[A-Za-z0-9]|\+[a-z%])", w) or w in FLAGS.get(cmd, {}):
            row, used = option(cmd, w, nxt)
            rows.append(row)
            i += used
            continue
        rows.append((w, argument(cmd, w, nth)))
        nth += 1
    return rows


def option(cmd, word, nxt):
    """((piece, meaning), 1 if it took the next word as its value else 0)."""
    flags, takes = FLAGS.get(cmd, {}), FLAG_VALUE.get(cmd, set())
    unknown = ((word, _("an option of {cmd}: `man {cmd}` explains it").format(cmd=cmd)), 0)
    if word in flags:
        if word.lstrip("-+") in takes and nxt:
            return (f"{word} {nxt}", _(flags[word]).format(value=nxt)), 1
        return (word, _(flags[word]).format(value="")), 0
    if word.startswith("--"):
        return unknown
    sign, letters, meanings = word[0], word[1:], []
    for j, letter in enumerate(letters):
        flag = sign + letter
        if flag not in flags:
            return unknown
        if letter in takes:
            rest = letters[j + 1:]
            value = rest or nxt
            meanings.append(_(flags[flag]).format(value=value))
            return (word if rest else f"{word} {value}", "; ".join(meanings)), (0 if rest else 1)
        meanings.append(_(flags[flag]).format(value=""))
    return (word, "; ".join(meanings)), 0


def argument(cmd, word, nth):
    """What a plain word is, from its shape and its place."""
    if word.startswith("‹"):
        return _("put the real {what} here").format(what=word.strip("‹›"))
    if word in SYNTAX:
        return _(SYNTAX[word])
    if "$(" in word:
        return _("text; $( ) inside runs a command and puts its output here")
    if word.startswith("$"):
        return _("a variable: its value goes here")
    if re.fullmatch(r"\{\d+\.\.\d+\}", word):
        a, b = word[1:-1].split("..")
        return _("the numbers from {a} to {b}").format(a=a, b=b)
    if re.match(r"https?://", word):
        return _("the address")
    if cmd in ARGS:
        return _(ARGS[cmd][min(nth, len(ARGS[cmd]) - 1)])
    return _("a file, folder or word it works on")


def main(args):
    """`bashou learn [command]`."""
    command = " ".join(args).strip()
    if not command:
        try:
            command = (state.CACHE / "learn").read_text().strip()
        except OSError:
            command = ""
    if not command:
        print("  " + _("No suggestion to explain yet. Try `bashou talk`, or `bashou learn <command>`."))
        return 1
    print(f"\n  {BOLD}{command.replace(chr(10), ' ⏎ ')}{RESET}\n")
    rows = explain(command)
    width = min(max(len(p) for p, _m in rows), 24)
    for piece, meaning in rows:
        print(f"  {CYAN}{piece:<{width}}{RESET}  {DIM}{meaning}{RESET}")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
