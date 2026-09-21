from . import Challenge

LEVELS = ["INFO", "INFO", "INFO", "DEBUG", "WARN", "ERROR"]
MESSAGES = ["user login", "cache miss", "disk almost full", "request timeout", "payment accepted",
            "connection reset", "retrying job", "config reloaded", "error page served"]


def setup(work, rng):
    lines, count = [], 0
    for i in range(rng.randint(250, 400)):
        level = rng.choice(LEVELS)
        count += level == "ERROR"
        lines.append(f"2026-09-{rng.randint(1, 28):02d} 12:{i % 60:02d} [{level}] {rng.choice(MESSAGES)}")
    (work / "app.log").write_text("\n".join(lines) + "\n")
    return {"task": "The Log Hydra grows a head for every [ERROR] line in app.log.\n"
                    "How many lines contain [ERROR]? (lowercase \"error\" doesn't count)",
            "answer": count}


CHALLENGE = Challenge(
    id="grep_hydra", pet="mole", tools=("grep", "egrep", "rg"), threat="Log Hydra",
    hints=["grep can count matching lines by itself: look at `grep -c`.",
           "Try: grep -c '\\[ERROR\\]' app.log  (or grep -cF '[ERROR]' app.log)"],
    setup=setup,
)
