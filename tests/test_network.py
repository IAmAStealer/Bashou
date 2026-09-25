"""Network fights stay on this machine (owner, 2026-09-25): listeners on 127.0.0.1/::1 only, stopped with the
arena; captures are files. Nothing may reach another machine."""

import random
import tempfile
import time
import unittest
from pathlib import Path

from bashou.challenges import network

def loopback_fights():
    return [ch for ch in network.ALL + [network.CHEST] if ch.cleanup and ch.available()]


class LoopbackTest(unittest.TestCase):
    def test_listeners_are_loopback_only_and_stop_with_the_arena(self):
        self.assertTrue(loopback_fights() or not Path("/proc/net/tcp").exists())
        for ch in loopback_fights():
            with self.subTest(ch.id), tempfile.TemporaryDirectory() as tmp:
                work = Path(tmp) / "arena"
                work.mkdir()
                meta = ch.setup(work, random.Random(7))
                try:
                    port = meta["args"].get("port") or meta["answer"]
                    self.assertTrue(network.listening(port) or network.listening(port, v6=True))
                    for addr, lp, _rp, st in network.sockets() + network.sockets(v6=True):
                        if lp == port and st == "0A":
                            self.assertIn(addr, (network.LOOPBACK4, network.LOOPBACK6), f"{ch.id} listens beyond loopback")
                finally:
                    ch.cleanup(meta)
                for _ in range(50):
                    if not network.alive(meta["pid"]):
                        break
                    time.sleep(0.05)
                gone = not network.alive(meta["pid"]) or not Path(f"/proc/{meta['pid']}/cmdline").read_bytes()   # a zombie has none
                self.assertTrue(gone, f"{ch.id} left its listener running")


class CaptureTest(unittest.TestCase):
    def test_captures_are_valid_pcap_files(self):
        for setup, name in ((network.heron_setup, "capture.pcap"), (network.revenant_setup, "capture.pcap"),
                            (network.dns_setup, "dns.pcap")):
            with tempfile.TemporaryDirectory() as tmp:
                setup(Path(tmp), random.Random(3))
                data = (Path(tmp) / name).read_bytes()
                self.assertEqual(data[:4], bytes.fromhex("d4c3b2a1"))       # little-endian pcap magic
                self.assertGreater(len(data), 24 + 16 * 5)

    def test_checksums_are_right(self):
        """tcpdump -vv flags bad checksums: a packet summed with its own checksum gives 0."""
        frame = network.tcp("10.0.0.5", 40000, "10.0.0.1", 443, network.SYN, 1)
        ip = frame[14:34]
        self.assertEqual(network.checksum(ip), 0)
        seg = frame[34:]
        self.assertEqual(network.checksum(network.pseudo("10.0.0.5", "10.0.0.1", 6, seg) + seg), 0)
