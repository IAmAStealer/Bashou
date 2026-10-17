"""`bashou export` / `bashou import`: one save on two computers, carried as a small text file (owner, 2026-10-16)."""

import base64
import copy
import hashlib
import io
import json
import os
import stat
import tempfile
import unittest
import zlib
from pathlib import Path

from bashou import achievements, creatures, lesson, progress, state, transfer
from bashou.adventure import world


def played():
    """A save that played a bit of everything: commands, a fight, a pony, lessons, the adventure."""
    s = state.default()
    s.update(starter="pebble", language="en")
    for line in ["grep -r todo ."] * 12 + ["find . -name '*.py'"] * 11 + ["ls"] * 40:
        progress.record(s, 0, line, "2026-10-16", 14)
    s["challenges"].append("line_moth")
    s["fights_won"] = 1
    progress.unlock(s, "sofa", "beat the Line moth")
    s["ponies"].append("pony_foal")
    s["lessons"]["read"] += ["command_line", "paths"]
    s["lessons"]["opened"] += ["command_line", "paths"]
    s["lessons"]["met"] += ["line_moth"]
    adv = world.new()
    adv.update(chapter=2, chapters_done=1, walked=640.0, correct=25, levels={"bash": 2, "linux": 1},
               seen=["bash-1-01"], distance=640.0)
    s["adventure"] = adv
    s["settings"] = {"pet_size": "small"} if "pet_size" in state.SETTINGS else {}
    s["today"] = {"date": "2026-10-16", "count": 63}
    s["update_checked"] = 1760000000
    progress.check(s)
    return s


def mangle(text):
    """What a mail client may do to a pasted block: quote it, rewrap the long lines, use CRLF, add words around."""
    lines = []
    for line in text.splitlines():
        lines += [line[:40], line[40:]] if len(line) > 40 and not line.startswith(("-----", "Check")) else [line]
    body = "\r\n".join("> " + line for line in lines if line)
    return "Hi me,\r\nhere is my save:\r\n\r\n" + body + "\r\n\r\n-- \r\nsent from my work computer\r\n"


def parts(text):
    """(version, mode, json bytes) of a block, without checking it: to forge broken ones in tests."""
    lines = [line.strip() for line in text.splitlines()]
    version = next(line.split(":", 1)[1].strip() for line in lines if line.startswith("Version:"))
    mode = next(line.split(":", 1)[1].strip() for line in lines if line.startswith("Mode:"))
    start, end = lines.index(transfer.BEGIN), lines.index(transfer.END)
    body = "".join(line for line in lines[start + 1:end] if ":" not in line)
    return version, mode, zlib.decompress(base64.b64decode(body))


def block(version, mode, raw, check=None):
    """A block built by hand, with a good check unless `check` is given."""
    body = base64.b64encode(zlib.compress(raw, 9)).decode()
    check = check or transfer.sign(version, mode, raw)
    return "\n".join([transfer.BEGIN, f"Version: {version}", f"Mode: {mode}",
                      *(body[i:i + 64] for i in range(0, len(body), 64)), transfer.END, f"Check: {check}"]) + "\n"


