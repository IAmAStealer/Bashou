import contextlib
import io
import os
import random
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bashou import challenges, fight, state
from bashou.challenges import cicd, repos, secrets, sql

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
    # building and debugging C (gdb ones run where gdb is installed: see the Debian check in the journal)
    "linker_lynx": ("gcc report.c stats.c -o report", None),
    "warning_wraith": ("sed -i 's/score = 100/score == 100/' grade.c", None),
    "segfault_salamander": ("gcc -g crash.c -o crash && gdb -q -batch -ex run -ex bt ./crash 2>&1"
                            " | grep -o 'crash.c:[0-9]*' | head -1 | cut -d: -f2", None),
    "breakpoint_beetle": ("gcc -g loan.c -o loan && gdb -q -batch -ex 'break month_end if month == {x}' -ex run"
                          " -ex 'print balance' ./loan 2>/dev/null | sed -n 's/^[$]1 = //p'", r"for month (\d+)"),
    "trial_gdb_line": ("gcc -g count.c -o count && gdb -q -batch -ex run -ex bt ./count 2>&1"
                       " | grep -o 'count.c:[0-9]*' | head -1 | cut -d: -f2", None),
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
    "indent_imp": ("cat > .github/workflows/ci.yml <<'X'\n" + cicd.GH_OK.replace("{", "{{").replace("}", "}}") + "X", None),
    "trial_ci_indent": ("cat > .github/workflows/ci.yml <<'X'\n" + cicd.GH_OK.replace("{", "{{").replace("}", "}}") + "X", None),
    "stage_specter": ("sed -i 's/^  stage: [a-z-]*$/&/; /^unit:/,/^$/s/stage: .*/stage: test/' .gitlab-ci.yml", None),
    "secret_sprite": ("sed -i 's/API_TOKEN: ghp_.*/API_TOKEN: ${{{{ secrets.API_TOKEN }}}}/' .github/workflows/ci.yml", None),
    "needs_newt": ("sed -i \"/^  deploy:/a\\    needs: test\\n    if: github.ref == 'refs/heads/main'\" .github/workflows/ci.yml", None),
    "manual_mole": ("printf '%s\\n' '  rules:' '    - if: $CI_COMMIT_BRANCH == \"main\"' '      when: manual' >> .gitlab-ci.yml", None),
    # SQL fights: the sqlite3 command line (CI has it)
    "query_quokka": ("sqlite3 shop.db 'SELECT COUNT(*) FROM products WHERE price > {x};'", r"more than (\d+)"),
    "join_jackal": ("sqlite3 shop.db \"SELECT SUM(total) FROM orders JOIN customers ON orders.customer_id = customers.id "
                    "WHERE customers.name = '{x}';\"", r"did (\w+) spend"),
    "table_troll": ("f=$(ls ../*.db 2>/dev/null); sqlite3 \"$(sed -n 's/.*database \\(\\S*\\) with.*/\\1/p' <<< '{x}')\" "
                    "\"CREATE TABLE $(sed -n 's/.*a table \\([a-z]*\\):.*/\\1/p' <<< '{x}') "
                    "($(sed -n 's/.*a column \\([a-z]*\\) that holds text.*/\\1/p' <<< '{x}') TEXT, "
                    "$(sed -n 's/.*a column \\([a-z]*\\) that holds whole.*/\\1/p' <<< '{x}') INTEGER);\"", r"(Create the database .*)"),
    "insert_imp": ("x=$(tr '\\n' ' ' <<< '{x}'); sqlite3 shop.db \"INSERT INTO products (name, price, stock) VALUES "
                   "($(sed -E \"s/the (\\w+) is missing.*price ([0-9]+), stock ([0-9]+).*/'\\1', \\2, \\3/\" <<< \"$x\"));\"",
                   r"(?s)(the \w+ is missing.*?stock \d+)"),
    "update_urchin": ("sqlite3 shop.db \"UPDATE products SET price = $(sed -E 's/.*to ([0-9]+).*/\\1/' <<< '{x}') "
                      "WHERE name = '$(sed -E 's/.*price of (\\w+) .*/\\1/' <<< '{x}')';\"", r"(Set the price of \w+ to \d+)"),
    "upsert_unicorn": ("printf \"INSERT INTO stock (item, qty) VALUES ('%s', %s) ON CONFLICT(item) DO UPDATE SET qty = qty + excluded.qty;\" "
                       "$(sed -E 's/([0-9]+) × (\\w+).*/\\2 \\1/' <<< '{x}') > restock.sql", r"(\d+ × \w+)"),
    "trial_sql_loot": ("sqlite3 loot.db \"SELECT COUNT(*) FROM loot WHERE rarity = 'rare';\"", None),
    # gpg and pass (run with a throwaway GNUPGHOME, or the fight's practice one: never your own keys)
    "plaintext_pixie": ("gpg --batch --pinentry-mode loopback --passphrase {x} -c secrets.txt && rm secrets.txt",
                        r"passphrase (\S+), then"),
    "cipher_crow": ("gpg --batch --pinentry-mode loopback --passphrase {x} -d message.txt.gpg | sed -n 's/.*code is \\(.*\\)\\./\\1/p'",
                    r"passphrase (\S+)\."),
    "trial_gpg_note": ("gpg --batch --pinentry-mode loopback --passphrase {x} -d note.txt.gpg | sed -n 's/.*code is \\(.*\\)\\./\\1/p'",
                       r"passphrase (\S+)\."),
    "forger_ferret": ("for m in mirror1 mirror2; do gpgv --keyring ./vendor.gpg $m/tool-1.4.tar.gz.sig $m/tool-1.4.tar.gz "
                      "2>/dev/null && echo $m; done", None),
    "vault_vole": ("pass show backup/server", None),
    "cleartext_cricket": ("sed -i 's|^DB_PASSWORD=.*|DB_PASSWORD=\"$(pass show db/prod)\"|' deploy.sh", None),
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
    "trial_sort_scores": ("sort -n scores.txt | tail -1", None),
    "trial_sort_visitors": ("sort visitors.txt | uniq -c | sort -rn | head -1 | awk '{{print $2}}'", None),
}


