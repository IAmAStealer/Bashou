from . import Challenge

WORDS = ["old", "misc", "tmp", "stuff", "docs", "src", "keep", "notes", "cache", "trash"]


def setup(work, rng):
    maze = work / "maze"
    dirs = [maze]
    for _ in range(rng.randint(12, 20)):
        d = rng.choice(dirs) / rng.choice(WORDS)
        d.mkdir(parents=True, exist_ok=True)
        dirs.append(d)
    count = 0
    for i in range(rng.randint(40, 70)):
        d = rng.choice(dirs)
        ext = rng.choice([".txt", ".log", ".bak", ".md", ".bak", ".conf"])
        f = d / f"file{i}{ext}"
        f.write_text("x" * rng.randint(0, 50))
        count += ext == ".bak"
    # Decoys: directories named like backups are not files.
    for _ in range(3):
        (rng.choice(dirs) / f"archive{rng.randint(0, 99)}.bak").mkdir(exist_ok=True)
    return {"task": "The Maze Wraith hides in backup files.\n"
                    "How many regular files ending in .bak are there in maze/, at any depth?\n"
                    "(Careful: some directories are named *.bak too.)",
            "answer": count}


CHALLENGE = Challenge(
    id="find_wraith", pet="fox", tools=("find",), threat="Maze Wraith",
    hints=["find walks every subdirectory; -type f keeps only files, -name matches a pattern.",
           "Try: find maze -type f -name '*.bak' | wc -l"],
    setup=setup,
)
