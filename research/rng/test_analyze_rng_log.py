#!/usr/bin/env python3
"""Tests for Phase H RNG analysis (synthetic logs — no game required)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from analyze_rng_log import analyze, test_cross_session, test_round_index_determinism
from unity_random import UnityRandom, fisher_yates_shuffle, brute_force_seed_from_shuffle


class TestUnityRandom(unittest.TestCase):
    def test_brute_force_recovers_known_seed(self):
        seed = 424242
        rng = UnityRandom(seed)
        order = fisher_yates_shuffle(rng, list(range(1, 12)))
        found = brute_force_seed_from_shuffle(order, seed_min=0, seed_max=1_000_000)
        self.assertIsNotNone(found)
        replay = fisher_yates_shuffle(UnityRandom(found), list(range(1, 12)))
        self.assertEqual(replay, order)

    def test_different_seeds_differ(self):
        a = fisher_yates_shuffle(UnityRandom(1), list(range(1, 12)))
        b = fisher_yates_shuffle(UnityRandom(2), list(range(1, 12)))
        self.assertNotEqual(a, b)


class TestAnalyzeLog(unittest.TestCase):
    def _write_log(self, events):
        f = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
        for ev in events:
            f.write(json.dumps(ev) + "\n")
        f.close()
        return Path(f.name)

    def test_session_fixed_verdict(self):
        path = self._write_log([
            {"event": "random_init_state", "seed": 12345},
            {"event": "stock_shuffle", "round": 1, "stock": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]},
            {"event": "stock_shuffle", "round": 2, "stock": [2, 1, 4, 3, 6, 5, 8, 7, 10, 9, 11]},
        ])
        report = analyze([path])
        self.assertEqual(report["verdict"], "SESSION_FIXED")

    def test_round_determinism_helper(self):
        shuffles = [
            {"round": 1, "stock": [1, 2, 3]},
            {"round": 1, "stock": [1, 2, 3]},
            {"round": 2, "stock": [3, 2, 1]},
        ]
        ok, _ = test_round_index_determinism(shuffles)
        self.assertTrue(ok)

    def test_cross_session_different(self):
        a = [{"round": 1, "stock": [1, 2, 3]}]
        b = [{"round": 1, "stock": [3, 2, 1]}]
        same, _ = test_cross_session(a, b)
        self.assertFalse(same)

    def test_recover_seed_flag(self):
        seed = 999
        order = fisher_yates_shuffle(UnityRandom(seed), list(range(1, 12)))
        path = self._write_log([
            {"event": "stock_shuffle", "round": 1, "stock": order},
        ])
        report = analyze([path], recover_seed=True, seed_max=2000)
        self.assertEqual(report["seed_recovery"]["recovered"], 1)


if __name__ == "__main__":
    unittest.main()