class ChallengeTest(unittest.TestCase):
    def test_every_challenge_has_a_solution(self):
        self.assertEqual(set(SOLUTIONS), set(challenges.BY_ID))

    def test_reference_solutions(self):
        for ch in challenges.ALL + challenges.SECURITY + challenges.TRIALS:
            if not ch.available():
                continue
            for seed in range(3):
                with self.subTest(ch.id, seed=seed), tempfile.TemporaryDirectory() as tmp, \
                        tempfile.TemporaryDirectory() as gnupg:
                    work = Path(tmp) / "arena"                  # like the arena: the log lives next to it
                    work.mkdir()
                    meta = ch.setup(work, random.Random(seed))
                    env = {**os.environ, "GNUPGHOME": gnupg, **meta.get("env", {})}
                    try:
                        cmd, pattern = SOLUTIONS[ch.id]
                        if pattern:
                            cmd = cmd.format(x=re.search(pattern, ch.task_text(meta)).group(1))
                        else:
                            cmd = cmd.format()
                        done = subprocess.run(["bash", "-c", cmd], cwd=work, capture_output=True, text=True, env=env)
                        out = done.stdout.strip()
                        (work.parent / "log").write_text(f"{done.returncode}\t    1  {cmd}\n")   # as the arena logs it
                        self.assertTrue(ch.check(work, meta, out or "done"), f"{ch.id}: {out!r}")
                        self.assertFalse(ch.check(work, {**meta, "expected": "nope"}, "wrong")
                                         and ch.verify is None)
                    finally:
                        if ch.cleanup:
                            ch.cleanup(meta)
                        secrets.stop_agent(gnupg)

    def test_code_fights_start_broken(self):
        """The file as handed out must fail its own tests (else there is nothing to fix)."""
        for ch in challenges.code.ALL + challenges.debug.ALL + challenges.rust.ALL:
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


