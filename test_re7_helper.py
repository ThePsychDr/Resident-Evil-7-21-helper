#!/usr/bin/env python3
"""Smoke tests for core solver logic."""
import unittest

import re7_helper_latest as solver


class TestHoffmanRuleTable(unittest.TestCase):
    def setUp(self):
        solver._HOFFMAN_RULE_TABLE_CACHE = None

    def test_rule_table_loads(self):
        table = solver._load_hoffman_rule_table()
        self.assertTrue(table)
        self.assertIn("rules", table)
        self.assertGreater(len(table["rules"]), 0)


class TestRoundOutcome(unittest.TestCase):
    def test_double_bust_smaller_margin_wins(self):
        self.assertEqual(solver.resolve_round_outcome(23, 25, 21), "WIN")
        self.assertEqual(solver.resolve_round_outcome(25, 23, 21), "LOSS")

    def test_single_bust(self):
        self.assertEqual(solver.resolve_round_outcome(22, 20, 21), "LOSS")
        self.assertEqual(solver.resolve_round_outcome(20, 22, 21), "WIN")


class TestRemoveEffect(unittest.TestCase):
    def test_remove_puts_opponent_card_in_dead_cards(self):
        result = solver.apply_trump_effect(
            "Remove",
            u_hand=[5, 8],
            o_vis=[3, 7],
            remaining=[1, 2, 4, 6, 9, 10, 11],
            dead_cards=[],
            target=21,
        )
        self.assertEqual(result["o_vis"], [3])
        self.assertEqual(result["dead_cards"], [7])
        self.assertIn("Removed opponent's card 7", result["msg"])


class TestProbabilities(unittest.TestCase):
    def test_calculate_probabilities(self):
        remaining = [1, 2, 3, 4]
        safe, bust, perfect = solver.calculate_probabilities(remaining, 18, 21)
        self.assertAlmostEqual(safe, 75.0)
        self.assertAlmostEqual(bust, 25.0)
        self.assertEqual(perfect, [3])


if __name__ == "__main__":
    unittest.main()
