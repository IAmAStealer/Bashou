import os
import random
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bashou import challenges, fight, state
from bashou.challenges import repos

# Reference solutions, run with bash in the arena folder. {x} is filled from the task text.
SOLUTIONS = {
    "line_moth": ("wc -l < notes.txt", None),
    "column_crab": ("cut -d, -f2 servers.csv | sed -n '{x}p'", r"on line (\d+)"),
    "jumble_sprite": ("sort names.txt | head -1", None),
    "last_word_wisp": ("tail -1 boot.log", None),
    "first_line_imp": ("head -{x} recipe.txt | tail -1", r"line (\d+)"),
    "needle_gnat": ("grep {x} contacts.txt | cut -d' ' -f2", r"What is (\w+)'s"),
    "field_wasp": ("awk '{{print $2}}' people.txt | sed -n '{x}p'", r"line (\d+)"),
    "dust_bunny": ("ls crates | grep '[.]key$'", None),
    "verse_viper": ("sed -n '{x}p' poem.txt", r"line (\d+)"),
    "peak_harpy": ("sort -n scores.txt | tail -1", None),
    "grep_hydra": ("grep -cF '[ERROR]' app.log", None),
    "awk_golem": ("awk -F, '$2 == \"{x}\" {{ s += $3 }} END {{ print s }}' sales.csv", r'for "(\w+)"'),
    "find_wraith": ("find maze -type f -name '*.bak' | wc -l", None),
    "uniq_swarm": ("sort visitors.txt | uniq -c | sort -rn | head -1 | awk '{{print $2}}'", None),
    "sed_serpent": ("sed -i 's/teh/the/g; s/Teh/The/g' letter.txt", None),
    "ps_phantom": ("pgrep -f '^{x}'", r"named (phantom-\w+)"),
    "pipe_eel": ("grep ' 404$' access.log | cut -d' ' -f1 | sort -u | wc -l", None),
    # code fights: fix the file, or a python3 one-liner
    "colon_cobra": ("sed -i 's/^def greet(names)$/def greet(names):/' greet.py", None),
    "semicolon_slug": ("sed -i 's/\")$/\");/' hello.c", None),
    "list_leech": ("sed -i 's/^    for i, host in enumerate(hosts):$/    return list(dict.fromkeys(hosts))\\n&/' hosts.py",
                   None),
    "dict_djinn": ("sed -i 's/counts\\[level\\] += 1/counts[level] = counts.get(level, 0) + 1/' tally.py", None),
    "loop_lich": ("sed -i 's/^        delay = delay \\* 2$/&\\n        i += 1/' retry.py", None),
    "ouroboros": ("sed -i 's/^            total(item)$/            size += total(item)/' du.py", None),
    "json_jinn": ("python3 -c \"import json; print(json.load(open('config.json'))['database']['port'])\"", None),
    "base64_banshee": ("python3 -c \"import base64; print(base64.b64decode(open('secret.txt').read()).split()[-1]"
                       ".decode())\"", None),
    "percent_poltergeist": ("python3 -c \"import re, urllib.parse as u; "
                            "print(re.search(r'etc/(\\w+)', u.unquote(open('access.log').read())).group(1))\"", None),
    "injection_imp": ("sed -i 's/os.system(\"echo checking \" + host)/print(\"checking\", host)/' check_hosts.py", None),
    "token_trickster": ("python3 -c \"import base64, json; p = open('token.txt').read().split('.')[1]; "
                        "print(json.loads(base64.urlsafe_b64decode(p + '=='))['sub'])\"", None),
    "leak_lurker": ("sed -i 's/^        fputs(loud, stdout);$/&\\n        free(loud);/' shout.c", None),
    "fencepost_fiend": ("sed -i 's/i <= count/i < count/' average.c", None),
    "stack_specter": ("sed -i 's/^    return n + sum_to(n - 1);$/    if (n <= 0)\\n        return 0;\\n&/' sum.c", None),
    "overflow_ogre": ("sed -i '/strcpy/d; s/, name);/, argv[1]);/' greet.c", None),
    # rust fights (rustc): fix the file
    "mut_marmot": ("sed -i 's/let errors = 0;/let mut errors = 0;/' counter.rs", None),
    "const_condor": ("sed -i 's/^const MAX_POINTS = /const MAX_POINTS: u32 = /' points.rs", None),
    "shadow_shade": ("sed -i 's/let mut guess = /let guess = /; s/^    guess = guess.trim/    let guess: u32 = guess.trim/'"
                     " guess.rs", None),
    "byte_basilisk": ("sed -i 's/let mut total: u8 = 0;/let mut total: u32 = 0;/; s/total += r;/total += r as u32;/'"
                      " temps.rs", None),
    # package fights (Debian here; Red Hat through a fake rpm, see PackageFightTest)
    "version_vole": ("dpkg-query -W -f '${{Version}}' {x}", r"version of (\S+) is installed"),
    "candidate_crow": ("apt-cache policy {x} | awk '/Candidate:/ {{print $2}}'", r"version of (\S+) would"),
    "stowaway_stoat": ("dpkg -S {x} | cut -d: -f1", r"put (\S+) on"),
    "autoremove_adder": ("apt-mark showmanual | grep -qx {x} && echo manual || echo auto", r"Is (\S+) marked"),
    "release_raven": ("rpm -q --qf '%{{VERSION}}-%{{RELEASE}}' {x}", r"version of (\S+) is installed"),
    "hitchhiker_hare": ("rpm -qf --qf '%{{NAME}}' {x}", r"put (\S+) on"),
    "census_centipede": ("rpm -qa | wc -l", None),
    # repository fights: write the right file back, or one dnf command limited to one repo
    "mirror_mimic": ("cat > debian.sources <<'X'\n" + repos.DEBIAN_OK + "X", None),
    "repo_revenant": ("cat > rocky.repo <<'X'\n" + repos.ROCKY_OK + "X", None),
    "enabled_ettin": ("dnf --disablerepo='*' --enablerepo={x} repolist", r"only the (\S+) repository"),
    # security
    "hidden_file": ("cat .[!.]*", None),
    "encoded_note": ("base64 -d note.txt | cut -d' ' -f2", None),
    "failed_logins": ("grep 'Failed password' auth.log | awk '{{print $(NF-3)}}' | sort | uniq -c | sort -rn"
                      " | head -1 | awk '{{print $2}}'", None),
    "recent_change": ("find site -type f -mmin -10", None),
    "cron_backdoor": ("grep -rh '| *sh' etc/cron.d | grep -oE 'https?://[^/]+' | cut -d/ -f3", None),
    "suid_file": ("find bin -perm -4000 -type f", None),
    # adventure chests
    "trial_dirs": ("mkdir -p {x}", r"folders (\S+)"),
    "trial_note": ("echo {x} > map.txt", r"the word (\w+)"),
    "trial_move": ("mv key.txt chest/", None),
    "trial_copy": ("cp -r scroll backup", None),
    "trial_rename": ("mv rusty_sword.txt shiny_sword.txt", None),
    "trial_clean": ("rm *.tmp", None),
    "trial_spell": ("chmod u+x spell.sh && ./spell.sh > /dev/null", None),
    "trial_link": ("ln -s camp/tent home", None),
    "trial_journal": ("echo rested >> journal.txt", None),
    "trial_gems": ("find cave -name '*.gem' | wc -l", None),
    "trial_loot": ("tar czf loot.tar.gz loot", None),
    "trial_letter": ("sed -i 's/dragon/friend/g' letter.txt", None),
    "trial_scrolls": ("grep -rl treasure library", None),
    "trial_awk_names": ("awk '{{print $1}}' people.txt > names.txt", None),
    "trial_awk_sum": ("awk '{{s += $2}} END {{print s}}' prices.txt", None),
    "trial_pipe_cities": ("awk '{{print $3}}' people.txt | sort -u | wc -l", None),
}


