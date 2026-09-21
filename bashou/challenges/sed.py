from . import Challenge

SENTENCES = ["I left {} keys on {} table.", "{} cat sat near {} door.", "Send {} report before {} meeting.",
             "{} sun rises over {} hills.", "Water {} plants and feed {} fish."]


def setup(work, rng):
    good, bad = [], []
    for _ in range(rng.randint(8, 14)):
        s = rng.choice(SENTENCES)
        words = [rng.choice(["the", "teh"]) for _ in range(2)]
        bad.append(s.format(*words).capitalize())
        good.append(s.format("the", "the").capitalize())
    (work / "letter.txt").write_text("\n".join(bad) + "\n")
    return {"expected": "\n".join(good) + "\n"}


def verify(work, meta, value):
    return (work / "letter.txt").read_text() == meta["expected"]


CHALLENGE = Challenge(
    id="sed_serpent", pet="snake", tools=("sed",), threat="Typo Serpent",
    task="The Typo Serpent scrambled letter.txt: \"the\" became \"teh\" in places.\n"
         "Fix the file in place (every occurrence, also \"Teh\"), then type: answer done",
    hints=["sed -i edits a file in place; s/old/new/g replaces every match on a line.",
           "Try: sed -i 's/teh/the/g; s/Teh/The/g' letter.txt"],
    setup=setup, verify=verify,
)