class CicdFightTest(unittest.TestCase):
    """CI/CD fights read the fix by meaning: other valid ways of writing it win too."""

    def fixed(self, fight, text):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            ch = challenges.BY_ID[fight]
            meta = ch.setup(work, random.Random(0))
            name = cicd.GITLAB if (work / cicd.GITLAB).exists() else cicd.WORKFLOW
            (work / name).write_text(text(( work / name).read_text(), meta))
            return ch.check(work, meta, "done")

    def test_every_planted_indent_mistake_breaks_the_file(self):
        for right, wrong in cicd.INDENT_MISTAKES:
            with tempfile.TemporaryDirectory() as tmp:
                cicd.write(Path(tmp), cicd.WORKFLOW, cicd.GH_OK.replace(right, wrong, 1))
                self.assertFalse(cicd.indent_verify(Path(tmp), {}, ""), wrong)
        self.assertRaises(ValueError, cicd.load, cicd.GH_OK.replace("    runs-on", "\trunt-on"))

    def test_needs_and_if_in_other_forms(self):
        add = lambda extra: lambda text, meta: text.replace("  deploy:\n", "  deploy:\n" + extra)
        self.assertTrue(self.fixed("needs_newt", add("    needs: [test]\n    if: github.ref_name == 'main'\n")))
        self.assertTrue(self.fixed("needs_newt", add("    needs:\n      - test\n    if: ${{ github.ref == \"refs/heads/main\" }}\n")))
        self.assertFalse(self.fixed("needs_newt", add("    needs: test\n")))                # still every branch
        self.assertFalse(self.fixed("needs_newt", add("    if: github.ref == 'refs/heads/main'\n")))

    def test_manual_in_other_forms(self):
        add = lambda extra: lambda text, meta: text + extra
        self.assertTrue(self.fixed("manual_mole", add("  rules:\n    - if: '$CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH'\n      when: manual\n")))
        self.assertTrue(self.fixed("manual_mole", add("  only:\n    - main\n  when: manual\n")))
        self.assertFalse(self.fixed("manual_mole", add("  when: manual\n")))                      # every branch
        self.assertFalse(self.fixed("manual_mole", add("  rules:\n    - if: $CI_COMMIT_BRANCH == \"main\"\n      when: manual\n    - when: on_success\n")))
        self.assertFalse(self.fixed("manual_mole", add("  when: manual\n  rules:\n    - if: $CI_COMMIT_BRANCH == \"main\"\n")))

    def test_secret_needs_the_secrets_context_and_the_token_gone(self):
        swap = lambda new: lambda text, meta: text.replace(meta["token"], new)
        self.assertTrue(self.fixed("secret_sprite", swap("${{secrets.API_TOKEN}}")))
        self.assertFalse(self.fixed("secret_sprite", swap("$API_TOKEN")))
        self.assertFalse(self.fixed("secret_sprite", lambda text, meta: text + "# old: " + meta["token"] + "\n"))


@unittest.skipUnless(shutil.which("gpg") and shutil.which("gpgconf"), "needs gpg")
class SecretsFightTest(unittest.TestCase):
    """gpg and pass fights: they start unsolved, cheats lose, and Bashou's own gpg never uses ~/.gnupg."""

    def setup(self, fight, seed=0):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        ch = challenges.BY_ID[fight]
        meta = ch.setup(Path(tmp.name), random.Random(seed))
        if ch.cleanup:
            self.addCleanup(ch.cleanup, meta)
        return ch, Path(tmp.name), meta

    def test_the_clear_file_must_go_and_the_passphrase_must_open_it(self):
        ch, work, meta = self.setup("plaintext_pixie")
        self.assertFalse(ch.check(work, meta, "done"))
        secrets.lock(work / "secrets.txt", work / "secrets.txt.gpg", "not-the-one")
        (work / "secrets.txt").unlink()
        self.assertFalse(ch.check(work, meta, "done"))                     # another passphrase
        (work / "secrets.txt").write_text(meta["secret"])
        secrets.lock(work / "secrets.txt", work / "secrets.txt.gpg", meta["args"]["pw"])
        self.assertFalse(ch.check(work, meta, "done"))                     # the clear copy is still there
        (work / "secrets.txt").unlink()
        self.assertTrue(ch.check(work, meta, "done"))

    def test_the_forged_download_fails_its_signature(self):
        ch, work, meta = self.setup("forger_ferret", seed=4)
        results = {m: subprocess.run(["gpgv", "--keyring", "./vendor.gpg", f"{m}/{secrets.RELEASE}.sig",
                                      f"{m}/{secrets.RELEASE}"], cwd=work, capture_output=True).returncode
                   for m in ("mirror1", "mirror2")}
        self.assertEqual(results[meta["answer"]], 0)
        self.assertNotEqual(results["mirror1" if meta["answer"] == "mirror2" else "mirror2"], 0)

    @unittest.skipUnless(shutil.which("pass"), "needs pass")
    def test_the_script_must_read_the_store(self):
        ch, work, meta = self.setup("cleartext_cricket")
        self.assertFalse(ch.check(work, meta, "done"))                     # the password is in clear
        script = work / "deploy.sh"
        original = script.read_text()
        script.write_text(original.replace(meta["pw"], "wrong"))
        self.assertFalse(ch.check(work, meta, "done"))                     # gone, but no login
        script.write_text(original.replace(f'"{meta["pw"]}"', '"$(pass show db/prod)"'))
        self.assertTrue(ch.check(work, meta, "done"))
        self.assertIn("login ok", subprocess.run(["bash", "deploy.sh"], cwd=work, capture_output=True, text=True,
                                                 env={**os.environ, **meta["env"]}).stdout)

    def test_bashou_never_touches_your_keys(self):
        with tempfile.TemporaryDirectory() as home:
            with mock.patch.dict(os.environ, {"GNUPGHOME": home + "/mine", "HOME": home}):
                for fight in ("plaintext_pixie", "cipher_crow", "forger_ferret"):
                    ch, work, meta = self.setup(fight)
                    ch.check(work, meta, "done")
            self.assertEqual(sorted(os.listdir(home)), [])