class ChallengeTest(unittest.TestCase):
    def test_every_challenge_has_a_solution(self):
        self.assertEqual(set(SOLUTIONS), set(challenges.BY_ID))

    def test_reference_solutions(self):
        for ch in challenges.ALL + challenges.SECURITY + challenges.TRIALS:
            if not ch.available():
                continue
            for seed in range(3):
                with self.subTest(ch.id, seed=seed), tempfile.TemporaryDirectory() as tmp:
                    work = Path(tmp)
                    meta = ch.setup(work, random.Random(seed))
                    try:
                        cmd, pattern = SOLUTIONS[ch.id]
                        if pattern:
                            cmd = cmd.format(x=re.search(pattern, ch.task_text(meta)).group(1))
                        else:
                            cmd = cmd.format()
                        out = subprocess.run(["bash", "-c", cmd], cwd=work, capture_output=True,
                                             text=True).stdout.strip()
                        self.assertTrue(ch.check(work, meta, out or "done"), f"{ch.id}: {out!r}")
                        self.assertFalse(ch.check(work, {**meta, "expected": "nope"}, "wrong")
                                         and ch.verify is None)
                    finally:
                        if ch.cleanup:
                            ch.cleanup(meta)

    def test_code_fights_start_broken(self):
        """The file as handed out must fail its own tests (else there is nothing to fix)."""
        for ch in challenges.code.ALL + challenges.rust.ALL:
            if ch.verify and ch.available():
                with self.subTest(ch.id), tempfile.TemporaryDirectory() as tmp:
                    meta = ch.setup(Path(tmp), random.Random(1))
                    self.assertFalse(ch.check(Path(tmp), meta, "done"))

    def test_the_pipe_eel_needs_a_real_pipeline(self):
        with tempfile.TemporaryDirectory() as base:
            ch = challenges.BY_ID["pipe_eel"]
            log = Path(base) / "log"
            log.write_text("0\t    1  grep 404 access.log | wc -l\n")          # only 2 commands
            self.assertFalse(fight.used_tool(base, ch))
            log.write_text(log.read_text() + "0\t    2  grep ' 404$' access.log | cut -d' ' -f1 | sort -u\n")
            self.assertTrue(fight.used_tool(base, ch))

    def test_the_tool_is_required(self):
        with tempfile.TemporaryDirectory() as base:
            ch = challenges.BY_ID["grep_hydra"]
            log = Path(base) / "log"
            log.write_text("0\t    1  cat app.log\n1\t    2  grep -c ERROR nope\n")
            self.assertFalse(fight.used_tool(base, ch))
            log.write_text(log.read_text() + "0\t    3  grep -c ERROR app.log | head\n")
            self.assertTrue(fight.used_tool(base, ch))


