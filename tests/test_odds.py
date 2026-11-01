"""Tests for the RE7 '21' odds math.

Run from the repo root:
    python3 -m unittest discover tests

The core check is an independent brute-force model: enumerate EVERY ordering of
the cards you can't see, deal the opponent's face-down card first, then play the
rest of the round card by card.  Every ordering is equally likely (the 11-card
deck is shuffled), so averaging over orderings gives the exact probabilities the
solver's faster recursive code must reproduce.
"""
import itertools
import json
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import re7_helper_latest as solver  # noqa: E402

FULL_DECK = list(range(1, 12))
EPS = 1e-9


# ----------------------------------------------------------------------------
# Independent reference model (deliberately naive — no memoisation, no tricks)
# ----------------------------------------------------------------------------
def ref_outcome(you, opp, target):
    """Win/tie/loss written straight from the rule: closest to target without
    going over wins; if both go over, the smaller total wins."""
    you_ok, opp_ok = you <= target, opp <= target
    if you_ok and opp_ok:
        return "win" if you > opp else "loss" if you < opp else "tie"
    if you_ok != opp_ok:
        return "win" if you_ok else "loss"
    return "win" if you < opp else "loss" if you > opp else "tie"


def ref_opponent_play(total, cards, draw_prob, target):
    """Opponent draws cards from `cards` in order, drawing with probability
    draw_prob(total) each time.  Returns {final_total: prob}."""
    if total > target or not cards:
        return {total: 1.0}
    p = draw_prob(total)
    if p <= 0.001:
        return {total: 1.0}
    if p >= 0.999:
        p = 1.0
    out = {}
    if p < 1.0:
        out[total] = 1.0 - p
    for t, q in ref_opponent_play(total + cards[0], cards[1:], draw_prob, target).items():
        out[t] = out.get(t, 0.0) + p * q
    return out


def ref_round(you_total, opp_visible, unseen, draw_prob, target, you_hit,
              opp_hidden=None, opp_stays=False, player_vis_for_ai=None):
    """Exact win/tie/loss by enumerating all orderings of `unseen`.

    Ordering = [opponent hidden card (if unknown)] + [your hit card (if hitting)]
               + [cards the opponent would draw, in order].
    """
    res = {"win": 0.0, "tie": 0.0, "loss": 0.0}
    perms = list(itertools.permutations(unseen))
    if not perms:
        perms = [()]
    w = 1.0 / len(perms)
    for perm in perms:
        perm = list(perm)
        if opp_hidden is None:
            if not perm:
                hidden = 0
            else:
                hidden = perm.pop(0)
        else:
            hidden = opp_hidden
        you = you_total
        if you_hit:
            if not perm:
                continue
            you += perm.pop(0)
        seen_by_ai = you if player_vis_for_ai is None else player_vis_for_ai
        opp_start = opp_visible + hidden
        if opp_stays:
            dist = {opp_start: 1.0}
        else:
            dist = ref_opponent_play(opp_start, perm, lambda t: draw_prob(t, seen_by_ai), target)
        for t, q in dist.items():
            res[ref_outcome(you, t, target)] += w * q
    return res


def ref_opp_distribution(opp_visible, unseen, draw_prob, target, opp_hidden=None):
    out = {}
    perms = list(itertools.permutations(unseen)) or [()]
    for perm in perms:
        perm = list(perm)
        hidden = perm.pop(0) if opp_hidden is None else opp_hidden
        for t, q in ref_opponent_play(opp_visible + hidden, perm, draw_prob, target).items():
            out[t] = out.get(t, 0.0) + q / len(perms)
    return out


def unseen_after(*known):
    k = [c for group in known for c in group]
    return [c for c in FULL_DECK if c not in k]


def assert_dist_close(tc, got, want):
    keys = set(got) | set(want)
    for k in keys:
        tc.assertAlmostEqual(got.get(k, 0.0), want.get(k, 0.0), delta=EPS, msg=f"total {k}")


def assert_wtl_close(tc, got, want):
    for k in ("win", "tie", "loss"):
        tc.assertAlmostEqual(got[k], want[k], delta=EPS, msg=k)


# A spread of opponent AIs: hard threshold, gray-zone, chicken, real profiles.
AIS = {
    "threshold17": solver.BankerAI(17, 17, False, 17, 21, 1, 12),
    "grayzone": solver.BankerAI(15, 19, False, 16, 21, 1, 13),
    "chicken": solver.BankerAI(14, 17, True, 18, 21, 1, 14),
    "tally_basic": solver.BANKER_AI_PROFILES["tally_basic"],
    "mr_big_head": solver.BANKER_AI_PROFILES["mr_big_head"],
}