class SqlFightTest(unittest.TestCase):
    """The SQL fights, played with Python's sqlite3 (the sqlite3 command may be missing here)."""

    def play(self, fight, sql_text=None, seed=0):
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            ch = challenges.BY_ID[fight]
            meta = ch.setup(work, random.Random(seed))
            start = ch.check(work, meta, meta.get("answer", "done") if ch.verify is None else "done")
            if sql_text:
                if fight == "upsert_unicorn":
                    (work / sql.UPSERT_FILE).write_text(sql_text(meta["args"]))
                else:
                    import sqlite3
                    db = sqlite3.connect(work / (meta["args"].get("db") or "shop.db"))
                    db.executescript(sql_text(meta["args"]))
                    db.commit()
                    db.close()
            return start, ch.check(work, meta, meta.get("answer", "done") if ch.verify is None else "done")

    def test_fix_fights_start_broken_and_the_right_sql_wins(self):
        for seed in range(5):
            self.assertEqual(self.play("table_troll", lambda a: f"CREATE TABLE {a['table']} ({a['text']} VARCHAR(80), "
                                                                 f"{a['number']} INT);", seed), (False, True))
            self.assertEqual(self.play("insert_imp", lambda a: f"INSERT INTO products (name, price, stock) VALUES "
                                                                f"('{a['item']}', {a['price']}, {a['stock']});", seed), (False, True))
            self.assertEqual(self.play("update_urchin", lambda a: f"UPDATE products SET price = {a['price']} "
                                                                   f"WHERE name = '{a['item']}';", seed), (False, True))
            self.assertEqual(self.play("upsert_unicorn", lambda a: f"INSERT INTO stock (item, qty) VALUES ('{a['item']}', "
                                       f"{a['n']}) ON CONFLICT(item) DO UPDATE SET qty = qty + excluded.qty;", seed), (False, True))

    def test_wrong_sql_loses(self):
        self.assertFalse(self.play("table_troll", lambda a: f"CREATE TABLE {a['table']} ({a['text']} INTEGER, {a['number']} TEXT);")[1])
        self.assertFalse(self.play("update_urchin", lambda a: f"UPDATE products SET price = {a['price']};")[1])   # no WHERE
        self.assertFalse(self.play("insert_imp", lambda a: f"INSERT INTO products (name, price) VALUES ('{a['item']}', {a['price']});")[1])
        self.assertFalse(self.play("upsert_unicorn", lambda a: f"INSERT OR REPLACE INTO stock (item, qty) VALUES "
                                                               f"('{a['item']}', {a['n']});")[1])        # the old qty is lost

    def test_the_players_sql_cannot_reach_other_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            for evil in (f"VACUUM INTO '{tmp}/copy.db';", f"ATTACH '{tmp}/other.db' AS o; CREATE TABLE o.t (a);",
                         "CREATE TABLE extra (a);", "PRAGMA journal_mode = OFF;"):
                self.assertFalse(self.play("upsert_unicorn", lambda a: evil)[1], evil)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_answers_come_from_the_database(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            meta = challenges.BY_ID["join_jackal"].setup(work, random.Random(3))
            db = sqlite3.connect(work / "shop.db")
            total, = db.execute("SELECT SUM(total) FROM orders JOIN customers ON orders.customer_id = customers.id "
                                "WHERE customers.name = ?", (meta["args"]["name"],)).fetchone()
            self.assertEqual(meta["answer"], str(total))


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
            if not ch.available():               # the gpg chest can't even be set up without gpg
                continue
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
        self.assertEqual(ready, {ch.id for ch in challenges.ALL if ch.level == 1 and not ch.after})
        self.assertIn("semicolon_slug", challenges.BY_ID["linker_lynx"].after)   # level 1, after the first C fight
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


class FixFightTest(unittest.TestCase):
    """Players typed their command after `answer` in fights where they fix a file (owner)."""

    def test_every_answer_done_fight_is_flagged(self):
        for ch in challenges.ALL:
            with self.subTest(ch.id):
                self.assertEqual(ch.fix, "verify" in ch.task, ch.id)

    def test_banner_explains_answer_done(self):
        ch = challenges.BY_ID["colon_cobra"]
        banner = fight.banner(ch, "task")
        self.assertIn("verify", banner)
        self.assertNotIn("answer <value>", banner)
        self.assertIn("answer <value>", fight.banner(challenges.BY_ID["line_moth"], "task"))

    def test_a_command_after_answer_is_explained_not_judged(self):
        base = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, base)
        (base / "arena").mkdir()
        (base / "meta.json").write_text('{"challenge": "colon_cobra"}')
        out = io.StringIO()
        with contextlib.redirect_stdout(out), mock.patch.object(challenges.Challenge, "check") as check:
            self.assertEqual(fight.cmd_answer(str(base), "python3 greet.py"), 1)
        check.assert_not_called()
        self.assertIn("run `python3 greet.py` at the prompt", out.getvalue())

    def test_verify_strikes_fix_fights_only(self):
        base = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, base)
        (base / "arena").mkdir()
        (base / "meta.json").write_text('{"challenge": "line_moth", "answer": 3}')
        with contextlib.redirect_stdout(io.StringIO()) as out:
            self.assertEqual(fight.cmd_verify(str(base)), 1)
        self.assertIn("answer <value>", out.getvalue())
        (base / "meta.json").write_text('{"challenge": "colon_cobra"}')
        with mock.patch.object(challenges.Challenge, "check", return_value=True) as check, \
                mock.patch.object(fight, "used_tool", return_value=True):
            self.assertEqual(fight.cmd_verify(str(base)), 0)
        self.assertEqual(check.call_args.args[2], "done")


