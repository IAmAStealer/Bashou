from . import Challenge


def setup(work, rng):
    ips = list(dict.fromkeys(f"10.0.{rng.randint(0, 9)}.{rng.randint(1, 254)}" for _ in range(15)))
    pages = ["/", "/index.html", "/about", "/shop", "/cart", "/login"]
    lines = []
    for _ in range(rng.randint(150, 250)):
        lines.append(f"{rng.choice(ips)} GET {rng.choice(pages)} 200")
    lost = rng.sample(ips, rng.randint(3, 8))       # the IPs that hit a missing page
    for ip in lost:
        for _ in range(rng.randint(1, 4)):
            lines.append(f"{ip} GET /old-{rng.randint(1, 99)}.html 404")
    for _ in range(5):                               # decoys: "404" in the page, status 200
        lines.append(f"{rng.choice(ips)} GET /404.html 200")
    rng.shuffle(lines)
    (work / "access.log").write_text("\n".join(lines) + "\n")
    return {"answer": len(lost)}


CHALLENGE = Challenge(
    level=3, after=("grep_hydra", "uniq_swarm"), id="pipe_eel", pet="octopus", tools=("|",), threat="Knot Eel",
    task="The Knot Eel ties commands into knots. Untie it with one pipeline of at least 3 commands.\n"
         "In access.log (ip, method, page, status), how many different IPs got a 404 status?",
    hints=["One small step per command, joined with |: keep the 404 lines, keep the IP, drop duplicates, count.",
           "Try: grep ' 404$' access.log | cut -d' ' -f1 | sort -u | wc -l"],
    setup=setup,
    uses=lambda analysis: analysis.pipes >= 3,
    requires=["grep", "cut", "sort", "wc"],
)