# (your cards, opponent face-up cards, dead cards, target)
SCENARIOS = [
    ([6, 10], [9], [], 21),
    ([2, 3], [11], [], 21),
    ([10, 9], [8, 7], [], 21),      # opponent showing 15 — high visible total
    ([4, 5], [10, 8], [], 21),      # opponent showing 18 — hidden card can bust them
    ([7, 8], [3], [1, 2], 21),      # dead cards
    ([11, 9, 3], [6], [], 24),      # Go for 24 active
    ([11, 10], [5], [], 17),        # Go for 17 active, you're already bust
    ([9, 8, 7], [5, 1], [], 21),    # you're bust (24)
]


class TestRules(unittest.TestCase):
    def test_round_outcome_truth_table(self):
        for target in (17, 21, 24, 27):
            for you in range(2, 40):
                for opp in range(2, 40):
                    self.assertEqual(
                        solver.resolve_round_outcome(you, opp, target).lower(),
                        ref_outcome(you, opp, target), (you, opp, target))

    def test_both_bust_lower_total_wins(self):
        self.assertEqual(solver.resolve_round_outcome(23, 25, 21), "WIN")
        self.assertEqual(solver.resolve_round_outcome(25, 23, 21), "LOSS")
        self.assertEqual(solver.resolve_round_outcome(24, 24, 21), "TIE")
        self.assertEqual(solver.resolve_round_outcome(21, 22, 21), "WIN")

    def test_bust_outcome_agrees_when_you_are_bust(self):
        for you in range(22, 35):
            for opp in range(2, 35):
                self.assertEqual(solver.bust_outcome(you, opp, 21),
                                 solver.resolve_round_outcome(you, opp, 21))
        self.assertEqual(solver.bust_outcome(20, 25, 21), "NOT_BUST")

    def test_best_card_for(self):
        self.assertEqual(solver.best_card_for(14, [3, 7, 9], 21), 7)    # exact 21
        self.assertEqual(solver.best_card_for(14, [3, 8, 9], 21), 3)    # largest that fits
        self.assertEqual(solver.best_card_for(21, [3, 8, 9], 21), 3)    # all bust -> least bust
        self.assertIsNone(solver.best_card_for(10, [], 21))


class TestDrawOdds(unittest.TestCase):
    def test_safe_and_bust_match_enumeration(self):
        """Your next card is uniform over the deck, but the deck is the unseen cards
        minus the opponent's hidden one.  Averaging over that hidden card must give the
        same safe/bust split as the solver's 'all unseen cards' shortcut."""
        for mine, opp, dead, target in SCENARIOS:
            unseen = unseen_after(mine, opp, dead)
            total = sum(mine)
            safe = 0.0
            for hidden in unseen:
                deck = [c for c in unseen if c != hidden]
                safe += sum(1 for c in deck if total + c <= target) / len(deck) / len(unseen)
            safe_pct, bust_pct, perfect = solver.calculate_probabilities(unseen, total, target)
            self.assertAlmostEqual(safe_pct / 100, safe, delta=EPS)
            self.assertAlmostEqual(safe_pct + bust_pct, 100.0, delta=EPS)
            self.assertEqual(sorted(perfect), [c for c in unseen if total + c == target])

    def test_empty_deck(self):
        self.assertEqual(solver.calculate_probabilities([], 15, 21), (0.0, 0.0, []))


