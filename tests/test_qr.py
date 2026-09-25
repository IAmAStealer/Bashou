import random
import shutil
import string
import subprocess
import unittest

from bashou import qr


def reference(text):
    """qrencode's matrix (byte mode, level L, no margin)."""
    out = subprocess.run(["qrencode", "-t", "ASCII", "-l", "L", "-8", "-m", "0", text],
                         capture_output=True, text=True, check=True).stdout.splitlines()
    return [[line[i] == "#" for i in range(0, len(line), 2)] for line in out]


def mask_of(rows):
    """The mask a code uses, read back from its format bits."""
    for mask in range(8):
        m = qr.Matrix((len(rows) - 17) // 4)
        m.format(mask)
        if all(rows[8][c] == m.dark[8][c] for c in range(9) if c != 6):
            return mask


class QrTest(unittest.TestCase):
    def test_format_and_version_bits(self):
        self.assertEqual(qr.bch(0b01 << 3 | 0, 0x537, 10) ^ 0x5412, 0b111011111000100)    # level L, mask 0
        self.assertEqual(qr.bch(7, 0x1F25, 12), 0x07C94)                                 # version 7

    def test_reed_solomon(self):
        """The worked example of the standard: "01234567" at 1-M."""
        data = [0x10, 0x20, 0x0C, 0x56, 0x61, 0x80, 0xEC, 0x11, 0xEC, 0x11, 0xEC, 0x11, 0xEC, 0x11, 0xEC, 0x11]
        self.assertEqual(qr.reed_solomon(data, 10), [0xA5, 0x24, 0xD4, 0xC1, 0xED, 0x36, 0xC7, 0x87, 0x2C, 0x55])

    def test_versions_grow_with_the_text(self):
        self.assertEqual(len(qr.encode("hi")), 21)
        self.assertEqual(len(qr.encode("x" * 150)), 45)             # version 7: a share link
        with self.assertRaises(ValueError):
            qr.encode("x" * 272)

    def test_terminal_is_dark_on_light(self):
        lines = qr.terminal(qr.encode("hi"))
        self.assertEqual(len(lines), (21 + 8 + 1) // 2)
        self.assertIn("107m", lines[0])                             # the quiet zone is white

    @unittest.skipUnless(shutil.which("qrencode"), "qrencode isn't installed")
    def test_same_matrix_as_qrencode(self):
        rng = random.Random(1)
        alphabet = string.ascii_letters + string.digits + "-_.#/:"
        texts = ["HELLO WORLD", "https://iamastealer.github.io/Bashou/share.html#v1.eJyrVkpUsjIw0FEqSs1L"]
        texts += ["".join(rng.choice(alphabet) for _ in range(rng.randrange(1, 270))) for _ in range(20)]
        for text in texts:
            with self.subTest(len(text)):
                ref = reference(text)
                self.assertEqual(qr.encode(text, mask=mask_of(ref)), ref)