class BlockTest(unittest.TestCase):
    def test_round_trip_both_modes(self):
        s = played()
        for mode in ("minimal", "full"):
            data = transfer.decode(transfer.encode(s, mode))
            self.assertEqual(data, (mode, json.loads(json.dumps(transfer.payload(s, mode)))), mode)

    def test_the_block_looks_like_a_mail_safe_text(self):
        text = transfer.encode(played())
        lines = text.splitlines()
        self.assertEqual(lines[0], transfer.BEGIN)
        self.assertEqual(lines[1], f"Version: {state.SAVE_VERSION}")
        self.assertEqual(lines[2], "Mode: minimal")
        self.assertEqual(lines[-2], transfer.END)
        self.assertTrue(lines[-1].startswith("Check: "))
        for line in lines[3:-2]:
            self.assertLessEqual(len(line), 64)
            self.assertRegex(line, r"^[A-Za-z0-9+/=]+$")
        self.assertLess(len(text), 2000)                           # minimal stays small

    def test_minimal_holds_only_the_meta_progress(self):
        data = transfer.payload(played(), "minimal")
        self.assertEqual(set(data), {"achievements", "starter", "pets", "ponies", "lessons", "challenges", "adventure",
                                     "ladder_best", "starter_best"})
        self.assertEqual(set(data["lessons"]), {"read", "met", "passed"})
        self.assertLessEqual(set(data["adventure"]), {"levels", "chapters_done", "right"})
        text = json.dumps(data)
        for private in ("2026", "grep -r", "pet_size", "1760000000"):    # no dates, commands or settings
            self.assertNotIn(private, text)
        self.assertNotIn("mole", data["pets"])                     # its achievement brings it back
        self.assertIn("sofa", data["pets"])                        # won in a fight: no achievement brings it
        self.assertIn("pony_foal", data["ponies"])

    def test_full_leaves_this_computer_alone(self):
        data = transfer.payload(played(), "full")
        for field in transfer.LOCAL:
            self.assertNotIn(field, data)
        for field in ("settings", "today", "update_checked", "threat", "evolving"):
            self.assertIn(field, transfer.LOCAL)
        self.assertIn("commands", data)

    def test_a_mailed_block_still_reads(self):
        s = played()
        self.assertEqual(transfer.decode(mangle(transfer.encode(s)))[1], json.loads(json.dumps(transfer.payload(s))))

    def refused(self, text, why):
        with self.assertRaises(transfer.Refused) as caught:
            transfer.decode(text)
        self.assertEqual(caught.exception.why, why)
        self.assertTrue(str(caught.exception))                     # always says why, in words

    def test_a_check_made_without_the_salt_is_refused(self):
        version, mode, raw = parts(transfer.encode(played()))
        self.refused(block(version, mode, raw, hashlib.sha256(raw).hexdigest()), "check")

    def test_an_edited_save_with_its_old_check_is_refused(self):
        text = transfer.encode(played())
        version, mode, raw = parts(text)
        check = text.splitlines()[-1].split(":", 1)[1].strip()
        data = json.loads(raw)
        data["achievements"].append("tidal_wave")
        self.refused(block(version, mode, json.dumps(data).encode(), check), "check")

    def test_the_mode_line_is_checked_too(self):
        text = transfer.encode(played())
        self.refused(text.replace("Mode: minimal", "Mode: full"), "check")

    def test_broken_blocks_are_refused(self):
        text = transfer.encode(played())
        lines = text.splitlines()
        self.refused("hello", "format")
        self.refused("\n".join(lines[:-1]), "format")                       # no check line
        self.refused("\n".join(lines[:4] + lines[-2:]), "format")           # most of the body lost
        self.refused(text.replace(lines[3], lines[3][:-4]), "format")       # cut base64

    def test_a_huge_text_is_refused_before_reading(self):
        self.refused("x" * (transfer.MAX_TEXT + 1), "size")

    def test_a_zip_bomb_is_refused(self):
        raw = b'{"achievements": ["' + b"a" * (transfer.MAX_JSON * 4) + b'"]}'
        self.refused(block(str(state.SAVE_VERSION), "minimal", raw), "size")

    def test_only_the_same_save_version_comes_in(self):
        version, mode, raw = parts(transfer.encode(played()))
        older = block(str(state.SAVE_VERSION - 1), mode, raw)
        newer = block(str(state.SAVE_VERSION + 1), mode, raw)
        with self.assertRaises(transfer.Refused) as old:
            transfer.decode(older)
        with self.assertRaises(transfer.Refused) as new:
            transfer.decode(newer)
        self.assertEqual((old.exception.why, new.exception.why), ("older", "newer"))
        self.assertIn("export", str(old.exception))                # update over there, then export again
        self.assertNotEqual(str(old.exception), str(new.exception))

    def test_unknown_fields_and_bad_types_are_refused(self):
        version, mode, raw = parts(transfer.encode(played()))
        data = json.loads(raw)
        for bad in ({**data, "commands": 99999}, {**data, "achievements": "all"},
                    {**data, "lessons": {"read": [1, 2]}}, {**data, "adventure": {"levels": {"bash": "x"}}},
                    {**data, "adventure": {"position": 3}}, ["not", "a", "save"]):
            self.refused(block(version, mode, json.dumps(bad).encode()), "field")
        self.refused(block(version, "everything", raw), "format")

    def test_unknown_ids_are_dropped_not_kept(self):
        version, mode, raw = parts(transfer.encode(played()))
        data = json.loads(raw)
        data["achievements"].append("made_up")
        data["pets"].append("unicorn")
        _mode, got = transfer.decode(block(version, mode, json.dumps(data).encode()))
        merged = transfer.merge(state.default(), got, "minimal")
        self.assertNotIn("made_up", merged["achievements"])
        self.assertNotIn("unicorn", merged["pets"])


def forms(s):
    return {pet: progress.reached(s, pet) for pet in s["pets"]}