class TestOpponentDistribution(unittest.TestCase):
    def test_stay_distribution_is_hidden_card_spread(self):
        unseen = unseen_after([6, 10], [9])
        dist = solver.opponent_total_distribution(9, unseen, 17, 21, behavior="stay")
        assert_dist_close(self, dist, {9 + c: 1 / len(unseen) for c in unseen})

    def test_auto_matches_brute_force(self):
        for name, ai in AIS.items():
            for mine, opp, dead, target in SCENARIOS:
                unseen = unseen_after(mine, opp, dead)
                you = sum(mine)
                with self.subTest(ai=name, mine=mine, opp=opp, target=target):
                    got = solver.opponent_total_distribution(
                        sum(opp), unseen, ai.take_card_border, target,
                        behavior="auto", banker_ai=ai, player_visible_total=you)
                    want = ref_opp_distribution(
                        sum(opp), unseen, lambda t: ai.draw_probability(t, you, target), target)
                    assert_dist_close(self, got, want)
                    self.assertAlmostEqual(sum(got.values()), 1.0, delta=EPS)

    def test_known_hidden_card(self):
        ai = AIS["grayzone"]
        unseen = unseen_after([6, 10], [9], [4])  # 4 is the opponent's hidden card
        got = solver.opponent_total_distribution(
            9, unseen, 15, 21, behavior="auto", banker_ai=ai, player_visible_total=16, opp_hidden=4)
        want = ref_opp_distribution(
            9, unseen, lambda t: ai.draw_probability(t, 16, 21), 21, opp_hidden=4)
        assert_dist_close(self, got, want)
        stay = solver.opponent_total_distribution(9, unseen, 15, 21, behavior="stay", opp_hidden=4)
        self.assertEqual(stay, {13: 1.0})

    def test_regression_hidden_card_is_never_skipped(self):
        """Old bug: with the opponent showing 18 in the AI's 'gray zone', the solver let
        the opponent 'stay' on its visible 18 — as if it had no face-down card at all.
        The opponent's final total can never be below visible + smallest unseen card."""
        ai = solver.BankerAI(15, 19, False, 16, 21, 1, 13)
        unseen = unseen_after([4, 5], [10, 8])
        dist = solver.opponent_total_distribution(18, unseen, 15, 21, banker_ai=ai,
                                                  player_visible_total=9)
        self.assertGreaterEqual(min(dist), 18 + min(unseen))
        self.assertNotIn(18, dist)

    def test_hit_once_draws_hidden_plus_one(self):
        unseen = [1, 2, 3]
        dist = solver.opponent_total_distribution(10, unseen, 17, 21, behavior="hit_once")
        # hidden + one more card = any 2 of {1,2,3}: sums 3,4,5 each with prob 1/3
        assert_dist_close(self, dist, {13: 1 / 3, 14: 1 / 3, 15: 1 / 3})


class TestStayHit(unittest.TestCase):
    def test_stay_and_hit_match_brute_force(self):
        for name, ai in AIS.items():
            for mine, opp, dead, target in SCENARIOS:
                unseen = unseen_after(mine, opp, dead)
                you = sum(mine)
                for behavior in ("auto", "stay"):
                    with self.subTest(ai=name, mine=mine, opp=opp, target=target, behavior=behavior):
                        stay, hit = solver.evaluate_stay_hit_outcomes(
                            you, sum(opp), unseen, ai.take_card_border, target, behavior, banker_ai=ai)
                        dp = lambda t, pv: ai.draw_probability(t, pv, target)  # noqa: E731
                        assert_wtl_close(self, stay, ref_round(
                            you, sum(opp), unseen, dp, target, you_hit=False,
                            opp_stays=(behavior == "stay")))
                        assert_wtl_close(self, hit, ref_round(
                            you, sum(opp), unseen, dp, target, you_hit=True,
                            opp_stays=(behavior == "stay")))
                        for probs in (stay, hit):
                            self.assertAlmostEqual(sum(probs.values()), 1.0, delta=EPS)

    def test_known_hidden_card_matches_brute_force(self):
        ai = AIS["tally_basic"]
        mine, opp, hidden = [6, 10], [9], 4
        unseen = unseen_after(mine, opp, [hidden])
        dp = lambda t, pv: ai.draw_probability(t, pv, 21)  # noqa: E731
        for behavior in ("auto", "stay"):
            stay, hit = solver.evaluate_stay_hit_outcomes(
                16, 9, unseen, 16, 21, behavior, banker_ai=ai, opp_hidden=hidden)
            assert_wtl_close(self, stay, ref_round(16, 9, unseen, dp, 21, False, opp_hidden=hidden,
                                                   opp_stays=(behavior == "stay")))
            assert_wtl_close(self, hit, ref_round(16, 9, unseen, dp, 21, True, opp_hidden=hidden,
                                                  opp_stays=(behavior == "stay")))

    def test_obvious_cases(self):
        # Opponent stayed showing 2 + hidden from {1}: total 3. You on 20 -> certain win.
        unseen = [1]
        stay, _ = solver.evaluate_stay_hit_outcomes(20, 2, unseen, 17, 21, "stay")
        self.assertAlmostEqual(stay["win"], 1.0, delta=EPS)


