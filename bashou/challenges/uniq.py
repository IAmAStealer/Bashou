from . import Challenge


def setup(work, rng):
    ips = [f"10.0.{rng.randint(0, 9)}.{rng.randint(1, 254)}" for _ in range(12)]
    ips = list(dict.fromkeys(ips))
    counts = {ip: rng.randint(3, 30) for ip in ips}
    top = max(counts, key=counts.get)
    counts[top] += 5  # make the winner unique
    lines = [ip for ip, n in counts.items() for _ in range(n)]
    rng.shuffle(lines)
    (work / "visitors.txt").write_text("\n".join(lines) + "\n")
    return {"answer": top}


CHALLENGE = Challenge(
    level=2, id="uniq_swarm", pet="sofa", tools=("uniq",), threat="Echo Swarm",
    task="The Echo Swarm repeats itself endlessly.\n"
         "Which IP address appears most often in visitors.txt?",
    hints=["uniq only merges adjacent lines, so sort first. `uniq -c` counts them.",
           "Try: sort visitors.txt | uniq -c | sort -rn | head -1"],
    setup=setup,
)
