"""The network Bashou shows follows doc/contributing/network-style.md (owner, 2026-10-28: a quality judge for every
kind of content). Addresses in text players read are documentation, private or special addresses (N1): a real
one changes with time and belongs to someone."""

import ipaddress
import re
import unittest
from pathlib import Path

from tests.test_bash_style import all_texts

ROOT = Path(__file__).resolve().parent.parent
STYLE = ROOT / "doc" / "contributing" / "network-style.md"
ALLOWED = [ipaddress.ip_network(n) for n in (
    "192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24",           # documentation, RFC 5737
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",               # private, RFC 1918
    "100.64.0.0/10", "127.0.0.0/8", "169.254.0.0/16", "0.0.0.0/32", "224.0.0.0/4", "255.0.0.0/8",
    "2001:db8::/32",                                               # documentation, RFC 3849
)]
RESOLVERS = {"1.1.1.1", "1.0.0.1", "8.8.8.8", "8.8.4.4", "9.9.9.9"}   # public resolvers, named as such
IPV4 = re.compile(r"(?<![\d.])\d{1,3}(?:\.\d{1,3}){3}(?![\d.])")
IPV6 = re.compile(r"(?<![\w:])[0-9a-fA-F]*:[0-9a-fA-F:]*:[0-9a-fA-F]*(?![\w:])")   # checked by ip_address


def outside(text):
    """The addresses in this text that are not allowed (N1)."""
    for m in IPV4.findall(text) + IPV6.findall(text):
        try:
            a = ipaddress.ip_address(m)
        except ValueError:
            continue                        # a time (10:00:00), a gcc position (c:5:14:)
        if m not in RESOLVERS and not any(a in n for n in ALLOWED if n.version == a.version) \
                and not (a.version == 6 and a not in ipaddress.ip_network("2000::/3")):
            yield m


class TextTest(unittest.TestCase):
    def test_addresses_are_documentation_private_or_special(self):
        for _, lines in all_texts():
            for where, line in lines:
                with self.subTest(where=where):
                    self.assertEqual(list(outside(line)), [], f"{where}: {line}")

    def test_outside_finds_real_addresses(self):
        self.assertEqual(list(outside("example.org 104.20.26.136, 2606:4700::6812:1a88")),
                         ["104.20.26.136", "2606:4700::6812:1a88"])
        self.assertEqual(list(outside("203.0.113.100 2001:db8::1 fe80::1 ::1 192.168.1.10 dig @1.1.1.1")), [])


class StyleFileTest(unittest.TestCase):
    def test_every_rule_has_an_online_source(self):
        """Owner (2026-10-26): every rule needs an online reference, official when there is one."""
        for line in STYLE.read_text().splitlines():
            if re.match(r"\| N\d+ \|", line):
                with self.subTest(rule=line.split("|")[1].strip()):
                    self.assertRegex(line, r"\]\(https://")

    def test_rule_ids_are_unique(self):
        ids = re.findall(r"^\| (N\d+) \|", STYLE.read_text(), re.M)
        self.assertGreater(len(ids), 5)
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