FAKE_RPM = r"""#!/bin/bash
qf=""; mode=""; args=()
while [ $# -gt 0 ]; do
  case $1 in --qf) qf=$2; shift ;; -q|-ql|-qf|-qa) mode=$1 ;; *) args+=("$1") ;; esac; shift
done
name=${args[0]}
nl() { [[ $qf == *'\n' ]] && echo; }
case $mode in
  -qa) printf 'bash-5.1.8-9.el9.x86_64\ncoreutils-8.32-35.el9.x86_64\nrpm-4.16.1.3-29.el9.x86_64\n' ;;
  -q) case $name in bash) v=5.1.8-9.el9 ;; coreutils) v=8.32-35.el9 ;; rpm) v=4.16.1.3-29.el9 ;;
        *) echo "package $name is not installed"; exit 1 ;; esac
      if [ -n "$qf" ]; then printf %s "$v"; nl; else echo "$name-$v.x86_64"; fi ;;
  -ql) [ "$name" = coreutils ] && echo /usr/bin/env ;;
  -qf) if [ "$name" = /usr/bin/env ]; then
         if [ -n "$qf" ]; then printf coreutils; nl; else echo coreutils-8.32-35.el9.x86_64; fi
       else echo "file $name is not owned by any package"; exit 1; fi ;;
esac
"""