class MergeTest(unittest.TestCase):
    def setUp(self):
        self.source = played()

    def imported(self, local=None, mode="minimal"):
        local = state.default() if local is None else local
        self.got = transfer.decode(transfer.encode(self.source, mode))[1]
        return transfer.merge(local, self.got, mode)

    def test_an_empty_save_gets_the_whole_progress_back(self):
        s = self.imported()
        self.assertEqual(s["starter"], "pebble")
        self.assertEqual(set(s["pets"]), set(self.source["pets"]))
        self.assertEqual(forms(s), forms(self.source))
        self.assertEqual(progress.starter_level(s), progress.starter_level(self.source))
        self.assertEqual(set(s["achievements"]), set(self.source["achievements"]))
        self.assertIn("pony_foal", s["ponies"])
        passed = [le["id"] for le in lesson.load() if lesson.mastered(self.source, le)]
        self.assertTrue(passed)
        self.assertEqual([le["id"] for le in lesson.load() if lesson.mastered(s, le)], passed)
        self.assertEqual(s["adventure"]["chapters_done"], 1)
        self.assertEqual(s["adventure"]["levels"], {"bash": 2, "linux": 1})

    def test_forms_kept_from_older_rules_come_too(self):
        self.source["ladder_best"]["bat"] = creatures.forms("bat")[-1]      # reached before families changed
        self.source["pets"].append("bat") if "bat" not in self.source["pets"] else None
        s = self.imported()
        self.assertEqual(progress.reached(s, "bat"), len(creatures.forms("bat")))
        local = state.default()
        local.update(starter="pebble", pets=["bat"], ladder_best={"bat": creatures.forms("bat")[-1]})
        self.source["ladder_best"]["bat"] = creatures.forms("bat")[0]
        self.assertEqual(self.imported(local)["ladder_best"]["bat"], creatures.forms("bat")[-1])   # the higher stays

    def test_counters_are_rebuilt_from_achievements(self):
        s = self.imported()
        self.assertGreaterEqual(s["tools"].get("grep", 0), 10)    # Burrower: grep 10 times
        self.assertGreaterEqual(s["commands"], 50)                # Puddle: 50 commands
        self.assertGreaterEqual(s["adventure"]["walked"], 500)    # Wanderer: 500 m
        self.assertGreaterEqual(s["fights_won"], len(s["challenges"]))
        burrower = achievements.BY_ID["burrower"]
        self.assertEqual(burrower.where(s), "10/10")

    def test_every_count_achievement_rebuilds_its_counter(self):
        for a in achievements.ALL:
            if not a.floor:
                continue
            s = state.default()
            s["achievements"] = [a.id]
            transfer.rebuild(s)
            self.assertTrue(a.state(s), a.id)

    def test_count_achievements_without_a_floor_are_known(self):
        floorless = {a.id for a in achievements.ALL if a.progress and not a.floor}
        self.assertEqual(floorless, transfer.NO_FLOOR)

    def test_the_highest_value_stays(self):
        local = state.default()
        local.update(starter="pebble", commands=5000, tools={"grep": 400})
        local["achievements"] = ["burrower", "miner"]
        s = self.imported(local)
        self.assertEqual(s["commands"], 5000)
        self.assertEqual(s["tools"]["grep"], 400)

    def test_lists_are_joined_local_first(self):
        local = state.default()
        local.update(starter="pebble", achievements=["night_owl"], challenges=["space_sprite"])
        s = self.imported(local)
        self.assertEqual(s["achievements"][0], "night_owl")
        self.assertEqual(s["challenges"][:2], ["space_sprite", "line_moth"])
        self.assertEqual(len(s["achievements"]), len(set(s["achievements"])))

    def test_adventure_levels_keep_the_best_per_topic(self):
        local = state.default()
        local["adventure"] = {**world.new(), "levels": {"bash": 1, "linux": 3, "sql": 1}}
        s = self.imported(local)
        self.assertEqual(s["adventure"]["levels"], {"bash": 2, "linux": 3, "sql": 1})

    def test_the_road_moves_to_the_next_chapter_when_the_import_is_ahead(self):
        local = state.default()
        local["adventure"] = {**world.new(), "chapter": 1, "leg": 1, "hearts": 1, "distance": 90.0, "topic": "bash"}
        adv = self.imported(local)["adventure"]
        self.assertEqual((adv["chapter"], adv["leg"], adv["hearts"], adv["topic"]), (2, 0, world.HEARTS, None))
        self.assertEqual(adv["phase"], "intro")

    def test_the_road_stays_when_this_computer_is_ahead(self):
        local = state.default()
        local["adventure"] = {**world.new(), "chapter": 4, "leg": 2, "chapters_done": 3, "distance": 2000.0}
        adv = self.imported(local)["adventure"]
        self.assertEqual((adv["chapter"], adv["leg"], adv["chapters_done"]), (4, 2, 3))

    def test_the_local_starter_stays(self):
        local = state.default()
        local["starter"] = "star"
        s = self.imported(local)
        self.assertEqual(s["starter"], "star")
        self.assertTrue(any("starter" in line.lower() for line in transfer.summary(local, s, self.got)))

    def test_this_computers_own_things_stay(self):
        local = state.default()
        local.update(starter="pebble", active="starter", share_name="me", language="fr", settings={"os": "linux"},
                     looks={"starter": "pebble"})
        local["lessons"]["page"] = {"paths": 2}
        for mode in ("minimal", "full"):
            s = self.imported(copy.deepcopy(local), mode)
            for field in ("active", "share_name", "language", "settings", "looks"):
                self.assertEqual(s[field], local[field], (mode, field))
            self.assertEqual(s["lessons"]["page"], {"paths": 2})
            self.assertEqual(s["evolving"], [])                   # no evolution queue from an import

    def test_full_mode_brings_counters_and_days(self):
        local = state.default()
        local.update(starter="pebble", commands=10, days=["2026-10-01"])
        s = self.imported(local, "full")
        self.assertEqual(s["commands"], self.source["commands"])
        self.assertEqual(s["days"], ["2026-10-01", "2026-10-16"])
        self.assertEqual(s["adventure"]["walked"], 640.0)
        self.assertEqual(s["today"], local["today"])

    def test_full_mode_takes_the_road_from_the_save_further_on(self):
        local = state.default()
        local["adventure"] = {**world.new(), "chapter": 2, "leg": 2, "distance": 900.0, "hearts": 1, "chapters_done": 1}
        adv = self.imported(local, "full")["adventure"]
        self.assertEqual((adv["chapter"], adv["leg"], adv["distance"], adv["hearts"]), (2, 2, 900.0, 1))

    def test_the_summary_tells_a_full_import_brings_counts(self):
        once = self.imported()
        s = self.imported(copy.deepcopy(once), "full")
        self.assertTrue(transfer.summary(once, s, self.got))

    def test_importing_twice_changes_nothing(self):
        once = self.imported()
        got = transfer.decode(transfer.encode(self.source))[1]
        self.assertEqual(transfer.merge(copy.deepcopy(once), got, "minimal"), once)

    def test_merge_leaves_its_inputs_alone(self):
        local = state.default()
        before = copy.deepcopy(local)
        self.imported(local)
        self.assertEqual(local, before)

    def test_the_summary_says_what_comes(self):
        lines = transfer.summary(state.default(), self.imported(), self.got)
        text = "\n".join(lines)
        self.assertIn("achievements", text)
        self.assertIn("pets", text)
        self.assertEqual(transfer.summary(self.imported(), self.imported(), self.got), [])


class FilesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.saved = state.DATA, state.STATE, state.CACHE
        state.DATA = Path(self.tmp.name) / "data"
        state.STATE = state.DATA / "state.json"
        state.CACHE = state.DATA / "cache"
        self.here = Path(self.tmp.name) / "here"
        self.here.mkdir()

    def tearDown(self):
        state.DATA, state.STATE, state.CACHE = self.saved
        self.tmp.cleanup()

    def test_export_writes_a_private_file_here_and_never_overwrites(self):
        s = played()
        first = transfer.write(s, "minimal", self.here, "2026-10-16")
        second = transfer.write(s, "minimal", self.here, "2026-10-16")
        full = transfer.write(s, "full", self.here, "2026-10-16")
        self.assertEqual(first.name, "bashou-save-2026-10-16.txt")
        self.assertEqual(second.name, "bashou-save-2026-10-16-2.txt")
        self.assertEqual(full.name, "bashou-save-full-2026-10-16.txt")
        self.assertEqual(stat.S_IMODE(first.stat().st_mode), 0o600)
        self.assertEqual(transfer.decode(first.read_text())[0], "minimal")

    def test_import_asks_backs_up_and_saves(self):
        path = transfer.write(played(), "minimal", self.here, "2026-10-16")
        state.save(state.default())
        out = io.StringIO()
        self.assertEqual(transfer.load(path.read_text(), ask=lambda _q: "y", out=out), 0)
        self.assertIn("mole", state.load()["pets"])
        self.assertTrue(list(state.DATA.glob("state.json.bak-*")))

    def test_saying_no_changes_nothing(self):
        path = transfer.write(played(), "minimal", self.here, "2026-10-16")
        state.save(state.default())
        before = state.STATE.read_text()
        self.assertEqual(transfer.load(path.read_text(), ask=lambda _q: "n", out=io.StringIO()), 1)
        self.assertEqual(state.STATE.read_text(), before)

    def test_a_refused_block_changes_nothing(self):
        state.save(state.default())
        before = state.STATE.read_text()
        out = io.StringIO()
        self.assertEqual(transfer.load("nothing here", ask=lambda _q: "y", out=out), 1)
        self.assertEqual(state.STATE.read_text(), before)
        self.assertTrue(out.getvalue().strip())

    def test_nothing_new_says_so_without_asking(self):
        s = played()
        state.save(s)
        path = transfer.write(s, "minimal", self.here, "2026-10-16")
        asked = []
        self.assertEqual(transfer.load(path.read_text(), ask=asked.append, out=io.StringIO()), 0)
        self.assertEqual(asked, [])


if __name__ == "__main__":
    unittest.main()
