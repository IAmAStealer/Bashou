import os
import signal
import subprocess
import time
from pathlib import Path

from . import Challenge


def setup(work, rng):
    name = f"phantom-{rng.randrange(16 ** 4):04x}"
    # Detached from Python; cleanup() kills it when the arena closes.
    out = subprocess.run(["bash", "-c", f"(exec -a {name} sleep 3600) </dev/null >/dev/null 2>&1 & echo $!"],
                         capture_output=True, text=True)
    pid = int(out.stdout)
    # `$!` comes back before the subshell has exec'd: wait until the process shows its name.
    for _ in range(100):
        try:
            if Path(f"/proc/{pid}/cmdline").read_bytes().startswith(name.encode()):
                break
        except OSError:
            pass
        time.sleep(0.02)
    return {"args": {"name": name}, "answer": pid, "pid": pid}


def cleanup(meta):
    try:
        os.kill(meta["pid"], signal.SIGTERM)
    except (OSError, KeyError):
        pass


CHALLENGE = Challenge(
    id="ps_phantom", pet="ghost", tools=("ps", "pgrep", "pidof"), threat="Process Phantom",
    task="A Process Phantom named {name} haunts this machine.\nWhat is its PID?",
    hints=["`ps aux` lists every process with its PID in the 2nd column; filter it with grep.",
           "Try: pgrep -f phantom   or   ps aux | grep phantom"],
    setup=setup, cleanup=cleanup, requires=["ps"],
)
