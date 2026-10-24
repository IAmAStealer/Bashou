"""Certificates (owner, 2026-10-23: "so many people are bad at it"): lessons certs, certs_tools, certs_admin, six
fights and a chest, questions, and the rules of doc/contributing/certs-style.md on everything players read."""

import json
import os
import random
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bashou import challenges, lesson
from bashou.adventure import lessons as owl

ROOT = Path(__file__).resolve().parent.parent
QUESTIONS = ROOT / "bashou" / "adventure" / "questions"
LESSONS = ("certs", "certs_tools", "certs_admin")
FIGHTS = ("expiry_elk", "san_salamander", "key_kobold", "chain_chameleon", "insecure_iguana", "request_raccoon")
CHEST = "trial_cert_issuer"
# A text that names the mistake on purpose: where -> the rules it shows broken.
ON_PURPOSE = {"insecure_iguana": {"T1"}}           # the task says what someone did: curl -k
OPENSSL = shutil.which("openssl")


def need_openssl(test):
    if not OPENSSL:
        test.skipTest("openssl not installed")


def cert_lessons(lang="en"):
    return [le for le in lesson.load(lang) if le["id"] in LESSONS]


def cert_questions(lang="en"):
    ids = {q for le in cert_lessons() for q in le.get("questions", [])}
    return [q for q in json.loads((QUESTIONS / lang / "network.json").read_text()) if q["id"] in ids]


def texts(lang="en"):
    """(where, text) of everything players read about certificates: right answers and explanations only."""
    for le in cert_lessons(lang):
        for n, page in enumerate(le["pages"], 1):
            yield f"{le['id']}/{n}", "\n".join(page.get("scheme", []) + page.get("text", []))
    for le in owl.LESSONS:
        if le["id"] == "certs":
            for n, (text, example) in enumerate(le["pages"], 1):
                yield f"owl certs/{n}", f"{text}\n{example}"
    for q in cert_questions(lang):
        yield q["id"], f"{q['choices'][q['answer']]}\n{q['explain']}"
    for cid in (*FIGHTS, CHEST):
        c = challenges.BY_ID[cid]
        yield cid, "\n".join([c.task, *c.hints, c.help or ""])


def lines_breaking(text):
    """(rule, line) of certs-style.md rules a line breaks; a line marked ✘ shows the mistake on purpose."""
    found = []
    for line in text.replace("\\\n", " ").splitlines():          # a command continued with \ is one line
        if "✘" in line or "✗" in line:
            continue
        if re.search(r"\bcurl\b[^|;.,:]*\s(-[a-zA-Z]*k[a-zA-Z]*|--insecure)\b", line) or re.search(
                r"verify\s*=\s*False|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*0", line):
            found.append(("T1", line))
        if re.search(r"-pass(out|in)\s+pass:", line):
            found.append(("T13", line))
        if re.search(r"\bopenssl\s+x509\b", line) and "-noout" not in line and re.search(r"-in\b", line) \
                and not re.search(r"-req\b|-out\b|-pubkey|>", line):
            found.append(("T12", line))
        if re.search(r"\bopenssl\s+s_client\b", line) and "-servername" not in line:
            found.append(("T10", line))
        if re.search(r"rsa(_keygen_bits:|:|\s+)(512|1024)\b|-(md5|sha1)\b", line, re.I):
            found.append(("T6", line))
        if re.search(r"-(ssl3|tls1|tls1_1)\b", line):
            found.append(("T8", line))
    return found


class StructureTest(unittest.TestCase):
    def test_the_lessons_make_a_road(self):
        by_id = {le["id"]: le for le in lesson.load("en")}
        self.assertEqual(by_id["certs"]["after"], ["keys", "net_debug"])
        self.assertEqual(by_id["certs_tools"]["after"], ["certs"])
        self.assertEqual(by_id["certs_admin"]["after"], ["certs_tools"])
        for lid in LESSONS:
            with self.subTest(lid):
                self.assertEqual(by_id[lid]["skill"], "network")
                self.assertTrue((ROOT / "bashou" / "lesson" / "fr" / f"{lid}.json").exists())
        fought = [f for lid in LESSONS for f in by_id[lid]["fights"]]
        self.assertEqual(sorted(fought), sorted(FIGHTS), "each fight is taught by one lesson")

    def test_each_lesson_has_its_questions_in_both_languages(self):
        fr = {q["id"]: q for q in json.loads((QUESTIONS / "fr" / "network.json").read_text())}
        en = {q["id"]: q for q in cert_questions()}
        for le in cert_lessons():
            with self.subTest(le["id"]):
                self.assertGreaterEqual(len(le.get("questions", [])), 4)
                for qid in le["questions"]:
                    self.assertIn(qid, en)
                    self.assertIn(qid, fr)
                    self.assertEqual(fr[qid]["answer"], en[qid]["answer"])
        self.assertGreaterEqual(len(en), 12)

    def test_the_fights_belong_to_network(self):
        for cid in FIGHTS:
            with self.subTest(cid):
                c = challenges.BY_ID[cid]
                self.assertEqual(c.skill, "network")
                self.assertIn("openssl", c.requires)
        self.assertIn(CHEST, {c.id for c in challenges.TRIALS})

    def test_the_owl_teaches_openssl(self):
        le = next(le for le in owl.LESSONS if le["id"] == "certs")
        self.assertEqual(le["tool"], "openssl")
        self.assertIn("network", le["topics"])


