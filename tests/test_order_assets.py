import unittest

from research.tools import order_deltas as codec


class OrderAssetsTests(unittest.TestCase):
    def test_holes_and_decreasing_runs(self):
        source = b"5\n4\n0\n7\n2\n"
        labels = codec.label_encode(source)
        self.assertEqual(list(labels[:8]), [1, 0, 2, 0, 1, 1, 0, 2])
        self.assertEqual(codec.label_decode(labels), source)

    def test_more_than_one_byte_of_run_labels(self):
        asc = b"".join(f"{x}\n".encode() for x in range(260))
        self.assertEqual(codec.label_decode(codec.label_encode(asc)), asc)

    def test_duplicate_id_rejected(self):
        with self.assertRaises(ValueError):
            codec.label_encode(b"2\n1\n2\n")

    def test_signed_varints_and_incomplete_last_byte(self):
        source = b"159650\n30481\n30113\n0\n172314\n"
        self.assertEqual(codec.decode(codec.encode(source)), source)
        with self.assertRaises(ValueError):
            codec.decode(b"\x80")
