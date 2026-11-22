import unittest

from research.tools import weight_tables


class AccountingTest(unittest.TestCase):
    def test_measures_both_copies_and_charges_code_twice(self):
        self.assertEqual(weight_tables.projected_saving(1000, 990, 6), 8)

    def test_code_can_reverse_model_gain(self):
        self.assertEqual(weight_tables.projected_saving(1000, 990, 12), -4)
