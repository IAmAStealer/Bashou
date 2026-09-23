"""Turn a command line into what Bashou cares about: tools, pipes and constructs.

This is a small scanner, not a full bash parser: it only needs to be right on
the command lines people actually type.
"""

import re
import shlex
from dataclasses import dataclass, field

KEYWORDS = {"do", "then", "else", "elif", "if", "while", "until", "!", "time", "{", "}", "done", "fi", "esac"}
WRAPPERS = {"sudo", "env", "nice", "nohup", "exec", "command", "builtin", "watch", "xargs",
            "strace", "ltrace", "timeout", "stdbuf", "ionice", "doas"}
# Wrapper options that take a separate value.
HELP_READERS = {"man", "info", "help", "less", "more", "whatis", "apropos"}
OPTION_VALUES = {"-e", "-o", "-p", "-s", "-u", "-g", "-n", "-I", "-d", "-P", "-L", "-a"}
REDIRECT = re.compile(r"^(\d*|&)(>>?|<|>&|<&|&>>?)(.*)$")
# One logged command: "status<TAB>" + the output of `history 1` ("  123  command").
RECORD = re.compile(r"^(\d+)\t\s*\d+\*?  (.*)$")


@dataclass
class Analysis:
    commands: list = field(default_factory=list)   # [(name, [args])]
    pipes: int = 0                                  # longest pipeline, in stages
    constructs: set = field(default_factory=set)

    @property
    def tools(self):
        return {name for name, _ in self.commands}

    @property
    def help_only(self):
        """Only reading about commands: `wc --help`, `man wc`, `wc --help | less`."""
        return bool(self.commands) and all("--help" in args or name in HELP_READERS for name, args in self.commands)


def parse_log(text):
    """[(status, command)] from a log written by the bash hooks. Multi-line commands are joined."""
    records = []
    for line in text.split("\n"):
        m = RECORD.match(line)
        if m:
            records.append([int(m.group(1)), m.group(2)])
        elif records and line:
            records[-1][1] += "\n" + line
    return [tuple(r) for r in records]


def _split(segment):
    try:
        return shlex.split(segment, comments=True)
    except ValueError:
        return segment.split()


def _command(words, result):
    """Record the command at the start of `words`, looking through wrappers."""
    kept, skip = [], False
    for w in words:
        m = REDIRECT.match(w)
        if skip:
            skip = False
        elif m:
            skip = not m.group(3)   # `> file`: the target is the next word
        else:
            kept.append(w)
    words = kept
    while words and (words[0] in KEYWORDS or re.match(r"^[A-Za-z_]\w*=", words[0])):
        if words[0] in ("while", "until"):
            result.constructs.add("loop")
        words = words[1:]
    if not words:
        return
    if words[0] in ("for", "case", "select"):
        if words[0] == "for":
            result.constructs.add("loop")
        return
    name = words[0].lstrip("\\").rsplit("/", 1)[-1]
    if not re.match(r"^[\w.+-]+$", name):
        return
    args = words[1:]
    result.commands.append((name, args))
    if name == "tee":
        result.constructs.add("tee")
    if name in WRAPPERS:
        rest = list(args)
        while rest and (rest[0].startswith("-") or re.match(r"^[A-Za-z_]\w*=", rest[0])):
            opt = rest.pop(0)
            if opt in OPTION_VALUES and rest:
                rest.pop(0)
        if name == "timeout" and rest:
            rest.pop(0)
        _command(rest, result)


def analyze(line):
    """Analyze one (possibly multi-line) command line."""
    result = Analysis()
    segments, current = [], []
    stages = 1
    quote = None
    outer = []          # quote state to restore when a $( ) opened inside "..." closes
    heredocs = []
    i, n = 0, len(line)

    def cut(new_pipeline=True):
        nonlocal stages
        segments.append("".join(current))
        current.clear()
        if new_pipeline:
            result.pipes = max(result.pipes, stages)
            stages = 1

    while i < n:
        ch = line[i]
        two = line[i:i + 2]
        if quote == "'":
            current.append(ch)
            if ch == "'":
                quote = None
            i += 1
            continue
        if ch == "\\" and i + 1 < n:
            current.append(line[i:i + 2])
            i += 2
            continue
        if quote == '"':
            if ch == '"':
                quote = None
                current.append(ch)
                i += 1
                continue
            if two == "$(" and line[i:i + 3] != "$((":
                result.constructs.add("subst")
                cut()
                outer.append('"')
                quote = None
                i += 2
                continue
            current.append(ch)
            i += 1
            continue
        # Outside quotes.
        if ch in "'\"":
            quote = ch
            current.append(ch)
        elif ch == "#" and (not current or current[-1] in " \t"):
            while i < n and line[i] != "\n":
                i += 1
            continue
        elif two == "$(" and line[i:i + 3] != "$((":
            result.constructs.add("subst")
            cut()
            outer.append(None)
            i += 2
            continue
        elif ch == ")" and outer:
            cut()
            quote = outer.pop()
            if quote:
                current.append('"')
        elif two == "$(":
            # Arithmetic $(( )): not a command.
            depth = 0
            while i < n:
                depth += (line[i] == "(") - (line[i] == ")")
                current.append(line[i])
                i += 1
                if depth == 0 and line[i - 1] == ")":
                    break
            continue
        elif two in ("<(", ">(") :
            result.constructs.add("procsub")
            cut()
            i += 2
            continue
        elif ch == "`":
            result.constructs.add("subst")
            cut()
        elif two == "||" or two == "&&":
            cut()
            i += 2
            continue
        elif ch == "|":
            stages += 1
            cut(new_pipeline=False)
            i += 2 if two == "|&" else 1
            continue
        elif line.startswith("2>&1", i) or two == "&>":
            result.constructs.add("stderr")
            current.append(line[i:i + 4] if two != "&>" else two)
            i += 4 if two != "&>" else 2
            continue
        elif two == "<<" and line[i:i + 3] != "<<<":
            m = re.match(r"<<-?\s*(['\"]?)(\w+)\1", line[i:])
            if m:
                result.constructs.add("heredoc")
                heredocs.append(m.group(2))
                i += m.end()
                continue
            current.append(two)
            i += 2
            continue
        elif ch in ";&(){}" and not (ch == "&" and current and current[-1] in "<>"):
            cut()
        elif ch == "\n":
            cut()
            if heredocs:
                # Skip the heredoc bodies: they are data, not commands.
                rest = line[i + 1:].split("\n")
                skipped = 0
                for delim in heredocs:
                    while skipped < len(rest) and rest[skipped].strip() != delim:
                        skipped += 1
                    skipped += 1
                heredocs.clear()
                i += 1 + sum(len(r) + 1 for r in rest[:skipped])
                continue
        else:
            current.append(ch)
        i += 1
    cut()

    for segment in segments:
        if segment.strip():
            _command(_split(segment), result)
    return result