class PackageFightTest(unittest.TestCase):
    def test_they_follow_the_distro(self):
        with mock.patch.object(challenges, "family", return_value=frozenset({"ubuntu", "debian"})):
            self.assertFalse(challenges.BY_ID["release_raven"].available())
        with mock.patch.object(challenges, "family", return_value=frozenset({"rocky", "rhel", "centos", "fedora"})):
            self.assertFalse(challenges.BY_ID["version_vole"].available())

    def test_os_release_family(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "os-release"
            path.write_text('NAME="Rocky Linux"\nID="rocky"\nID_LIKE="rhel centos fedora"\n')
            self.assertEqual(challenges.family.__wrapped__(str(path)), {"rocky", "rhel", "centos", "fedora"})
            self.assertEqual(challenges.family.__wrapped__(str(path) + "-missing"), frozenset())

    def test_red_hat_fights_with_a_fake_rpm(self):
        with tempfile.TemporaryDirectory() as bin_dir, tempfile.TemporaryDirectory() as tmp:
            fake = Path(bin_dir) / "rpm"
            fake.write_text(FAKE_RPM)
            fake.chmod(0o755)
            path = f"{bin_dir}:{os.environ['PATH']}"
            with mock.patch.dict(os.environ, {"PATH": path}), \
                    mock.patch.object(challenges, "family", return_value=frozenset({"rocky", "rhel"})):
                for cid in ("release_raven", "hitchhiker_hare", "census_centipede"):
                    ch = challenges.BY_ID[cid]
                    self.assertTrue(ch.available(), cid)
                    meta = ch.setup(Path(tmp), random.Random(0))
                    cmd, pattern = SOLUTIONS[cid]
                    x = re.search(pattern, ch.task_text(meta)).group(1) if pattern else ""
                    out = subprocess.run(["bash", "-c", cmd.format(x=x)], capture_output=True, text=True,
                                         env={**os.environ}).stdout.strip()
                    self.assertTrue(ch.check(Path(tmp), meta, out), f"{cid}: {out!r} {meta}")
                    self.assertFalse(ch.check(Path(tmp), meta, "nope"), cid)
                raven = challenges.BY_ID["release_raven"]
                meta = raven.setup(Path(tmp), random.Random(0))
                self.assertTrue(raven.check(Path(tmp), meta, subprocess.run(
                    ["rpm", "-q", meta["args"]["pkg"]], capture_output=True, text=True).stdout))  # full name too
                hare = challenges.BY_ID["hitchhiker_hare"]
                self.assertTrue(hare.check(Path(tmp), {"answer": "coreutils"}, "coreutils-8.32-35.el9.x86_64"))
                self.assertFalse(hare.check(Path(tmp), {"answer": "coreutils"}, "coreutils-extra"))


class ReviewTest(unittest.TestCase):
    """Owner: a beaten fight comes back after 1, 7 and 30 days; after the third review it is acquired."""

    def setUp(self):
        self.s = state.default()
        self.ch = challenges.BY_ID["line_moth"]

    def fight(self, day, won=True):
        return fight.after_fight(self.s, self.ch, won, today=day)

    def test_four_fights_then_acquired(self):
        self.assertIn("tomorrow", self.fight("2026-01-01"))
        self.s["challenges"].append(self.ch.id)                       # run() records the win
        self.assertEqual(self.s["reviews"]["line_moth"]["due"], "2026-01-02")
        self.assertEqual(fight.due(self.s, "2026-01-01"), [])
        self.assertEqual(fight.due(self.s, "2026-01-02"), [self.ch])
        self.assertIn("7 days", self.fight("2026-01-02"))
        self.assertEqual(self.s["reviews"]["line_moth"]["due"], "2026-01-09")
        self.assertIn("30 days", self.fight("2026-01-09"))
        self.assertEqual(self.s["reviews"]["line_moth"]["due"], "2026-02-08")
        self.assertIn("for good", self.fight("2026-02-08"))
        self.assertNotIn("line_moth", self.s["reviews"])
        self.assertIsNone(self.fight("2026-06-01"))                   # acquired: nothing more

    def test_a_lost_review_starts_over(self):
        self.fight("2026-01-01")
        self.s["challenges"].append(self.ch.id)
        self.fight("2026-01-02")                                       # review 1 won
        self.assertIn("start over", self.fight("2026-01-09", won=False))
        self.assertEqual(self.s["reviews"]["line_moth"], {"step": 0, "due": "2026-01-10"})

    def test_losing_a_new_fight_schedules_nothing(self):
        self.assertIsNone(self.fight("2026-01-01", won=False))
        self.assertEqual(self.s["reviews"], {})

    def test_due_reviews_come_as_threats_and_say_so(self):
        s = self.s
        s["challenges"] = [c.id for c in challenges.ALL]                # nothing new left
        s["reviews"] = {"line_moth": {"step": 1, "due": "2000-01-01"}}
        self.assertGreater(fight.threats_per_day(s), 0)                # reviews keep threats coming
        rng = ThreatTest.Always()
        fight.maybe_threat(s, rng, now=10_000_000_000)
        self.assertEqual((s["threat"]["challenge"], s["threat"]["review"]), ("line_moth", True))
        said = fight.announcement(s, now=10_000_000_000)
        self.assertIn("is back", said)
        banner = fight.banner(self.ch, "task", s["reviews"]["line_moth"])
        self.assertIn("Review 2/3", banner)
        self.assertNotIn("Review", fight.banner(self.ch, "task"))

    def test_old_wins_are_spread_over_the_next_days(self):
        old = {**state.default(), "challenges": ["line_moth", "grep_hydra", "awk_golem"]}
        del old["reviews"]
        s = state.migrate(old)
        days = sorted(r["due"] for r in s["reviews"].values())
        self.assertEqual(len(set(days)), 3)                            # one a day, not all at once
        self.assertTrue(all(r["step"] == 0 for r in s["reviews"].values()))


class LenientAnswerTest(unittest.TestCase):
    def test_the_same_answer_written_another_way(self):
        from bashou.challenges import code, packages
        self.assertTrue(code.url_verify(None, {"answer": "shadow"}, "/etc/shadow"))
        self.assertTrue(code.url_verify(None, {"answer": "shadow"}, "shadow"))
        self.assertFalse(code.url_verify(None, {"answer": "shadow"}, "passwd"))
        self.assertTrue(packages.same_version("bash 5.2.37-2+b9", "5.2.37-2+b9"))       # dpkg-query -W
        self.assertTrue(packages.same_version("4.0.4-9", "2:4.0.4-9"))
        self.assertFalse(packages.same_version("", "2:4.0.4-9"))


class RepoFightTest(unittest.TestCase):
    def test_planted_files_fail_and_fixed_ones_pass(self):
        for seed in range(20):
            with tempfile.TemporaryDirectory() as tmp:
                work, rng = Path(tmp), random.Random(seed)
                repos.debian_setup(work, rng)
                repos.rocky_setup(work, rng)
                self.assertFalse(repos.debian_verify(work, {}, "done"), (work / "debian.sources").read_text())
                self.assertFalse(repos.rocky_verify(work, {}, "done"), (work / "rocky.repo").read_text())
        for right, wrong in repos.DEBIAN_MISTAKES + repos.ROCKY_MISTAKES:     # each mistake alone breaks it
            with tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp)
                (work / "debian.sources").write_text(repos.DEBIAN_OK.replace(right, wrong, 1))
                (work / "rocky.repo").write_text(repos.ROCKY_OK.replace(right, wrong, 1))
                self.assertFalse(repos.debian_verify(work, {}, "") and repos.rocky_verify(work, {}, ""), wrong)

    def test_the_fix_is_read_by_meaning(self):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            (work / "debian.sources").write_text(
                repos.DEBIAN_OK.replace("https://deb.debian.org/debian", "http://deb.debian.org/debian/")
                .replace("trixie trixie-updates", "trixie trixie-updates trixie-backports")
                .replace("Components: main\nSigned", "Components: main contrib non-free-firmware\nSigned"))
            self.assertTrue(repos.debian_verify(work, {}, "done"))
            (work / "rocky.repo").write_text(repos.ROCKY_OK.replace(
                "baseurl=https://dl.rockylinux.org/pub/rocky/$releasever/BaseOS/$basearch/os/",
                "mirrorlist=https://mirrors.rockylinux.org/mirrorlist?arch=$basearch&repo=BaseOS-$releasever$rltype"))
            self.assertTrue(repos.rocky_verify(work, {}, "done"))

    def test_one_repository_per_command(self):
        cases = {"dnf --disablerepo='*' --enablerepo=epel search nginx": "epel",
                 "dnf --disablerepo '*' --enablerepo epel list": "epel",
                 "dnf --repo=crb repolist": "crb",
                 "dnf --enablerepo=epel --disablerepo='*' search x": None,      # the order matters
                 "dnf --enablerepo=epel search x": None,
                 "dnf --disablerepo='*' --enablerepo=epel,crb list": None}
        import shlex
        for cmd, want in cases.items():
            self.assertEqual(repos.only_repo(shlex.split(cmd)), want, cmd)
        with tempfile.TemporaryDirectory() as base:
            (Path(base) / "arena").mkdir()
            log = Path(base) / "log"
            log.write_text("0\t    1  dnf repolist\n1\t    2  sudo dnf --disablerepo='*' --enablerepo=epel list\n")
            meta = {"args": {"repo": "epel"}}
            self.assertFalse(repos.enabled_verify(Path(base) / "arena", meta, "done"))
            log.write_text(log.read_text() + "0\t    3  sudo dnf --disablerepo='*' --enablerepo=epel list\n")
            self.assertTrue(repos.enabled_verify(Path(base) / "arena", meta, "done"))

    def test_enabled_repos_are_read_from_the_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "rocky.repo").write_text("[baseos]\nenabled=1\n[crb]\nenabled=0\n[appstream]\nname=x\n")
            Path(tmp, "broken.repo").write_text("not a repo file")
            self.assertEqual(repos.enabled_repos(tmp), ["baseos", "appstream"])

    def test_the_named_editor_is_installed(self):
        import importlib
        with mock.patch("shutil.which", lambda e: "/usr/bin/vi" if e in ("vi", "sed") else None):
            self.assertEqual(importlib.reload(repos).EDITORS[0], "vi")
        importlib.reload(repos)

    def test_red_hat_file_fight(self):
        with mock.patch.object(challenges, "family", return_value=frozenset({"rocky", "rhel"})):
            self.assertTrue(challenges.BY_ID["repo_revenant"].available())
            self.assertFalse(challenges.BY_ID["mirror_mimic"].available())


