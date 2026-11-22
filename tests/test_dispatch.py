import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from research.tools import dispatch as d


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Path(self.tmp.name)
        self.t = {
            "kind": "extract",
            "question": "Which build was tested?",
            "source": "release table, row 2",
            "excerpt": "July build: startup only.",
        }
        self.worker = Mock(
            return_value={
                "answer": "Only startup.",
                "usage": {
                    "input_tokens": 34,
                    "cached_input_tokens": 11,
                    "output_tokens": 4,
                },
            }
        )

    def go(self, t=None, live=True):
        return d.dispatch(self.t if t is None else t, live, self.store, self.worker)

    def test_no_spend_routes(self):
        self.assertEqual(
            self.go({"kind": "script", "question": "Hash archive?"})["route"], "script"
        )
        self.assertEqual(
            self.go(
                {
                    "kind": "decision",
                    "question": "Does a size match establish identity?",
                }
            )["route"],
            "premium-parent",
        )
        self.go(live=False)
        self.worker.assert_not_called()

    def test_reuse_instead_of_second_dispatch(self):
        a = self.go()
        b = self.go()
        self.assertEqual(b["answer"], a["answer"])
        self.assertTrue(b["reused"])
        self.worker.assert_called_once()

    def test_fail_closed_on_worker_failure(self):
        self.worker.side_effect = ValueError("Unavailable")
        with self.assertRaises(ValueError):
            self.go()
        with self.assertRaises(ValueError):
            self.go()
        self.worker.assert_called_once()

    def test_no_unjustified_premium_worker(self):
        with self.assertRaises(ValueError):
            self.go(dict(self.t, kind="challenge"))
        self.worker.assert_not_called()

    def test_reserve_premium_separately(self):
        for i in range(3):
            self.go(dict(self.t, question=str(i)))
        with self.assertRaises(ValueError):
            self.go()
        premium = dict(
            self.t,
            kind="challenge",
            stakes="Committing days of compute to the wrong build",
        )
        self.assertEqual(self.go(premium)["route"], "premium-review")
        with self.assertRaises(ValueError):
            self.go(dict(premium, question="Another?"))

    def test_context_bound(self):
        with self.assertRaises(ValueError):
            self.go(dict(self.t, excerpt="X" * 13000))
        self.worker.assert_not_called()

    def test_usage_unknown_not_zero(self):
        self.assertIsNone(d.usage({}))
        self.assertIsNone(d.usage({"tokens": {"input": 0, "output": 0}}))
        buckets = {"input": 14, "cache_read": 4, "output": 2}
        self.assertEqual(d.usage({"tokens": buckets}), buckets)
