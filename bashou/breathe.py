"""Guided breathing, the original Zenos feature."""

import shutil
import sys
import time
from datetime import date, timedelta

from . import state

PATTERNS = {
    "box": [("Inhale", 4), ("Hold", 4), ("Exhale", 4), ("Hold", 4)],
    "478": [("Inhale", 4), ("Hold", 7), ("Exhale", 8)],
    "calm": [("Inhale", 4), ("Exhale", 6)],
}
DIM, BOLD, CYAN, RESET = "\033[2m", "\033[1m", "\033[36m", "\033[0m"


def bar(fraction, width, growing):
    filled = round(fraction * width) if growing else round((1 - fraction) * width)
    return CYAN + "●" * filled + DIM + "·" * (width - filled) + RESET


def phase(label, seconds, width):
    growing = label != "Exhale"
    steps = seconds * 10
    for i in range(steps + 1):
        remaining = seconds - i // 10
        sys.stdout.write(f"\r  {BOLD}{label:<7}{RESET} {bar(i / steps, width, growing)} {remaining:>2}s ")
        sys.stdout.flush()
        time.sleep(0.1)


def breathe(pattern, cycles):
    width = min(40, shutil.get_terminal_size().columns - 24)
    print(f"\n  {BOLD}Bashou{RESET} · {pattern} · {cycles} cycles  {DIM}(Ctrl+C to stop){RESET}\n")
    done, start = 0, time.monotonic()
    try:
        for _ in range(cycles):
            for label, seconds in PATTERNS[pattern]:
                phase(label, seconds, width)
            done += 1
    except KeyboardInterrupt:
        pass
    elapsed = round(time.monotonic() - start)
    sys.stdout.write("\r\033[K")
    print(f"  {done} cycle(s), {elapsed}s. Well done.\n")
    if done:
        with state.locked() as s:
            s["breathe"].append({"date": date.today().isoformat(), "pattern": pattern,
                                 "cycles": done, "seconds": elapsed})


def streak(days):
    count, day = 0, date.today()
    if day.isoformat() not in days:
        day -= timedelta(days=1)
    while day.isoformat() in days:
        count += 1
        day -= timedelta(days=1)
    return count


def stats():
    log = state.load()["breathe"]
    if not log:
        print("No session yet. Run `bashou breathe` to start.")
        return
    total = sum(s["seconds"] for s in log)
    days = {s["date"] for s in log}
    print(f"  Sessions      : {len(log)}")
    print(f"  Total time    : {total // 60} min {total % 60} s")
    print(f"  Active days   : {len(days)}")
    print(f"  Current streak: {streak(days)} day(s)")