class UniqTipTest(unittest.TestCase):
    """Bug report: `cut … | uniq -c` counted the same city several times; nothing said why."""

    def run_arena(self, lines):
        base = Path(tempfile.mkdtemp())
        self.addCleanup(__import__("shutil").rmtree, base)
        (base / "arena").mkdir()
        (base / "arena.rc").write_text(fight.RC)
        (base / "tip_uniq").write_text("TIP-UNIQ")
        (base / "arena/f.txt").write_text("b\na\nb\n")
        env = {**os.environ, "BASHOU_ARENA": str(base), "BASHOU_SRC": str(Path(fight.__file__).parent.parent)}
        env.pop("BASHOU_DUEL", None)
        out = subprocess.run(["bash", "--rcfile", str(base / "arena.rc"), "-i"], input="\n".join(lines) + "\nexit 0\n",
                             capture_output=True, text=True, env=env, timeout=20)
        return out.stdout

    def test_uniq_without_sort_gets_the_tip_once(self):
        out = self.run_arena(["cat f.txt | uniq -c", "cat f.txt | uniq -c"])
        self.assertEqual(out.count("TIP-UNIQ"), 1)

    def test_sort_then_uniq_gets_no_tip(self):
        self.assertNotIn("TIP-UNIQ", self.run_arena(["sort f.txt | uniq -c"]))

    def test_plain_sort_gets_the_scores_chest_wrong(self):
        for seed in range(20):
            with tempfile.TemporaryDirectory() as tmp:
                meta = challenges.BY_ID["trial_sort_scores"].setup(Path(tmp), random.Random(seed))
                text_last = sorted((Path(tmp) / "scores.txt").read_text().split())[-1]
                self.assertNotEqual(text_last, str(meta["answer"]))

    def test_the_owl_and_the_chest_say_why_sort_comes_first(self):
        from bashou.adventure import lessons
        pages = " ".join(text for text, example in lessons.BY_ID["pipes"]["pages"])
        self.assertIn("sort always comes before uniq", pages)
        self.assertTrue(any("next to each other" in h for h in challenges.BY_ID["trial_pipe_cities"].hints))


class StrikeWordTest(unittest.TestCase):
    """Owner: `answer` for file checks and `answer X` for questions were hard to tell apart."""

    def test_each_screen_shows_only_the_command_that_applies(self):
        from bashou import adventure
        for ch in challenges.ALL + challenges.TRIALS:
            with self.subTest(ch.id):
                screen = (adventure.trial_intro(ch, "task") if ch.kind == "trial" else fight.banner(ch, "task"))
                if ch.kind == "trial":
                    self.assertEqual(ch.fix, "answer <" not in ch.task)
                self.assertEqual("verify" in screen, ch.fix)
                self.assertEqual("answer <value>" in screen, not ch.fix)