class RulesTest(unittest.TestCase):
    def test_the_checks_catch_their_mistake(self):
        for line, rule in [("curl -k https://shop.example/", "T1"), ("curl -fsSk https://x/", "T1"),
                           ("curl --insecure https://x/", "T1"), ("requests.get(url, verify=False)", "T1"),
                           ("openssl genrsa -passout pass:hunter2 2048", "T13"),
                           ("openssl x509 -in site.pem -text", "T12"),
                           ("openssl s_client -connect shop.example:443", "T10"),
                           ("openssl req -new -newkey rsa:1024 -keyout k", "T6"),
                           ("openssl s_client -tls1 -connect x:443 -servername x", "T8")]:
            with self.subTest(line):
                self.assertIn(rule, {r for r, _ in lines_breaking(line)})
        self.assertEqual(lines_breaking("✘ curl -k https://x/  turns the check off"), [])
        self.assertEqual(lines_breaking("openssl x509 -in site.pem -noout -dates"), [])
        self.assertEqual(lines_breaking("curl --cacert ca.pem https://lab.example/"), [])

    def test_what_players_read_follows_the_rules(self):
        for lang in ("en", "fr"):
            for where, text in texts(lang):
                with self.subTest(lang, where=where):
                    self.assertEqual([r for r, _ in lines_breaking(text) if r not in ON_PURPOSE.get(where, ())], [])

    def test_the_insecure_way_is_always_followed_by_the_fix(self):
        """T1: when a page or an explanation names -k, it says what to do instead."""
        for where, text in texts():
            if re.search(r"(?<![\w-])-k\b|--insecure", text):
                with self.subTest(where):
                    self.assertRegex(text, r"--cacert|-CAfile|trust store|update-ca-")

    def test_the_san_is_what_clients_check(self):
        """T2: the lessons never send players to the CN."""
        for where, text in texts():
            for sentence in re.split(r"(?<=[.!?])\s", text):
                if re.search(r"\bCN\b|Common Name", sentence):
                    with self.subTest(where, sentence=sentence):
                        self.assertRegex(sentence, r"SAN|Subject Alternative|subjectAltName|issuer|not|ignore|n't|stopped")