class TrialTest(unittest.TestCase):
    def test_doing_nothing_fails(self):
        for ch in challenges.TRIALS:
            with tempfile.TemporaryDirectory() as tmp:
                meta = ch.setup(Path(tmp), random.Random(0))
                self.assertFalse(ch.check(Path(tmp), meta, ""), ch.id)

    def test_hints_show_the_real_names(self):
        ch = challenges.BY_ID["trial_dirs"]
        meta = ch.setup(Path("."), random.Random(0))
        self.assertIn(meta["args"]["path"], ch.hint_text(1, meta))
        awk = challenges.BY_ID["failed_logins"]
        self.assertIn("{print $(NF-3)}", awk.hint_text(1, {}))     # other braces untouched


class SecurityTest(unittest.TestCase):
    def test_the_busiest_ip_is_not_the_attacker(self):
        """Counting every line gives the admin's IP (successful logins): you have to filter first."""
        ch = challenges.BY_ID["failed_logins"]
        for seed in range(5):
            with tempfile.TemporaryDirectory() as tmp:
                meta = ch.setup(Path(tmp), random.Random(seed))
                cmd = "awk '{print $(NF-3)}' auth.log | sort | uniq -c | sort -rn | head -1 | awk '{print $2}'"
                out = subprocess.run(["bash", "-c", cmd], cwd=tmp, capture_output=True, text=True).stdout.strip()
                self.assertFalse(ch.check(Path(tmp), meta, out))

    def test_security_is_never_sent_as_a_threat(self):
        s = state.default()
        s["challenges"] = [c.id for c in challenges.ALL]
        self.assertIsNone(fight.maybe_threat(s, ThreatTest.Always(), 1_800_000_000))


