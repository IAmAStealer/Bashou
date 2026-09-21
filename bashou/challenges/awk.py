from . import Challenge

ITEMS = ["apple", "pear", "plum", "fig", "kiwi", "mango"]


def setup(work, rng):
    target = rng.choice(ITEMS)
    rows, total = ["date,item,qty,price"], 0
    for _ in range(rng.randint(60, 120)):
        item, qty = rng.choice(ITEMS), rng.randint(1, 40)
        total += qty if item == target else 0
        rows.append(f"2026-09-{rng.randint(1, 28):02d},{item},{qty},{rng.randint(1, 9)}.{rng.randint(0, 99):02d}")
    (work / "sales.csv").write_text("\n".join(rows) + "\n")
    return {"args": {"item": target}, "answer": total}


CHALLENGE = Challenge(
    id="awk_golem", pet="owl", tools=("awk", "gawk", "mawk"), threat="Ledger Golem",
    task="The Ledger Golem only yields to exact accounts.\n"
         "In sales.csv, what is the total qty (3rd column) sold for \"{item}\"?",
    hints=["awk splits lines into fields: -F, sets the separator, $2 and $3 are the columns.",
           "Try: awk -F, '$2 == \"ITEM\" { s += $3 } END { print s }' sales.csv"],
    setup=setup,
)