class FightTest(unittest.TestCase):
    def setUp(self):
        need_openssl(self)
        self.tmp = tempfile.TemporaryDirectory()
        self.work = Path(self.tmp.name) / "arena"
        self.work.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def sh(self, cmd):
        return subprocess.run(["bash", "-c", cmd], cwd=self.work, capture_output=True, text=True, timeout=30)

    def test_setup_makes_only_lab_keys_inside_the_arena(self):
        for cid in (*FIGHTS, CHEST):
            c = challenges.BY_ID[cid]
            if not c.available():
                continue
            with self.subTest(cid), tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp) / "arena"
                work.mkdir()
                meta = c.setup(work, random.Random(0))
                try:
                    for p in work.rglob("*"):
                        if p.is_file() and b"PRIVATE KEY" in p.read_bytes():
                            self.assertEqual(p.stat().st_mode & 0o077, 0, f"T5: {p.name} is readable by others")
                finally:
                    if c.cleanup:
                        c.cleanup(meta)

    def test_expiry_answer_is_the_file(self):
        c = challenges.BY_ID["expiry_elk"]
        meta = c.setup(self.work, random.Random(1))
        dying = [p.name for p in sorted((self.work / "certs").glob("*.pem"))
                 if self.sh(f"openssl x509 -checkend 2592000 -noout -in certs/{p.name}").returncode != 0]
        self.assertEqual(len(dying), 1)
        self.assertTrue(c.check(self.work, meta, dying[0]))
        self.assertTrue(c.check(self.work, meta, "certs/" + dying[0]))
        others = [p.name for p in (self.work / "certs").glob("*.pem") if p.name != dying[0]]
        self.assertFalse(c.check(self.work, meta, others[0]))

    def test_san_salamander_has_a_cn_trap(self):
        """The bad certificate names its site in the CN, not in the SAN: reading the subject is not enough."""
        c = challenges.BY_ID["san_salamander"]
        meta = c.setup(self.work, random.Random(2))
        bad = meta["answer"]
        subject = self.sh(f"openssl x509 -noout -subject -in 'sites/{bad}.pem'").stdout
        self.assertIn(bad, subject)
        self.assertIn("does NOT match", self.sh(f"openssl x509 -noout -checkhost '{bad}' -in 'sites/{bad}.pem'").stdout)
        self.assertFalse(c.check(self.work, meta, "nope.example"))

    def test_chain_must_be_in_order_without_the_root(self):
        c = challenges.BY_ID["chain_chameleon"]
        meta = c.setup(self.work, random.Random(3))
        leaf, *middle = meta["chain"]
        root = meta["root"]
        files = {name: (self.work / "certs" / name).read_text() for name in middle + [root]}
        server = (self.work / "server.pem").read_text()
        full = self.work / "fullchain.pem"
        full.write_text(server + "".join(files[n] for n in middle))
        self.assertTrue(c.check(self.work, meta, "done"))
        full.write_text(server + "".join(files[n] for n in reversed(middle)))
        self.assertFalse(c.check(self.work, meta, "done"), "T3: intermediates in order")
        full.write_text(server + "".join(files[n] for n in middle) + files[root])
        self.assertFalse(c.check(self.work, meta, "done"), "T3: no root")
        full.write_text(server)
        self.assertFalse(c.check(self.work, meta, "done"), "the leaf alone is the bug")

    def test_request_raccoon_checks_names_key_and_mode(self):
        c = challenges.BY_ID["request_raccoon"]
        meta = c.setup(self.work, random.Random(4))
        names = meta["names"]
        san = ",".join(f"DNS:{n}" for n in names)
        good = (f"openssl req -new -newkey ec -pkeyopt ec_paramgen_curve:P-256 -noenc -keyout shop.key -out shop.csr "
                f"-subj '/CN={names[0]}' -addext 'subjectAltName={san}' 2>/dev/null")
        self.assertEqual(self.sh(good + " && chmod 600 shop.key").returncode, 0)
        self.assertTrue(c.check(self.work, meta, "done"))
        os.chmod(self.work / "shop.key", 0o644)
        self.assertFalse(c.check(self.work, meta, "done"), "T5: the key is readable by others")
        self.sh(good.replace(f",DNS:{names[-1]}", "") + " && chmod 600 shop.key")
        self.assertFalse(c.check(self.work, meta, "done"), "T2: every name in the SAN")
        self.sh(good.replace("ec -pkeyopt ec_paramgen_curve:P-256", "rsa:1024") + " && chmod 600 shop.key")
        self.assertFalse(c.check(self.work, meta, "done"), "T6: RSA 1024 is too short")
        self.sh(f"openssl req -new -newkey ec -pkeyopt ec_paramgen_curve:P-256 -noenc -keyout shop.key -out shop.csr "
                f"-subj '/CN={names[0]}' 2>/dev/null && chmod 600 shop.key")
        self.assertFalse(c.check(self.work, meta, "done"), "T2: a CN alone covers nothing")

    def test_insecure_iguana_refuses_k_and_wants_the_lab_ca(self):
        c = challenges.BY_ID["insecure_iguana"]
        if not c.available():
            self.skipTest("Linux loopback only")
        meta = c.setup(self.work, random.Random(5))
        meta_ca = (self.work / "ca.pem").read_text()
        try:
            self.assertFalse(c.check(self.work, meta, "done"), "the starter keeps -k")
            script = self.work / "fetch.sh"
            text = script.read_text()
            script.write_text(text.replace(" -k ", " "))
            self.assertFalse(c.check(self.work, meta, "done"), "without -k nor the CA, curl refuses")
            script.write_text(text.replace(" -k ", " --cacert ca.pem -k "))
            self.assertFalse(c.check(self.work, meta, "done"), "T1: -k still there")
            script.write_text(text.replace(" -k ", " --cacert ca.pem "))
            self.assertFalse(c.check(self.work, meta, "done"), "ca.pem from the current folder: fails from cron")
            fixed = ' --cacert "$dir/ca.pem" '
            text = text.replace("\nurl=", '\ndir=$(dirname -- "${BASH_SOURCE[0]}")\nurl=')
            tricks = {"-k on a continued line": text.replace(" -k ", fixed + "\\\n  -k "),
                      "-k in an array": text.replace("page=$(curl", "opts=(-k)\npage=$(curl").replace(
                          " -k ", fixed + '"${opts[@]}" '),
                      "insecure in a config file": text.replace(" -k ", fixed + '-K "$dir/my.cfg" ')}
            (self.work / "my.cfg").write_text("insecure\n")
            for why, bad in tricks.items():
                script.write_text(bad)
                self.assertFalse(c.check(self.work, meta, "done"), why)
            home = Path(self.tmp.name) / "home"
            home.mkdir()
            (home / ".curlrc").write_text("insecure\n")
            script.write_text(text.replace(" -k ", fixed))
            with mock.patch.dict(os.environ, {"HOME": str(home)}):
                self.assertTrue(c.check(self.work, meta, "done"), "the player's ~/.curlrc isn't read")
            self.assertEqual((self.work / "ca.pem").read_text(), meta_ca, "verify puts ca.pem back")
        finally:
            c.cleanup(meta)

    def test_the_chest_takes_what_libressl_prints(self):
        """LibreSSL on a Mac prints issuer= /CN=…, OpenSSL 3 issuer=CN=…: both win."""
        meta = {"answer": "Old Oak CA"}
        for printed in ("issuer=CN=Old Oak CA", "issuer= /CN=Old Oak CA", "CN = Old Oak CA", "old oak ca"):
            self.assertTrue(challenges.certs.same_issuer(self.work, meta, printed), printed)

    def test_a_key_with_a_passphrase_fails_without_asking(self):
        """openssl pkey asked for the passphrase on the terminal, and the verify hung until its timeout."""
        c = challenges.BY_ID["request_raccoon"]
        meta = c.setup(self.work, random.Random(0))
        first, second = meta["names"]
        pw = Path(self.tmp.name) / "pw"
        pw.write_text("secret\n")
        subprocess.run(["openssl", "req", "-new", "-newkey", "ec", "-pkeyopt", "ec_paramgen_curve:P-256",
                        "-passout", f"file:{pw}", "-keyout", "shop.key", "-out", "shop.csr", "-subj", f"/CN={first}",
                        "-addext", f"subjectAltName=DNS:{first},DNS:{second}"], cwd=self.work, capture_output=True,
                       check=True, stdin=subprocess.DEVNULL)
        os.chmod(self.work / "shop.key", 0o600)
        calls, real = [], challenges.certs.check
        def spy(*args):
            calls.append(args)
            return real(*args)
        with mock.patch.object(challenges.certs, "check", spy):
            self.assertFalse(c.check(self.work, meta, "done"))
        keys = [a for a in calls if a[0] == "pkey"]
        self.assertTrue(keys)
        for args in keys:                       # on a terminal, openssl would ask for it there
            self.assertIn("-passin", args)

    def test_healthy_certificates_fit_todays_public_limit(self):
        """T7: public certificates last 200 days at most since 2026-03-15."""
        c = challenges.BY_ID["expiry_elk"]
        meta = c.setup(self.work, random.Random(3))
        for f in (self.work / "certs").glob("*.pem"):
            self.assertEqual(subprocess.run(["openssl", "x509", "-in", f, "-noout", "-checkend", str(201 * 86400)],
                                            capture_output=True).returncode, 1, f.name)
        self.assertTrue(meta["answer"])



class SpotTest(unittest.TestCase):
    def test_spot_knows_pem_headers(self):
        from bashou import spot
        rng = random.Random(0)
        for kind, header in [("cert", "-----BEGIN CERTIFICATE-----"), ("csr", "CERTIFICATE REQUEST-----"),
                             ("privkey", "PRIVATE KEY-----")]:
            with self.subTest(kind):
                self.assertIn(kind, spot.KINDS)
                texts = {spot.KINDS[kind][2](rng) for _ in range(20)}
                self.assertTrue(all(header in t and len(t) <= spot.LONGEST for t in texts), texts)
                self.assertGreater(len(texts), 3, "never the same twice")


if __name__ == "__main__":
    unittest.main()
