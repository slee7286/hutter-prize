import os
import sys
import tempfile
import unittest
from pathlib import Path

from research.tools import donor_prefix as d


class PrefixTests(unittest.TestCase):
    def test_short_equal_is_not_match(self):
        self.assertEqual(d.compare(b"x", b"x")["status"], "incomplete")

    def test_last_byte_has_zero_based_offset(self):
        a = bytes(d.LIMIT)
        self.assertEqual(d.compare(a, a[:-1] + b"X")["offset"], d.LIMIT - 1)
        self.assertEqual(d.compare(a, a)["status"], "match")

    def pipe_run(self, body, timeout: float = 3):
        with tempfile.TemporaryDirectory() as t:
            fifo = Path(t) / "fifo"
            os.mkfifo(fifo)
            return d.capture(
                fifo, [sys.executable, "-c", body, str(fifo)], Path(t) / "log", timeout
            )

    def test_stop_full_writer_at_limit(self):
        b, stop, _ = self.pipe_run(
            "import sys; f=open(sys.argv[1],'wb',buffering=0)\nwhile True: f.write(b'abc'*8192)"
        )
        self.assertEqual(stop, "prefix_limit")
        self.assertEqual(b, (b"abc" * d.LIMIT)[: d.LIMIT])

    def test_short_writer_preserved(self):
        b, stop, _ = self.pipe_run("import sys; open(sys.argv[1],'wb').write(b'abc')")
        self.assertEqual(b, b"abc")
        self.assertNotEqual(stop, "prefix_limit")

    def test_timeout_without_writer(self):
        b, stop, _ = self.pipe_run("import time; time.sleep(10)", 0.15)
        self.assertEqual((b, stop), (b"", "wall_timeout"))