class OrderTest(unittest.TestCase):
    """The Knot Eel came to a beginner: it needs pipes, uniq and more (owner's bug report)."""

    def test_beginners_get_level_1_fights_only(self):
        s = state.default()
        ready = {ch.id for ch in challenges.ALL if fight.ready(s, ch)}
        self.assertEqual(ready, {ch.id for ch in challenges.ALL if ch.level == 1})
        s["tools"]["grep"] = 1                                          # met grep, its fight can come
        self.assertTrue(fight.ready(s, challenges.BY_ID["grep_hydra"]))

    def test_harder_fights_after_their_tool_and_their_basics(self):
        s = state.default()
        s["tools"]["awk"] = 1
        self.assertFalse(fight.ready(s, challenges.BY_ID["awk_golem"]))        # grep fight first
        s["challenges"].append("grep_hydra")
        self.assertTrue(fight.ready(s, challenges.BY_ID["awk_golem"]))
        eel = challenges.BY_ID["pipe_eel"]
        s["challenges"].append("uniq_swarm")
        self.assertFalse(fight.ready(s, eel))                                  # never piped 3 commands
        s["adventure"] = {"lessons": ["pipes"]}                                # the owl's lesson counts
        self.assertTrue(fight.ready(s, eel))

    def test_each_tool_to_discover_once(self):
        """7 Python fights listed python3 7 times: the pets talked about nothing else."""
        tools = fight.to_discover(state.default())
        self.assertEqual(len(tools), len(set(tools)))

    def test_pets_hint_the_tool_before_its_fight(self):
        from bashou import dialogue
        s = state.default()
        s["challenges"] = ["grep_hydra", "find_wraith", "ps_phantom"]
        self.assertIn("awk", fight.to_discover(s))
        said = " ".join(dialogue.discover(s, random.Random(i)) or "" for i in range(30))
        self.assertIn("awk '{print $1}'", said)
        self.assertIn("adventure teaches it", said)


