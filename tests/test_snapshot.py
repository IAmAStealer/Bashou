"""What players see of pets, recorded once (tests/snapshot.json) so a refactor can't change it by accident.

The data moves into objects step by step (doc/PLAN.md): each step must give the same snapshot. A change
on purpose updates the file in the same commit, where its diff shows what moved:

    python3 -m tests.test_snapshot --write
"""

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

from bashou import achievements, creatures, i18n, progress, share, state

FILE = Path(__file__).resolve().parent / "snapshot.json"


def seen(s, who):
    """The form reached, its name and its stars (the starter shows its level instead)."""
    form = progress.reached(s, who)
    return [form, progress.sprite_of(s, who, form)[1], None if who == "starter" else progress.stars(s, who)]


def walks():
    """Every pet, the Slime and every starter line, step by step: what each step shows."""
    out = {}
    for pet in creatures.NAMES:
        s = state.default()
        s["starter"], s["pets"] = "star", [pet]
        steps = [seen(s, pet)]
        if pet in getattr(progress, "COMMAND_LADDER", {}) or pet == "slime":
            for n in (10, 100, 200, 500, 1500, 3500, 5000, 7500, 10000):
                s["commands"] = n
                progress.check(s)
                steps.append(seen(s, pet))
        else:
            for a in achievements.family(pet):
                progress.check(s, [a])
                steps.append(seen(s, pet))
        out[pet] = steps
    for line in creatures.STARTERS:
        s = state.default()
        s["starter"] = line
        steps = [seen(s, "starter")]
        for i in range(100):
            progress.check(s, [achievements.A(f"snap{i}", "cat", "", "")])
            steps.append(seen(s, "starter"))
        out["starter:" + line] = steps
    return out


def capture():
    with mock.patch("bashou.which.installed", return_value=True):
        return {"walks": walks(),
                "unlock_hints": {pet: progress.how_to_unlock(state.default(), pet) for pet in creatures.NAMES},
                "share_page": share.page_data(),
                "translated": sorted(set(i18n.messages()))}


class SnapshotTest(unittest.TestCase):
    maxDiff = 4000

    def test_players_see_the_same_pets(self):
        now, before = capture(), json.loads(FILE.read_text())
        for part in before:
            self.assertEqual(json.loads(json.dumps(now[part])), before[part],
                             f"{part} changed: on purpose? python3 -m tests.test_snapshot --write")


if __name__ == "__main__":
    if sys.argv[1:] == ["--write"]:
        FILE.write_text(json.dumps(capture(), ensure_ascii=False, indent=1) + "\n")
        print(f"wrote {FILE}")
    else:
        unittest.main()