class TestLoveYourEnemy(unittest.TestCase):
    def test_lucas_saw_round(self):
        """Opponent on exactly 21: every card busts them, so LYE always busts them."""
        unseen = [1, 2, 3, 5]
        # opponent shows 18, hidden card known 3 -> 21
        self.assertEqual(solver.love_your_enemy_bust_chance(18, unseen, 21, opp_hidden=3), 1.0)

    def test_best_card_never_busts_when_a_safe_card_exists(self):
        # Opponent shows 5; whatever the hidden card, a non-busting card remains.
        unseen = unseen_after([10, 7], [5])
        self.assertEqual(solver.love_your_enemy_bust_chance(5, unseen, 21), 0.0)

    def test_outcomes_match_brute_force(self):
        ai = AIS["grayzone"]
        mine, opp, target = [10, 8], [9], 21
        unseen = unseen_after(mine, opp)
        you = sum(mine)
        got = solver.love_your_enemy_outcomes(you, sum(opp), unseen, 15, target, banker_ai=ai)

        want = {"win": 0.0, "tie": 0.0, "loss": 0.0}
        for hidden in unseen:
            rest = [c for c in unseen if c != hidden]
            fits = [c for c in rest if sum(opp) + hidden + c <= target]
            forced = max(fits) if fits else min(rest)
            after = [c for c in rest if c != forced]
            dist = ref_opp_distribution(
                sum(opp) + forced, after, lambda t: ai.draw_probability(t, you, target),
                target, opp_hidden=hidden)
            for t, q in dist.items():
                want[ref_outcome(you, t, target)] += q / len(unseen)
        assert_wtl_close(self, got, want)
        self.assertAlmostEqual(sum(got["forced_cards"].values()), 1.0, delta=EPS)


class TestAdvice(unittest.TestCase):
    def test_action_follows_clear_win_edge(self):
        """Regression: advice once said 'HIT — can reach 21' while its own numbers showed
        STAY winning 52.7% vs HIT 42.2%. A clear (>=5 point) edge must decide the action."""
        intel = {"name": "Test Hoffman", "trumps": [], "stay_val": 17}
        ai = solver.BANKER_AI_PROFILES["molded_mid"]
        unseen = unseen_after([6, 10], [9], [4])
        stay, hit = solver.evaluate_stay_hit_outcomes(16, 9, unseen, 17, 21, "auto",
                                                      banker_ai=ai, opp_hidden=4)
        self.assertGreater(stay["win"] - hit["win"], 0.05)
        safe_pct, _, perfect = solver.calculate_probabilities(unseen, 16, 21)
        _, advice = solver.generate_advice(16, 9, intel, unseen, 21, safe_pct, perfect,
                                           10, 10, 10, 10, "auto", banker_ai=ai, opp_hidden=4)
        action = [a for a in advice if a.startswith("ACTION:")]
        self.assertEqual(len(action), 1, advice)
        self.assertTrue(action[0].startswith("ACTION: STAY"), action[0])


class TestQuickOdds(unittest.TestCase):
    def test_matches_core_functions(self):
        r = solver.quick_odds([6, 10], [9], ai_profile="tally_basic")
        ai = solver.BANKER_AI_PROFILES["tally_basic"]
        unseen = unseen_after([6, 10], [9])
        stay, hit = solver.evaluate_stay_hit_outcomes(16, 9, unseen, ai.take_card_border, 21, "auto",
                                                      banker_ai=ai)
        assert_wtl_close(self, r["main"]["stay"], stay)
        assert_wtl_close(self, r["main"]["hit"], hit)
        self.assertEqual([row["target"] for row in r["targets"]], [17, 21, 24, 27])

    def test_rejects_bad_input(self):
        with self.assertRaises(ValueError):
            solver.quick_odds([6, 6], [9])            # duplicate card
        with self.assertRaises(ValueError):
            solver.quick_odds([12], [9])              # out of range
        with self.assertRaises(ValueError):
            solver.quick_odds([6], [9], opp_hidden=6)  # hidden card already in your hand
        with self.assertRaises(ValueError):
            solver.quick_odds([6], [9], ai_profile="nope")


class TestData(unittest.TestCase):
    def test_rule_table_is_valid_json(self):
        path = os.path.join(os.path.dirname(HERE), "hoffman_rule_table.json")
        with open(path, encoding="utf-8") as f:
            self.assertIsInstance(json.load(f), dict)

    def test_opponent_trumps_exist_in_database(self):
        names = set(solver.TRUMPS)
        for opp in solver.OPPONENTS_NORMAL + solver.OPPONENTS_SURVIVAL + solver.OPPONENTS_SURVIVAL_PLUS + [
                solver.BOSS_SURVIVAL_PLUS_MID, solver.BOSS_SURVIVAL_PLUS_FINAL]:
            kits = [opp.get("trumps", [])] + [v.get("trumps", []) for v in opp.get("variants", {}).values()]
            for kit in kits:
                for t in kit:
                    self.assertIn(t, names, f"{opp['name']}: unknown trump {t!r}")


if __name__ == "__main__":
    unittest.main()
