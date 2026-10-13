"""What Bashou asks about other processes: their parent, their command line, and whether a shell is at its
prompt. Linux answers from /proc; macOS has no /proc, so ps and the terminal itself answer there (2026-10-13).
"""

import os
import subprocess
from pathlib import Path

PROC = Path("/proc/self/stat").exists()


def ps(pid, field):
    """One `ps -o` column of process `pid`, or None when it's gone."""
    try:
        out = subprocess.run(["ps", "-o", f"{field}=", "-p", str(pid)], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else None


def parent(pid):
    """(parent pid, program name) of `pid`, or None when it's gone."""
    if PROC:
        try:
            name = Path(f"/proc/{pid}/comm").read_text().strip()
            return int(Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[1]), name
        except (OSError, ValueError, IndexError):
            return None
    ppid, comm = ps(pid, "ppid"), ps(pid, "comm")
    if ppid is None or comm is None:
        return None
    return int(ppid), os.path.basename(comm.lstrip("-"))      # macOS: full path, and -zsh for a login shell


def command(pid):
    """The command line of `pid` ("" when it's gone), its words separated by spaces."""
    if PROC:
        try:
            return Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace").strip()
        except OSError:
            return ""
    return ps(pid, "command") or ""


def at_prompt(pid, fd=1):
    """True when shell `pid` owns its terminal (no command running): its process group is the terminal's
    foreground one. Linux reads both from /proc; elsewhere `fd` is that terminal."""
    if PROC:
        try:
            with open(f"/proc/{pid}/stat") as f:
                fields = f.read().rsplit(")", 1)[1].split()
        except OSError:
            return False
        return fields[2] == fields[5]   # pgrp == tpgid
    try:
        return os.getpgid(pid) == os.tcgetpgrp(fd)
    except OSError:
        return False