class ThreatTest(unittest.TestCase):
    class Always:
        def random(self):
            return 0.0

        def choice(self, pool):
            return pool[0]

    def test_threat_rules(self):
        s = state.default()
        now = 1_800_000_000
        note = fight.maybe_threat(s, self.Always(), now)
        self.assertIn("is coming", note)
        self.assertIsNotNone(fight.active_threat(s, now))
        # Only one at a time, and at least 2 h between two threats.
        self.assertIsNone(fight.maybe_threat(s, self.Always(), now + 60))
        self.assertIsNone(fight.maybe_threat(s, self.Always(), now + 3600))
        self.assertIsNone(fight.active_threat(s, now + 3600))    # it left after 10 min
        self.assertIsNotNone(fight.maybe_threat(s, self.Always(), now + 2 * 3600 + 1))

    def test_no_threat_when_bank_is_empty(self):
        s = state.default()
        s["challenges"] = [c.id for c in challenges.ALL]
        self.assertEqual(fight.threats_per_day(s), 0)
        self.assertIsNone(fight.maybe_threat(s, self.Always(), 1_800_000_000))

    def test_fewer_threats_at_higher_level(self):
        s = state.default()
        self.assertEqual(fight.threats_per_day(s), 3)
        s["pets"] = ["bat", "frog", "fox", "owl", "mole", "snake", "ghost", "ant", "turtle"]
        self.assertEqual(fight.threats_per_day(s), 1)


if __name__ == "__main__":
    unittest.main()
