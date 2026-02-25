#!/usr/bin/env python3
"""
RESIDENT EVIL 7: 21 — COMPLETE CARD GAME SOLVER
=================================================
Covers all three game modes from the Banned Footage Vol. 2 DLC:
1. Normal 21
2. Survival 21
3. Survival+ 21

Rules of 21 (RE7 version, simplified for practical play):
- Deck uses cards numbered 1–11 (one of each per round). Deck resets each round.
- Each player is dealt one face-up card, then takes turns drawing.
- Goal: get closer to target (17/21/24/27 depending on active "Go For" trump) without going over.
- In RE7, the loser takes damage based on outcome and trump modifiers.

This helper focuses on:
- Tracking which cards are still in the deck
- Computing safe/bust odds for your next draw
- Providing opponent-specific warnings based on their trump kit
- Keeping a simple round history + HP tracker across fights

Run:
  python3 re7_helper.py
"""

import os
import json
import re

# ============================================================
# GAME MODE DEFINITIONS
# ============================================================
GAME_MODES = {
    "1": {
        "name": "Normal 21",
        "desc": "Single match against Lucas. Learn the basics.",
        "player_hp": 10,
        "opponent_hp": 10,
        "rules": (
            "Standard rules. You play against Lucas.\n"
            "Trump cards are limited. Good for learning mechanics.\n"
            "Winning unlocks Survival mode."
        ),
    },
    "2": {
        "name": "Survival 21",
        "desc": "Gauntlet of 5 Hoffman opponents — finger-chopping mode.",
        "player_hp": 5,
        "opponent_hp": 5,
        "rules": (
            "Finger-chopping mode: you and each opponent have 5 HP (fingers).\n"
            "You face 5 Hoffman variants in a row.\n"
            "Your HP carries over between fights — conserve health!\n"
            "Final opponent (#5) is always Molded Hoffman.\n"
            "Winning unlocks Survival+ mode."
        ),
    },
    "3": {
        "name": "Survival+ 21",
        "desc": "Harder gauntlet: 10 opponents, electric rig, tougher AI.",
        "player_hp": 10,
        "opponent_hp": 10,
        "rules": (
            "Electric rig mode: you and each opponent have 10 HP.\n"
            "You face 10 Hoffman variants in a row.\n"
            "Your HP carries over — every point matters!\n"
            "Opponent order is random EXCEPT:\n"
            "  #5 is ALWAYS Molded Hoffman (mid-boss).\n"
            "  #10 is ALWAYS Undead Hoffman (final boss).\n"
            "  Mr. Big Head may appear randomly.\n"
            "AI is more aggressive, trump cards are deadlier.\n"
            "Completion unlocks 'Perfect Draw' trump and the trophy."
        ),
    },
}

# ============================================================
# OPPONENT DATABASE — Ordered lists per mode
# ============================================================
OPPONENTS_NORMAL = [
    {
        "name": "Lucas",
        "mode": "Normal 21",
        "desc": "Tutorial opponent. 3-round story mode (fingers → shock → saw).",
        "ai": "BASIC",
        "trumps": ["One-Up", "Two-Up", "Shield"],
        "stay_val": 17,
        "hp": 10,
        "tip": (
            "⚠ NOTE: Normal 21 (Lucas story mode) logic is not fully accurate.\n"
            "Lucas cheats in the final saw round (Perfect Draw + Desperation).\n"
            "Counter: Save 'Love Your Enemy' for the last round — it forces him to bust.\n"
            "The solver is optimized for Survival and Survival+ modes."
        ),
    },
]

OPPONENTS_SURVIVAL = [
    {
        "name": "Tally Mark Hoffman",
        "mode": "Survival",
        "desc": "Sack head with tally marks. Basic AI, no special trumps.",
        "ai": "BASIC",
        "trumps": [],
        "standard_trumps": ["One-Up", "Shield"],
        "stay_val": 16,
        "hp": 5,
        "tip": (
            "Easiest opponent. No special trump cards.\n"
            "Play normally and conserve HP.\n"
            "Don't waste strong trumps — save them for later fights."
        ),
    },
    {
        "name": "Bloody Handprints Hoffman",
        "mode": "Survival",
        "desc": "Sack head covered in bloody handprints.",
        "ai": "TRUMP STEALER",
        "trumps": ["Happiness", "Return", "Desire", "Mind Shift"],
        "standard_trumps": ["One-Up", "Shield"],
        "stay_val": 16,
        "hp": 5,
        "tip": (
            "'Mind Shift' makes you lose half your trumps unless\n"
            "you play two trump cards during the round.\n"
            "'Desire' raises your bet based on how many trumps YOU hold.\n"
            "'Happiness' lets both players draw a trump card.\n"
            "STRATEGY: Don't hoard trumps — Desire punishes it.\n"
            "Play two trumps per round to avoid Mind Shift penalty."
        ),
    },
    {
        "name": "Barbed Wire Hoffman",
        "mode": "Survival",
        "desc": "Sack head with barbed wire marks.",
        "ai": "SHIELD SPAMMER",
        "trumps": ["Shield Assault"],
        "standard_trumps": ["Shield", "One-Up"],
        "stay_val": 16,
        "hp": 5,
        "tip": (
            "Packs lots of Shield cards, then sacrifices them.\n"
            "'Shield Assault' removes 3 of his Shields to raise YOUR bet by 3.\n"
            "COUNTER: Use 'Destroy' on Shield Assault.\n"
            "Stack bet-ups to push damage past his shields."
        ),
    },
    {
        "name": "Tally Mark Hoffman (Upgraded)",
        "mode": "Survival",
        "desc": "Upgraded tally mark variant. Smarter AI, more trump cards.",
        "ai": "BASIC+",
        "trumps": [],
        "standard_trumps": ["One-Up", "Two-Up", "Shield"],
        "stay_val": 17,
        "hp": 5,
        "tip": (
            "Slightly smarter than the first Tally Mark.\n"
            "Still no special trumps but plays more strategically.\n"
            "Plays a bit tighter — stay sharp."
        ),
    },
    {
        "name": "Molded Hoffman (Survival Boss)",
        "mode": "Survival",
        "desc": "Head covered in black mold. Final boss of Survival.",
        "ai": "DECK MANIPULATOR",
        "trumps": ["Curse", "Conjure"],
        "standard_trumps": ["One-Up", "Two-Up", "Shield"],
        "stay_val": 17,
        "hp": 5,
        "tip": (
            "!! SURVIVAL BOSS !!\n"
            "'Curse' discards one of your trumps AND forces you to draw\n"
            "the HIGHEST remaining card — can be lethal.\n"
            "'Conjure' lets him draw 3 trumps (his bet goes up by 1).\n"
            "STRATEGY: Save 'Destroy' for Curse.\n"
            "Use 'Return'/'Exchange' to fix a forced bad draw.\n"
            "Winning this unlocks Survival+ mode."
        ),
    },
]

OPPONENTS_SURVIVAL_PLUS = [
    {
        "name": "Tally Mark Hoffman",
        "mode": "Survival+",
        "desc": "Sack head with vertical cut marks.",
        "ai": "BASIC+",
        "stay_val": 17,
        "hp": 10,
        "variants": {
            "2 cuts": {
                "visual_id": "2 vertical slash marks on the sack",
                "trumps": ["One-Up", "Two-Up+", "4 Card", "5 Card", "6 Card", "Twenty-One Up"],
                "tip": (
                    "2-CUT VARIANT:\n"
                    "Trumps: One-Up, Two-Up+, N Cards (lots), Twenty-One Up\n"
                    "'Twenty-One Up' forces YOUR result to be exactly 21 — YOUR bet +21!\n"
                    "'Two-Up+' removes your last face-up card AND raises bet by 2.\n"
                    "Has many numbered card draws to control his hand.\n"
                    "STRATEGY: Keep 'Destroy' for Twenty-One Up — it's a huge bet bomb.\n"
                    "Don't let your total sit near 21 or he'll lock you with it."
                ),
            },
            "3 cuts": {
                "visual_id": "3 vertical slash marks on the sack",
                "trumps": ["4 Card", "One-Up", "Two-Up", "Desire", "Happiness"],
                "tip": (
                    "3-CUT VARIANT:\n"
                    "Trumps: Draw Card, One-Up, Two-Up, Desire, Happiness\n"
                    "Has bet-raising cards (One-Up, Two-Up) — can stack damage.\n"
                    "'Desire' raises YOUR bet by half your trump count.\n"
                    "STRATEGY: Don't hoard trumps. Destroy his bet-ups if stacking."
                ),
            },
        },
        "trumps": ["One-Up", "Two-Up", "Two-Up+", "4 Card", "5 Card", "Desire", "Happiness", "Twenty-One Up"],
        "tip": (
            "Variants based on cut count (select variant at fight start):\n"
            " 2 cuts: One-Up, Two-Up+, N Cards (lots), Twenty-One Up\n"
            " 3 cuts: Draw Card, One-Up, Two-Up, Desire, Happiness\n"
            "STRATEGY: Save Destroy for Twenty-One Up (2-cut) or stack bet-ups (3-cut)."
        ),
    },
    {
        "name": "Bloody Handprints Hoffman",
        "mode": "Survival+",
        "desc": "Sack head with bloody handprints.",
        "ai": "TRUMP STEALER",
        "stay_val": 16,
        "hp": 10,
        "variants": {
            "2 hands": {
                "visual_id": "2 bloody handprints on the sack",
                "trumps": ["Happiness", "Return", "Desire", "Mind Shift"],
                "tip": (
                    "2-HAND VARIANT:\n"
                    "Trumps: Happiness, Return, Desire, Mind Shift\n"
                    "'Mind Shift' — play 2 trumps this round or lose half yours at end.\n"
                    "'Desire' — YOUR bet +half your trump count while it's on table.\n"
                    "'Return' removes your last face-up card (disruption).\n"
                    "STRATEGY: Spend trumps, don't hoard. Play 2/round for Mind Shift."
                ),
            },
            "4 hands": {
                "visual_id": "4 bloody handprints on the sack",
                "trumps": ["4 Card", "Happiness", "Desire+", "Mind Shift+"],
                "tip": (
                    "4-HAND VARIANT (DANGEROUS):\n"
                    "Trumps: Draw Card, Happiness, Desire+, Mind Shift+\n"
                    "'Desire+' — YOUR bet equals your FULL trump count while on table!\n"
                    "'Mind Shift+' — lose ALL your trumps unless you play 3 this round!\n"
                    "STRATEGY: Spend trumps AGGRESSIVELY. Never hold more than 3-4.\n"
                    "This is one of the most punishing non-boss opponents."
                ),
            },
        },
        "trumps": ["4 Card", "Desire", "Desire+", "Mind Shift", "Mind Shift+", "Happiness", "Return"],
        "tip": (
            "Variants based on handprint count (select variant at fight start):\n"
            " 2 hands: Happiness, Return, Desire, Mind Shift\n"
            " 4 hands: Draw Card, Happiness, Desire+, Mind Shift+ (DANGEROUS)\n"
            "STRATEGY: Spend trumps aggressively, never hoard."
        ),
    },
    {
        "name": "Barbed Wire Hoffman",
        "mode": "Survival+",
        "desc": "Sack head with horizontal barbed wire marks.",
        "ai": "SHIELD SPAMMER",
        "stay_val": 14,
        "hp": 10,
        "variants": {
            "3 wires": {
                "visual_id": "3 horizontal barbed wire wraps on the sack",
                "trumps": ["Shield", "Go for 17", "Shield Assault"],
                "tip": (
                    "3-WIRE VARIANT:\n"
                    "Trumps: Shield, Go for 17, Shield Assault\n"
                    "'Shield Assault' — removes 3 of HIS shields, YOUR bet +3.\n"
                    "'Go for 17' — changes target! Your 18+ becomes a bust!\n"
                    "COUNTER: Destroy Shield Assault. Watch for target change."
                ),
            },
            "4 wires": {
                "visual_id": "4 horizontal barbed wire wraps on the sack",
                "trumps": ["Shield", "Shield Assault", "Go for 17", "Two-Up"],
                "tip": (
                    "4-WIRE VARIANT:\n"
                    "Trumps: Shield, Shield Assault, Go for 17, Two-Up\n"
                    "Has Two-Up on top of Shield Assault — more aggressive.\n"
                    "'Go for 17' — changes target! Your 18+ becomes a bust!\n"
                    "COUNTER: Destroy Shield Assault. Stack bet-ups to overwhelm shields."
                ),
            },
        },
        "trumps": ["Shield", "Shield Assault", "Shield Assault+", "Go for 17", "Two-Up"],
        "tip": (
            "Variants based on wire count (select variant at fight start):\n"
            " 3 wires: Shield, Go for 17, Shield Assault\n"
            " 4 wires: Shield, Shield Assault, Go for 17, Two-Up\n"
            "COUNTER: Destroy Shield Assault. Stack bet-ups."
        ),
    },
    {
        "name": "Mr. Big Head Hoffman",
        "mode": "Survival+",
        "desc": "Giant gray cartoon mask, missing right eye. RARE random encounter.",
        "ai": "COWARD / ESCAPE ARTIST",
        "trumps": ["Escape"],
        "stay_val": 19,
        "hp": 10,
        "tip": (
            "RARE ENCOUNTER — special rewards for defeating him!\n"
            "'Escape' lets him void the round if he's losing.\n"
            "As long as Escape is on the table, he flees on loss.\n"
            "STRATEGY: 'Destroy' his Escape, then finish him.\n"
            "Stack bet-ups so when you win, he takes massive damage.\n"
            "He may re-play Escape each round — save multiple Destroys."
        ),
    },
]

# Fixed bosses in Survival+ (always appear at specific positions)
BOSS_SURVIVAL_PLUS_MID = {
    "name": "Molded Hoffman (Mid-Boss)",
    "mode": "Survival+",
    "desc": "Head covered in black mold/fungus. ALWAYS opponent #5.",
    "ai": "DECK MANIPULATOR",
    "trumps": ["Curse", "Black Magic", "Conjure", "Two-Up", "Destroy+", "Go for 17"],
    "stay_val": 17,
    "hp": 10,
    "trump_behavior": {
        "Curse": {"freq": "high", "when": "any", "repeats": True,
                  "note": "Discards your trump + forces highest card. Use Return after to undo."},
        "Black Magic": {"freq": "medium", "when": "mid_round", "repeats": False,
                        "note": "YOUR bet +10 = instant death. MUST Destroy immediately. Max twice per fight."},
        "Conjure": {"freq": "high", "when": "early", "repeats": True,
                    "note": "Draws 3 trumps, his bet +1. The +1 bet is a slight advantage for you."},
        "Destroy+": {"freq": "medium", "when": "reactive", "repeats": True,
                     "note": "Removes all your table trumps. Don't stack too many bet-ups at once."},
        "Go for 17": {"freq": "low", "when": "any", "repeats": True,
                      "note": "Changes target to 17. Your 18+ becomes a bust!"},
    },
    "tip": (
        "!! MID-BOSS — ALWAYS FIGHT #5 !!\n"
        "'Curse' discards one of your trumps AND forces you to draw\n"
        "the HIGHEST remaining card.\n"
        "'Black Magic' discards half your trumps, raises YOUR bet by 10\n"
        "(instant death if you lose!), AND he draws the best card.\n"
        "  Black Magic can only be used MAX TWICE per fight.\n"
        "'Conjure' lets him draw 3 trumps (his bet +1 — slight advantage for you).\n"
        "He also has 'Destroy+' and 'Go for 17'!\n"
        "STRATEGY: Save 'Destroy' for Black Magic (highest priority!).\n"
        "Use 'Return'/'Exchange' to fix forced bad draws.\n"
        "Don't stack all bet-ups at once — his Destroy+ wipes them.\n"
        "Card-count obsessively — know what Curse will force."
    ),
}

BOSS_SURVIVAL_PLUS_FINAL = {
    "name": "Undead Hoffman (Final Boss)",
    "mode": "Survival+",
    "desc": "Knives and scissors embedded in head. ALWAYS opponent #10.",
    "ai": "GAME BREAKER",
    "trumps": ["Ultimate Draw", "Two-Up+", "Perfect Draw+", "Dead Silence", "Oblivion"],
    "stay_val": 18,
    "hp": 10,
    "trump_behavior": {
        "Dead Silence": {"freq": "very_high", "when": "early", "repeats": True,
                         "note": "Uses most often. Will replay after Destroy. Priority Destroy target."},
        "Perfect Draw+": {"freq": "high", "when": "any", "repeats": True,
                          "note": "Almost always gets 21. Opponent bet +5. Very dangerous."},
        "Ultimate Draw": {"freq": "high", "when": "any", "repeats": True,
                          "note": "Gets best card + 2 trumps. Very dangerous."},
        "Oblivion": {"freq": "medium", "when": "losing", "repeats": True,
                     "note": "Cancels the round when losing. Cannot be countered."},
        "Two-Up+": {"freq": "medium", "when": "winning", "repeats": True,
                    "note": "Returns your last card AND raises bet by 2."},
    },
    "tip": (
        "!! FINAL BOSS — MOST DANGEROUS OPPONENT !!\n"
        "'Ultimate Draw' and 'Perfect Draw+' — almost always gets perfect cards.\n"
        "'Dead Silence' prevents you from drawing ANY cards (even via trumps).\n"
        "  He uses Dead Silence REPEATEDLY — save multiple Destroys!\n"
        "'Oblivion' cancels the entire round — wastes your good hands. Cannot be countered.\n"
        "'Two-Up+' returns your last card AND raises bet by 2.\n"
        "STRATEGY:\n"
        " 1) Save 'Destroy' for Dead Silence (highest priority). He WILL replay it.\n"
        " 2) If Dead Silence is up and you cannot Destroy: use Exchange to try busting him.\n"
        " 3) Stack shields — he hits HARD.\n"
        " 4) Be patient — Oblivion wastes rounds but does not hurt you.\n"
        " 5) This fight is luck-heavy. Stay calm, play conservatively."
    ),
}


# ============================================================
# TRUMP CARD DATABASE
# ============================================================
TRUMPS = {
    # ── Bet Up — increases OPPONENT's bet while on table ──
    #   weight: utility value (higher = save for harder fights). 0 = enemy-only card.
    #   etype: "Bet Modifier", "Draw Forcer", "Board Wipe", "Target Modifier", "Defensive", "Special", "Attack"
    "One-Up": {"cat": "Bet", "desc": "Opponent's bet +1 while on table. Also, draw 1 trump card.", "weight": 10, "etype": "Bet Modifier"},
    "Two-Up": {"cat": "Bet", "desc": "Opponent's bet +2 while on table. Also, draw 1 trump card.", "weight": 20, "etype": "Bet Modifier"},
    "Two-Up+": {"cat": "Bet", "desc": "Return opponent's last face-up card to deck. Opponent's bet +2 while on table.", "weight": 50, "etype": "Bet Modifier"},

    # ── Draw Number Card — draw a specific numbered card ──
    "2 Card": {"cat": "Cards", "desc": "Draw the 2 card. If not in deck, nothing happens.", "weight": 15, "etype": "Draw Forcer"},
    "3 Card": {"cat": "Cards", "desc": "Draw the 3 card. If not in deck, nothing happens.", "weight": 15, "etype": "Draw Forcer"},
    "4 Card": {"cat": "Cards", "desc": "Draw the 4 card. If not in deck, nothing happens.", "weight": 15, "etype": "Draw Forcer"},
    "5 Card": {"cat": "Cards", "desc": "Draw the 5 card. If not in deck, nothing happens.", "weight": 15, "etype": "Draw Forcer"},
    "6 Card": {"cat": "Cards", "desc": "Draw the 6 card. If not in deck, nothing happens.", "weight": 15, "etype": "Draw Forcer"},
    "7 Card": {"cat": "Cards", "desc": "Draw the 7 card. If not in deck, nothing happens.", "weight": 15, "etype": "Draw Forcer"},

    # ── Remove/Return/Swap ──
    "Remove": {"cat": "Cards", "desc": "Remove an opponent's face-up card from play for this round (it becomes a dead card).", "weight": 45, "etype": "Draw Forcer"},
    "Return": {"cat": "Cards", "desc": "Return your last face-up card to the deck.", "weight": 40, "etype": "Draw Forcer"},
    "Exchange": {"cat": "Cards", "desc": "Swap the last face-up cards drawn by you and opponent. Face-down cards can't be swapped.", "weight": 75, "etype": "Draw Forcer"},

    # ── Trump Management ──
    "Trump Switch": {"cat": "Switch", "desc": "Discard 2 of your trumps at random, draw 3 trumps. Works even with <2 trumps.", "weight": 20, "etype": "Special"},
    "Trump Switch+": {"cat": "Switch", "desc": "Discard 1 of your trumps at random, draw 4 trumps. Works even with 0 other trumps.", "weight": 30, "etype": "Special"},

    # ── Defense — reduces YOUR bet while on table ──
    "Shield": {"cat": "Defense", "desc": "Your bet -1 while on table.", "weight": 10, "etype": "Defensive"},
    "Shield+": {"cat": "Defense", "desc": "Your bet -2 while on table.", "weight": 20, "etype": "Defensive"},

    # ── Counter / Destroy ──
    "Destroy": {"cat": "Counter", "desc": "Remove opponent's last trump card from the table.", "weight": 60, "etype": "Board Wipe"},
    "Destroy+": {"cat": "Counter", "desc": "Remove ALL opponent's trump cards from the table.", "weight": 90, "etype": "Board Wipe"},
    "Destroy++": {"cat": "Counter", "desc": "Remove ALL opponent's trumps. Opponent can't use trumps while on table.", "weight": 100, "etype": "Board Wipe"},

    # ── Best Card Draw ──
    "Perfect Draw": {"cat": "Cards", "desc": "Draw the best possible card from the deck.", "weight": 80, "etype": "Draw Forcer"},
    "Perfect Draw+": {"cat": "Cards", "desc": "Draw the best possible card. Opponent's bet +5 while on table.", "weight": 90, "etype": "Draw Forcer"},
    "Ultimate Draw": {"cat": "Cards", "desc": "Draw the best possible card. Also, draw 2 trump cards.", "weight": 100, "etype": "Draw Forcer"},

    # ── Target Changers ──
    "Go for 24": {"cat": "Target", "desc": "Closest to 24 wins while on table. Replaces other 'Go For' cards.", "weight": 35, "etype": "Target Modifier"},
    "Go for 27": {"cat": "Target", "desc": "Closest to 27 wins while on table. Replaces other 'Go For' cards.", "weight": 40, "etype": "Target Modifier"},

    # ── Trump Draw ──
    "Harvest": {"cat": "Switch", "desc": "Draw a trump card after every trump you use while on table.", "weight": 50, "etype": "Special"},
    "Love Your Enemy": {"cat": "Cards", "desc": "Opponent draws the best possible card for THEM from the deck.", "weight": 60, "etype": "Draw Forcer"},

    # ── Enemy-exclusive trump cards (weight 0 = not player-obtainable) ──
    "Happiness": {"cat": "Switch", "desc": "Both players draw 1 trump card.", "weight": 0, "etype": "Attack"},
    "Desire": {"cat": "Attack", "desc": "YOUR bet +half YOUR trump count while on table.", "weight": 0, "etype": "Attack"},
    "Desire+": {"cat": "Attack", "desc": "YOUR bet +YOUR full trump count while on table.", "weight": 0, "etype": "Attack"},
    "Mind Shift": {
        "cat": "Attack",
        "desc": "You lose half trumps end of round (removed if you play 2+ this round).",
        "weight": 0, "etype": "Attack",
    },
    "Mind Shift+": {
        "cat": "Attack",
        "desc": "You lose ALL trumps end of round (removed if you play 3+ this round).",
        "weight": 0, "etype": "Attack",
    },
    "Shield Assault": {
        "cat": "Attack",
        "desc": "Enemy removes 3 of HIS Shields. YOUR bet +3 while on table.",
        "weight": 0, "etype": "Attack",
    },
    "Shield Assault+": {
        "cat": "Attack",
        "desc": "Enemy removes 2 of HIS Shields. YOUR bet +5 while on table.",
        "weight": 0, "etype": "Attack",
    },
    "Curse": {"cat": "Attack", "desc": "Removes a random trump from YOU. You draw the highest card in deck.", "weight": 0, "etype": "Attack"},
    "Black Magic": {
        "cat": "Attack",
        "desc": "Removes half YOUR trumps. YOUR bet +10. Enemy draws best card. MAX TWICE per fight.",
        "weight": 0, "etype": "Attack",
    },
    "Conjure": {"cat": "Attack", "desc": "Enemy draws 3 trumps. Enemy's bet +1 while on table.", "weight": 0, "etype": "Attack"},
    "Dead Silence": {"cat": "Attack", "desc": "You CANNOT draw cards (including via trump effects) while on table.", "weight": 0, "etype": "Attack"},
    "Twenty-One Up": {"cat": "Attack", "desc": "Your result must be exactly 21. YOUR bet +21 while on table.", "weight": 0, "etype": "Attack"},
    "Go for 17": {"cat": "Target", "desc": "Closest to 17 wins while on table. (Also used by enemies!)", "weight": 30, "etype": "Target Modifier"},

    # ── Special ──
    "Escape": {"cat": "Special", "desc": "Enemy doesn't take damage if they lose while on table. Round resets.", "weight": 0, "etype": "Special"},
    "Oblivion": {"cat": "Special", "desc": "Cancels this round. Begins a new round. No damage to either side.", "weight": 0, "etype": "Special"},
    "Desperation": {"cat": "Special", "desc": "Story-only. Both bets become 100. Opponent can't draw cards.", "weight": 0, "etype": "Special"},
}

# ============================================================
# CHALLENGE / UNLOCK TRACKING
# ============================================================
CHALLENGE_GOALS = {
    "beat_normal": {
        "name": "Beat Normal 21 (story mode)",
        "reward": "Unlocks Survival mode",
        "unlocks_trumps": [],
    },
    "beat_survival": {
        "name": "Beat Survival mode",
        "reward": "Unlocks Survival+ mode, Perfect Draw+",
        "unlocks_trumps": ["Perfect Draw+"],
    },
    "beat_survival_plus": {
        "name": "Beat Survival+ mode",
        "reward": "Achievement: You Gotta Know When To Hold 'Em",
        "unlocks_trumps": [],
    },
    "bust_win": {
        "name": "Win a round while bust",
        "reward": "Starting Trump Card +1",
        "unlocks_trumps": [],
    },
    "fifteen_trumps": {
        "name": "Use 15+ trump cards in a single round",
        "reward": "Trump Switch+",
        "unlocks_trumps": ["Trump Switch+"],
    },
    "no_damage_survival": {
        "name": "Beat Survival without taking damage",
        "reward": "Ultimate Draw",
        "unlocks_trumps": ["Ultimate Draw"],
    },
    "no_damage_survival_plus": {
        "name": "Beat Survival+ without taking damage",
        "reward": "Grand Reward",
        "unlocks_trumps": [],
    },
    "three_21s": {
        "name": "Reach exactly 21 three times in a row",
        "reward": "Go for 27",
        "unlocks_trumps": ["Go for 27"],
    },
    "opponents_defeated": {
        "name": "Defeat multiple opponents (cumulative)",
        "reward": "Shield+, Two Up+, Go for 24 (at milestones)",
        "unlocks_trumps": ["Shield+", "Two-Up+", "Go for 24"],
    },
}


def setup_challenge_progress(force_prompt=False):
    """Ask which challenges are completed at session start. Returns set of completed keys."""
    # Try loading from disk first
    if not force_prompt:
        saved_challenges, saved_trumps = load_progress()
        if saved_challenges is not None:
            print(f"\n ✓ Loaded save: {len(saved_challenges)} challenges completed")
            if saved_trumps:
                print(f"   Unlocked trumps: {', '.join(sorted(saved_trumps))}")
            print("   (Press U from main menu to update)")
            return saved_challenges, saved_trumps

    completed = set()
    print_header("CHALLENGE PROGRESS")
    print(" Which challenges have you already completed?")
    print(" (This determines which trump cards you have access to)\n")

    challenges = list(CHALLENGE_GOALS.items())
    for i, (key, goal) in enumerate(challenges, 1):
        print(f" {i:>2}. {goal['name']}")
        print(f"      → {goal['reward']}")

    print(f"\n Enter numbers for COMPLETED challenges (e.g., '1 2 5'), or 'all', or Enter for none:")
    raw = input(" > ").strip().lower()

    if raw == "all":
        completed = set(CHALLENGE_GOALS.keys())
    elif raw:
        try:
            indices = [int(x) for x in raw.split()]
            for idx in indices:
                if 1 <= idx <= len(challenges):
                    completed.add(challenges[idx - 1][0])
        except ValueError:
            print(" Couldn't parse input, starting with no challenges completed.")

    # Derive available trump cards from completed challenges
    available_trumps = set()
    for key in completed:
        goal = CHALLENGE_GOALS.get(key, {})
        available_trumps.update(goal.get("unlocks_trumps", []))

    if completed:
        print(f"\n Completed: {len(completed)} challenges")
        if available_trumps:
            print(f" Unlocked trumps: {', '.join(sorted(available_trumps))}")
    else:
        print("\n No challenges completed yet.")

    # Auto-save
    save_progress(completed, available_trumps)

    return completed, available_trumps


# ============================================================
# SAVE / LOAD SYSTEM
# ============================================================
import json

SAVE_FILE = os.path.join(os.path.expanduser("~"), ".re7_21_progress.json")


def save_progress(challenges_completed: set, available_trumps: set) -> None:
    """Persist challenge progress to disk."""
    data = {
        "challenges_completed": sorted(challenges_completed),
        "available_trumps": sorted(available_trumps),
    }
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f, indent=2)
        print(f" ✓ Progress saved to {SAVE_FILE}")
    except OSError as e:
        print(f" ⚠ Could not save: {e}")


def load_progress():
    """Load challenge progress from disk. Returns (challenges, trumps) or (None, None)."""
    try:
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
        challenges = set(data.get("challenges_completed", []))
        trumps = set(data.get("available_trumps", []))
        return challenges, trumps
    except (OSError, json.JSONDecodeError, KeyError):
        return None, None


# ============================================================
# BANKER AI — Real parameters from CardGameBanker.hpp
# ============================================================
# Source: app::CardGameBanker reverse-engineered fields:
#   BankerTakeCardBorder (0x54) — hard draw threshold: banker draws below this
#   BankerHandGoodBorder (0x50) — upper threshold: banker "satisfied" above this
#   IsBankerChicken      (0x58) — conservative/passive mode flag
#   PlayerHandGoodLow/High (0x5C/0x60) — range banker reads as player "dangerous"
#   PlayerHandBadLow/High  (0x64/0x68) — range banker reads as player "weak"
#
# Reconstructed draw logic:
#   1. banker_total < BankerTakeCardBorder  → ALWAYS draw  (hard floor)
#   2. banker_total >= BankerHandGoodBorder → ALWAYS stay  (satisfied)
#   3. In the gray zone [TakeCardBorder, HandGoodBorder):
#      • IsBankerChicken=True → nearly always stay (relies on shields/trumps)
#      • Player hand in "bad" range → stay (let player bust or fail)
#      • Player hand in "good" range → draw (must improve to beat them)
#      • Otherwise → probabilistic based on position in zone
#
# ┌──────────────────────────────────────────────────────────────┐
# │ RANDOMNESS FINDINGS (CardGameItemTable.hpp + CardGameMaster) │
# │                                                              │
# │ FIXED per opponent:                                          │
# │  • Which trump cards can appear   → loaded from UserData     │
# │    asset files (CardGameItemTableParamList, CardGameItemTable)│
# │  • When conditions allow a trump  → CardGameCondition fields  │
# │    are static per opponent (round, hand sum, item counts…)   │
# │                                                              │
# │ RANDOMIZED each session:                                     │
# │  • Trump deal ORDER → RandomIndexList (confirmed in header)  │
# │  • Numbered cards (1–11) → shuffled via Unity RNG each round │
# │    CardGameMaster.StockCardList is reshuffled per round      │
# │                                                              │
# │ IMPLICATION: You can't predict which card or trump is next,  │
# │ but you CAN predict WHEN conditions make a trump eligible.   │
# └──────────────────────────────────────────────────────────────┘

class BankerAI:
    """
    Real banker AI parameter set from app::CardGameBanker.
    Models the full draw/stay decision including player-hand awareness.
    """
    __slots__ = (
        "take_card_border", "hand_good_border", "is_chicken",
        "player_good_low", "player_good_high",
        "player_bad_low",  "player_bad_high",
    )

    def __init__(self, take_card_border, hand_good_border, is_chicken,
                 player_good_low, player_good_high, player_bad_low, player_bad_high):
        self.take_card_border = take_card_border
        self.hand_good_border = hand_good_border
        self.is_chicken       = is_chicken
        self.player_good_low  = player_good_low
        self.player_good_high = player_good_high
        self.player_bad_low   = player_bad_low
        self.player_bad_high  = player_bad_high

    def draw_probability(self, banker_total: int, player_visible_total: int, target: int = 21) -> float:
        """
        Returns probability (0.0–1.0) that banker draws another card in this state.
        Uses all six CardGameBanker fields to model the real decision tree.
        """
        if banker_total >= target:
            return 0.0   # Bust — can't draw
        if banker_total < self.take_card_border:
            return 1.0   # Hard floor — always draws below threshold
        if banker_total >= self.hand_good_border:
            return 0.0   # Hard ceiling — fully satisfied

        # ── Gray zone: [take_card_border, hand_good_border) ──
        if self.is_chicken:
            # Chicken mode: passive, relies on shields/trumps not hand strength
            return 0.05

        player_is_bad  = self.player_bad_low  <= player_visible_total <= self.player_bad_high
        player_is_good = self.player_good_low <= player_visible_total <= self.player_good_high

        if player_is_bad:
            # Player looks weak — banker happy to let them fail
            return 0.15
        if player_is_good:
            # Player looks dangerous — banker needs to improve
            return 0.80

        # Neutral player total: scale down linearly through the gray zone
        zone_width = max(1, self.hand_good_border - self.take_card_border)
        pos_in_zone = banker_total - self.take_card_border
        return max(0.10, 0.65 * (1.0 - pos_in_zone / zone_width))

    def describe(self) -> str:
        chicken_str = " │ ⚠ CHICKEN MODE (passive — relies on shields/trumps)" if self.is_chicken else ""
        return (
            f"Draws below {self.take_card_border} | Satisfied at {self.hand_good_border}+{chicken_str}\n"
            f"  Reads YOUR hand as 'dangerous': {self.player_good_low}–{self.player_good_high}  "
            f"'weak': {self.player_bad_low}–{self.player_bad_high}"
        )


# Per-opponent AI profiles — values inferred from CardGameBanker field patterns
# and cross-referenced with each opponent's observed behavior and trump kit
BANKER_AI_PROFILES = {
    # ── Normal mode ──
    "lucas":            BankerAI(17, 19, False, 17, 21,  1, 12),

    # ── Survival mode ──
    "tally_basic":      BankerAI(16, 18, False, 17, 21,  1, 12),
    "bloody_survival":  BankerAI(16, 19, False, 16, 21,  1, 13),
    "barbed_survival":  BankerAI(16, 17, True,  18, 21,  1, 14),  # chicken=True: relies on Shield Assault
    "tally_upgraded":   BankerAI(17, 19, False, 17, 21,  1, 12),
    "molded_survival":  BankerAI(17, 20, False, 16, 21,  1, 13),

    # ── Survival+ random pool ──
    "tally_s_plus":     BankerAI(17, 20, False, 16, 21,  1, 12),
    "bloody_s_plus":    BankerAI(16, 19, False, 16, 21,  1, 13),
    "barbed_3w":        BankerAI(14, 16, True,  18, 21,  1, 14),  # chicken=True, very low threshold
    "barbed_4w":        BankerAI(14, 17, True,  18, 21,  1, 14),
    "mr_big_head":      BankerAI(19, 21, False, 18, 21,  1, 14),  # aggressive — Escape is safety net

    # ── Survival+ bosses ──
    "molded_mid":       BankerAI(17, 20, False, 16, 21,  1, 13),
    "molded_final":     BankerAI(18, 21, False, 15, 21,  1, 12),  # most aggressive
}

# Map opponent names → profile key (used by fight_opponent to look up BankerAI)
OPPONENT_AI_MAP = {
    "Lucas":                          "lucas",
    "Tally Mark Hoffman":             "tally_basic",
    "Bloody Handprints Hoffman":      "bloody_survival",
    "Barbed Wire Hoffman":            "barbed_survival",
    "Tally Mark Hoffman (Upgraded)":  "tally_upgraded",
    "Molded Hoffman (Survival Boss)": "molded_survival",
    # Survival+ — variant selection happens in fight, map to base keys
    "Mr. Big Head Hoffman":           "mr_big_head",
    "Molded Hoffman (Mid-Boss)":      "molded_mid",
    "Undead Hoffman (Final Boss)":    "molded_final",
}

def get_banker_ai(intel: dict, variant_key: str = None) -> BankerAI:
    """Look up BankerAI profile for an opponent. Falls back to stay_val-based generic."""
    name = intel.get("name", "")
    # Variant overrides (Barbed Wire and Bloody Handprints S+ have distinct profiles)
    if variant_key:
        if variant_key in BANKER_AI_PROFILES:
            return BANKER_AI_PROFILES[variant_key]
    profile_key = OPPONENT_AI_MAP.get(name)
    if profile_key and profile_key in BANKER_AI_PROFILES:
        return BANKER_AI_PROFILES[profile_key]
    # Generic fallback using stay_val from opponent entry
    stay = int(intel.get("stay_val", 17))
    return BankerAI(stay, stay + 2, False, 17, 21, 1, 12)


# ============================================================
# TRUMP CONDITION ENGINE — From CardGameCondition.hpp
# ============================================================
# CardGameCondition gates WHEN each enemy trump is eligible to fire.
# It checks 14 state fields: Round, PlayerFinger, BankerFinger, BankerHandSum,
# BankerCantSeeCard, PlayerItemNum, BankerItemNum, PlayerLastTakeCardNo,
# BankerLastTakeCardNo, PlayerTableItemNum, BankerTableItemNum, KillCount,
# IsBankerTakeCard, and more.
#
# This class tracks those fields and returns likelihood assessments per trump.

class TrumpConditionState:
    """
    Mirrors the CardGameCondition state variables.
    Update each round for accurate trump timing predictions.
    """
    def __init__(self):
        self.round: int          = 1
        self.player_finger: int  = 5    # fingers remaining (Survival mode)
        self.banker_finger: int  = 5
        self.banker_hand_sum: int= 0    # banker's current total
        self.player_hand_sum: int= 0    # player's visible total
        self.kill_count: int     = 0    # Survival+ kill counter
        self.banker_item_num: int= 0    # trump cards banker currently holds
        self.player_item_num: int= 0    # trump cards player currently holds
        self.banker_took_card: bool = False   # did banker draw this turn?
        self.black_magic_uses: int = 0  # tracks max-2 Black Magic uses
        self.banker_items_used_round: int = 0  # trumps banker used this round
        self.player_betup_active: bool = False # true if YOUR bet > 1 this round
        self.banker_last_faceup: int = 0       # last visible banker card (0=unknown)
        self.banker_visible_count: int = 0     # number of visible banker cards

    def update(self, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)

    def trump_fire_likelihood(self, trump_name: str) -> tuple:
        """
        Returns (level_str, reason) predicting whether a trump condition is currently met.
        Levels: VERY HIGH | HIGH | MEDIUM | LOW
        Based on CardGameCondition field patterns for each trump type.
        """
        r   = self.round
        bhs = self.banker_hand_sum
        phs = self.player_hand_sum
        bi  = self.banker_item_num
        pi  = self.player_item_num

        if trump_name == "Curse":
            # Condition: BankerHandSum is low (banker needs to punish you to compensate)
            if bhs <= 13:
                return ("VERY HIGH", f"Banker total is only {bhs} — Curse forces you to draw the highest card!")
            if bhs <= 16 and phs >= 17:
                return ("HIGH", f"Banker at {bhs} vs your {phs} — Curse likely to hurt your position")
            return ("LOW", "Banker hand is decent — Curse less likely right now")

        if trump_name == "Black Magic":
            # Condition: desperation trump, fires max 2x, when banker is losing badly
            if self.black_magic_uses >= 2:
                return ("NONE", "Black Magic has already fired twice this fight — exhausted")
            if bhs < phs - 3 and r >= 2:
                return ("HIGH", f"Banker behind by {phs - bhs} pts in round {r} — Black Magic incoming! SAVE DESTROY!")
            if r >= 3 and bhs < 16:
                return ("MEDIUM", "Late round, banker has weak hand — possible Black Magic")
            return ("LOW", "Banker not desperate enough yet — but keep a Destroy ready")

        if trump_name == "Conjure":
            # Condition: BankerItemNum is low, typically early rounds
            if bi <= 1 and r <= 3:
                return ("VERY HIGH", f"Banker has only {bi} trumps in round {r} — Conjure to restock (draws 3)")
            if bi <= 3:
                return ("MEDIUM", f"Banker has {bi} trumps — may Conjure to restock")
            return ("LOW", f"Banker already has {bi} trumps — Conjure less likely")

        if trump_name == "Dead Silence":
            # Condition: IsBankerTakeCard check — fires when player would benefit from drawing
            if phs < 16:
                return ("VERY HIGH", f"Your hand is {phs} — Dead Silence will lock you here. DESTROY IT FIRST!")
            if phs < 19:
                return ("HIGH", f"At {phs} — Dead Silence to stop your improvement")
            return ("MEDIUM", "Even with a strong hand he may use Dead Silence to deny trumps")

        if trump_name == "Escape":
            # Condition: banker predicts loss — BankerHandSum < player eval
            if bhs < phs:
                return ("HIGH", f"Banker at {bhs} vs your {phs} — Escape will void this round if you win!")
            if bhs < 16:
                return ("MEDIUM", "Banker hand weak — may Escape preemptively before you stack bets")
            return ("LOW", "Banker hand decent — Escape unlikely this turn")

        if trump_name in ("Mind Shift", "Mind Shift+"):
            needed = 3 if "+" in trump_name else 2
            if pi >= 5:
                return ("VERY HIGH", f"You have {pi} trumps — {trump_name} will cost you heavily! Play {needed}+ NOW!")
            if pi >= 3:
                return ("HIGH", f"You have {pi} trumps — play {needed} this round to nullify {trump_name}")
            if pi >= 2:
                return ("MEDIUM", f"You have {pi} trumps — {trump_name} possible, try to play {needed}")
            return ("LOW", f"Only {pi} trumps — {trump_name} damage is minimal")

        if trump_name in ("Desire", "Desire+"):
            scale = pi if "+" in trump_name else pi // 2
            if pi >= 5:
                return ("VERY HIGH", f"{pi} trumps = +{scale} to YOUR bet — dump cheap trumps immediately!")
            if pi >= 3:
                return ("HIGH", f"You have {pi} trumps — {trump_name} adds {scale} to your bet. Burn cheap ones.")
            return ("LOW", f"Low trump count ({pi}) — {trump_name} impact is minimal")

        if trump_name in ("Shield Assault", "Shield Assault+"):
            shields = 2 if "+" in trump_name else 3
            return ("MEDIUM", f"Fires when banker sacrifices {shields} shields — your bet jumps high. Stack bet-ups to overwhelm.")

        if trump_name == "Happiness":
            if bi <= 2 or pi <= 1:
                return ("HIGH", f"One/both players low on trumps (banker:{bi}, you:{pi}) — Happiness to mutual restock")
            return ("MEDIUM", "Happiness may fire for tempo even with decent trump counts")

        if trump_name == "Go for 17":
            if bhs == 17:
                return ("VERY HIGH", "Banker is AT 17 — Go for 17 wins the round immediately if played!")
            if bhs >= 15:
                return ("HIGH", "Banker approaching 17 — Go for 17 incoming if they hit it")
            return ("LOW", "Banker not near 17 yet")

        return ("UNKNOWN", "No condition model for this trump")


# ============================================================
# HOFFMAN SURVIVAL AI — JSON RULE TABLE ENGINE
# ============================================================
# Decodes the enemy's "thinkset" (Attacker / Defence / Tricky / Molded / LassBoss / Rare)
# and evaluates the priority-ordered trump rules extracted from hoffmans/*.fsm.16.
# Falls back to the CardGameCondition timing engine as a backstop.

HOFFMAN_TRUMP_ALIASES = {
    "Perfect Draw+": "Perfect Draw",
    "Desire+":       "Desire",
    "Mind Shift+":   "Mind Shift",
}

def _norm_trump(name: str) -> str:
    return HOFFMAN_TRUMP_ALIASES.get(name, name)


def infer_hoffman_thinkset(intel: dict) -> str:
    """Map opponent trump kit → game thinkset name used by the Hoffman FSMs."""
    trumps = {_norm_trump(t) for t in (intel.get("trumps", []) + intel.get("standard_trumps", []))}
    name   = intel.get("name", "")
    if {"Dead Silence", "Oblivion"} & trumps or "Undead" in name:
        return "LassBoss"
    if trumps == {"Escape"} or ("Big Head" in name and "Escape" in trumps):
        return "Rare"
    if {"Curse", "Black Magic", "Conjure"} & trumps or "Molded" in name:
        return "Molded"
    if "Shield Assault" in trumps:
        return "Defence"
    if {"Mind Shift", "Desire", "Happiness"} & trumps:
        return "Tricky"
    return "Attacker"


_HOFFMAN_RULE_TABLE_CACHE = None

def _load_hoffman_rule_table() -> dict:
    global _HOFFMAN_RULE_TABLE_CACHE
    if _HOFFMAN_RULE_TABLE_CACHE is not None:
        return _HOFFMAN_RULE_TABLE_CACHE
    here = os.path.dirname(os.path.abspath(__file__))
    for candidate in [
        "Hoffman rule table.v2.json",
        "Hoffman rule table.full.v2.json",
        "Hoffman rule table.json",
    ]:
        p = os.path.join(here, candidate)
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    _HOFFMAN_RULE_TABLE_CACHE = json.load(f)
                    return _HOFFMAN_RULE_TABLE_CACHE
            except Exception:
                pass
    _HOFFMAN_RULE_TABLE_CACHE = {}
    return _HOFFMAN_RULE_TABLE_CACHE


def _token_to_display(token: str) -> str:
    """Convert internal FSM tokens like 'SheildAssalt' → 'Shield Assault'."""
    if not token:
        return token
    t = token.replace("Sheild", "Shield").replace("Assalt", "Assault").replace("Ovlivion", "Oblivion")
    for pref in ("Use", "Has", "Check_", "Check"):
        if t.startswith(pref):
            t = t[len(pref):]
            break
    t = re.sub(r"[_\-]+", " ", t)
    t = re.sub(r"(?<!^)([A-Z])", r" \1", t).strip()
    return re.sub(r"\s+", " ", t)


def _action_to_trump_name(action: str, action_defs: dict) -> str:
    if not action:
        return None
    meta = (action_defs or {}).get(action, {}) or {}
    effect = meta.get("effect")
    if effect == "set_target":
        return f"Go For {meta.get('target', '?')}"
    if effect == "draw_n":
        return f"Draw {meta.get('n', '?')}"
    if effect == "bet_up":
        return f"Bet Up (+{meta.get('amount', '?')})"
    if effect == "bet_down":
        return f"Bet Down (-{meta.get('amount', '?')})"
    effect_map = {
        "desire": "Desire", "happiness": "Happiness", "mind_shift": "Mind Shift",
        "curse": "Curse", "conjure": "Conjure", "dead_silence": "Dead Silence",
        "oblivion": "Oblivion", "escape": "Escape", "perfect_draw": "Perfect Draw",
        "shield_assault": "Shield Assault", "destroy": "Destroy",
    }
    if effect in effect_map:
        return effect_map[effect]
    m = re.match(r"UseGoal(\d+)$", action)
    if m:
        return f"Go For {m.group(1)}"
    return _token_to_display(action)


def _enemy_has_token(enemy_trumps: list, token: str) -> bool:
    if not token:
        return True
    want = _token_to_display(token).lower()
    if want.startswith("goal "):
        want = want.replace("goal ", "go for ")
    if not enemy_trumps:
        return True  # unknown kit — don't block prediction
    for t in enemy_trumps:
        if _norm_trump(t).lower() == want:
            return True
        if want in _norm_trump(t).lower():
            return True
    return False


def _eval_check(check_name: str, ctx: dict, check_defs: dict) -> bool:
    if not check_name:
        return True
    defs  = (check_defs or {}).get(check_name) or {}
    ctype = defs.get("type")
    bk    = ctx.get("bk_total")
    pl    = ctx.get("pl_total")
    last  = ctx.get("bk_last_faceup")
    try:
        if ctype == "bk_total_lte":
            return bk is not None and bk <= int(defs["value"])
        if ctype == "bk_total_eq":
            return bk is not None and bk == int(defs["value"])
        if ctype == "bk_total_gte":
            return bk is not None and bk >= int(defs["value"])
        if ctype == "bk_total_range_inclusive":
            return bk is not None and int(defs["min"]) <= bk <= int(defs["max"])
        if ctype == "player_total_gte":
            return pl is not None and pl >= int(defs["value"])
        if ctype == "player_trumps_gte":
            return int(ctx.get("pl_trumps", 0) or 0) >= int(defs["value"])
        if ctype == "last_faceup_range_inclusive":
            return last is not None and int(defs["min"]) <= last <= int(defs["max"])
        if ctype == "player_betup_active":
            return bool(ctx.get("player_betup_active", False))
        if ctype == "enemy_can_use_item":
            return int(ctx.get("bk_items_used_round", 0) or 0) < 1
        if ctype == "enemy_hand_count_gte":
            vis    = int(ctx.get("bk_visible_count", 0) or 0)
            hidden = 1 if vis > 0 else 0
            return (vis + hidden) >= int(defs["value"])
    except Exception:
        return False
    # Pattern fallback for inline check names like Check_21_19, Check_16_0
    m = re.match(r"Check_(\d+)_(\d+)$", check_name)
    if m and bk is not None:
        lo, hi = sorted([int(m.group(1)), int(m.group(2))])
        return lo <= bk <= hi
    m = re.match(r"Check_(\d+)_0$", check_name)
    if m and bk is not None:
        return bk <= int(m.group(1))
    return False


def _rule_matches(rule: dict, enemy_trumps: list, ctx: dict, check_defs: dict) -> bool:
    for cond in rule.get("when", []):
        if "has" in cond:
            if not _enemy_has_token(enemy_trumps, cond["has"]):
                return False
        elif "check" in cond:
            if not _eval_check(cond["check"], ctx, check_defs):
                return False
        elif "items_used_lt" in cond:
            used = int(ctx.get("bk_items_used_round", 0) or 0)
            if not (used < int(cond["items_used_lt"])):
                return False
        else:
            return False  # unknown condition type — be conservative
    return True


def _level_to_score(level: str) -> int:
    return {"VERY HIGH": 100, "HIGH": 70, "MEDIUM": 40, "LOW": 10, "NONE": 0}.get(level, 0)


def predict_enemy_trump(intel: dict, condition_state: "TrumpConditionState") -> tuple:
    """
    Returns (trump_name_or_None, confidence_str, reason).
    First evaluates the Hoffman rule-table JSON (actual FSM priority rules),
    then blends the CardGameCondition timing engine as a backstop.
    """
    enemy_trumps = [_norm_trump(t) for t in (intel.get("trumps", []) + intel.get("standard_trumps", []))]
    if condition_state is None:
        return (None, "LOW", "No condition state available.")

    ctx = {
        "bk_total":            int(getattr(condition_state, "banker_hand_sum", 0) or 0),
        "pl_total":            int(getattr(condition_state, "player_hand_sum", 0) or 0),
        "pl_trumps":           int(getattr(condition_state, "player_item_num", 0) or 0),
        "bk_trumps":           int(getattr(condition_state, "banker_item_num", 0) or 0),
        "bk_items_used_round": int(getattr(condition_state, "banker_items_used_round", 0) or 0),
        "player_betup_active": bool(getattr(condition_state, "player_betup_active", False)),
        "bk_last_faceup":      getattr(condition_state, "banker_last_faceup", None),
        "bk_visible_count":    int(getattr(condition_state, "banker_visible_count", 0) or 0),
    }
    thinkset    = infer_hoffman_thinkset(intel)
    table       = _load_hoffman_rule_table() or {}
    rules       = table.get("rules") or {}
    check_defs  = table.get("check_definitions") or {}
    action_defs = table.get("action_definitions") or {}

    # Evaluate JSON rules in priority order (lower number = higher priority)
    hoffman_pick = hoffman_reason = None
    hoffman_conf = "LOW"
    ts_rules = rules.get(thinkset) or rules.get(f"{thinkset}_p") or []
    if ts_rules:
        for rule in sorted(ts_rules, key=lambda r: int(r.get("priority", 9999))):
            if _rule_matches(rule, enemy_trumps, ctx, check_defs):
                action       = (rule.get("then") or {}).get("do")
                hoffman_pick = _action_to_trump_name(action, action_defs)
                prio         = int(rule.get("priority", 9999))
                hoffman_conf = "HIGH" if prio <= 15 else ("MEDIUM" if prio <= 40 else "LOW")
                hoffman_reason = f"[{thinkset}] rule '{rule.get('id', '?')}' (prio {prio})"
                break

    # Timing engine backstop
    best_by_condition = None
    best_score        = -1
    best_reason       = ""
    for trump in enemy_trumps:
        level, reason = condition_state.trump_fire_likelihood(trump)
        score = _level_to_score(level)
        if score > best_score:
            best_score        = score
            best_by_condition = trump
            best_reason       = f"{trump} [{level}]: {reason}"

    if hoffman_pick:
        if best_by_condition and best_by_condition != hoffman_pick and best_score >= 85:
            return (
                hoffman_pick,
                "MEDIUM" if hoffman_conf == "HIGH" else hoffman_conf,
                hoffman_reason + f" | timing strongly favors {best_reason}",
            )
        return (hoffman_pick, hoffman_conf, hoffman_reason)

    conf = "HIGH" if best_score >= 90 else ("MEDIUM" if best_score >= 55 else "LOW")
    if best_by_condition:
        return (best_by_condition, conf, best_reason)
    return (None, "LOW", "No matching rules / no trump candidates.")
# ============================================================
# Player-obtainable trump cards (cards the player can actually hold/draw)
# Excludes enemy-only cards: Escape, Oblivion, Go for 17, Happiness,
# Desire/+, Mind Shift/+, Shield Assault/+, Curse, Black Magic,
# Conjure, Dead Silence, Twenty-One Up, Desperation
PLAYER_TRUMPS = [
    "One-Up", "Two-Up", "Two-Up+",
    "Shield", "Shield+",
    "2 Card", "3 Card", "4 Card", "5 Card", "6 Card", "7 Card",
    "Return", "Remove", "Exchange",
    "Perfect Draw", "Perfect Draw+", "Ultimate Draw",
    "Love Your Enemy",
    "Go for 24", "Go for 27",
    "Destroy", "Destroy+", "Destroy++",
    "Trump Switch", "Trump Switch+", "Harvest",
]

# Cards that require challenge unlocks before they appear in your pool
UNLOCKABLE = {"Perfect Draw+", "Ultimate Draw", "Trump Switch+", "Shield+",
              "Two-Up+", "Go for 24", "Go for 27", "Harvest"}


def display_trump_hand(trump_hand: list) -> None:
    """Display player's current trump cards."""
    if not trump_hand:
        print("\n No trump cards in hand.")
        return
    print("\n ┌─ YOUR TRUMP CARDS ──────────────────────────────┐")
    for i, card in enumerate(trump_hand, 1):
        desc = TRUMPS.get(card, {}).get("desc", "")
        print(f" │ {i:>2}. {card:<20s} {desc[:35]:<35s}│")
    print(" └─────────────────────────────────────────────────┘")


def edit_trump_hand(trump_hand: list, available_trumps: set = None) -> list:
    """Let user add/remove trump cards from their hand.
    available_trumps: if provided, only show unlocked cards in the add list."""
    if available_trumps is not None:
        allowed = [c for c in PLAYER_TRUMPS
                   if c not in UNLOCKABLE or c in available_trumps]
    else:
        allowed = PLAYER_TRUMPS  # No filtering — show all

    while True:
        display_trump_hand(trump_hand)
        print("\n Options:")
        print("  +  Add trump card(s)")
        print("  -  Remove a trump card (by number)")
        print("  c  Clear all")
        print("  Enter  Done")
        choice = input(" > ").strip().lower()

        if not choice:
            return trump_hand
        elif choice == "c":
            trump_hand.clear()
            print(" Hand cleared.")
        elif choice == "-":
            if not trump_hand:
                print(" Hand is empty.")
                continue
            num = input(" Remove which # ? ").strip()
            try:
                idx = int(num) - 1
                if 0 <= idx < len(trump_hand):
                    removed = trump_hand.pop(idx)
                    print(f" Removed: {removed}")
                else:
                    print(" Invalid number.")
            except ValueError:
                print(" Invalid input.")
        elif choice == "+":
            print("\n Available trump cards:")
            for i, name in enumerate(allowed, 1):
                desc = TRUMPS.get(name, {}).get("desc", "")
                print(f"  {i:>2}. {name:<20s} {desc[:35]}")
            if available_trumps is not None:
                locked = [c for c in UNLOCKABLE if c not in available_trumps]
                if locked:
                    print(f"\n  🔒 Locked ({len(locked)}): {', '.join(sorted(locked))}")
            print(f"\n Enter numbers to add (e.g., '1 3 7'):")
            raw = input(" > ").strip()
            if raw:
                try:
                    for idx in [int(x) for x in raw.split()]:
                        if 1 <= idx <= len(allowed):
                            trump_hand.append(allowed[idx - 1])
                            print(f"  + {allowed[idx - 1]}")
                        else:
                            print(f"  ! No card #{idx}")
                except ValueError:
                    print("  ! Numbers only (e.g. '1 3 7')")
    return trump_hand


def recommend_trump_play(
    trump_hand: list,
    u_total: int,
    o_visible_total: int,
    remaining: list,
    target: int,
    stay_val: int,
    intel: dict,
    player_hp: int,
    opp_hp: int,
    opp_behavior: str = "auto",
    fight_num: int = 0,
    mode_key: str = "3",
    stay_win_pct: float = None,
) -> list:
    """
    Smart trump card auto-suggestion engine.
    Weight values drive sorting internally but are NEVER shown to user.

    stay_win_pct: if provided, used to suppress advice when winning comfortably.
    Returns list of recommendation strings, or empty list if no action needed.
    """
    if not trump_hand:
        return []

    def get_weight(card_name):
        return TRUMPS.get(card_name, {}).get("weight", 50)

    recs = []
    hand_set = set(trump_hand)
    enemy_trumps = set(intel.get("trumps", []))
    trump_behavior = intel.get("trump_behavior", {})
    gap_to_target = target - u_total if u_total < target else 0
    busted = u_total > target
    opp_name = intel.get("name", "")
    is_boss = "Boss" in opp_name or "Undead" in opp_name or "Molded" in opp_name
    destroys_held = sum(1 for c in trump_hand if c.startswith("Destroy"))
    SAVE_THRESHOLD = 60

    # ── SMART SUPPRESSION ──
    # Skip trump advice when you're winning comfortably against a weak opponent
    has_enemy_threats = bool(enemy_trumps & {
        "Dead Silence", "Black Magic", "Curse", "Escape",
        "Mind Shift", "Mind Shift+", "Desire", "Desire+",
        "Shield Assault", "Shield Assault+", "Twenty-One Up",
        "Oblivion", "Destroy+", "Destroy++"
    })
    needs_advice = (
        busted
        or has_enemy_threats
        or player_hp <= 3
        or is_boss
        or (stay_win_pct is not None and stay_win_pct < 0.55)
        or u_total == target
        or fight_num >= 5
    )
    if not needs_advice:
        return []

    # ── GAUNTLET RESOURCE MANAGEMENT ──
    if mode_key == "3" and fight_num > 0 and not is_boss:
        if fight_num < 5 and destroys_held > 0:
            recs.append("⚠ SAVE Destroy cards — Molded Hoffman (fight #5) needs them!")
        elif fight_num > 5 and fight_num < 10 and destroys_held > 0:
            recs.append("\033[91m★★ SAVE ALL Destroy cards for fight #10 — Dead Silence is lethal!\033[0m")
    elif mode_key == "2" and fight_num > 0 and fight_num < 5 and destroys_held > 0:
        recs.append("⚠ SAVE Destroy cards — Molded Hoffman (fight #5) needs them!")

    if not is_boss:
        expensive = sorted(set(c for c in trump_hand if get_weight(c) >= SAVE_THRESHOLD), key=get_weight, reverse=True)
        if expensive:
            recs.append(f"SAVE for bosses: {', '.join(expensive[:3])}")

    # ── PRIORITY 1: EMERGENCY — Busted ──
    if busted:
        fixes = []
        if "Return" in hand_set:
            fixes.append((get_weight("Return"), "★★ PLAY 'Return' — send back your last card!"))
        if "Go for 27" in hand_set and u_total <= 27:
            fixes.append((get_weight("Go for 27"), f"★★ PLAY 'Go for 27' — {u_total} is safe under 27!"))
        if "Go for 24" in hand_set and u_total <= 24 and target == 21:
            fixes.append((get_weight("Go for 24"), f"★★ PLAY 'Go for 24' — {u_total} is safe under 24!"))
        if "Exchange" in hand_set:
            fixes.append((get_weight("Exchange"), "★ 'Exchange' — swap your bust card with opponent's."))
        if fixes:
            fixes.sort(key=lambda x: x[0])
            recs.append("BUST RECOVERY (cheapest fix first):")
            for _, msg in fixes:
                recs.append(f"  {msg}")
        else:
            shield_cards = [c for c in trump_hand if c.startswith("Shield") and "Assault" not in c]
            if shield_cards:
                cheapest = min(shield_cards, key=get_weight)
                recs.append(f"No un-bust cards. Play '{cheapest}' to reduce damage.")
        return recs

    # ── PRIORITY 2: REACTIVE — Counter enemy threats ──
    if "Dead Silence" in enemy_trumps:
        ds_info = trump_behavior.get("Dead Silence", {})
        if ds_info.get("freq") in ("very_high", "high"):
            if destroys_held >= 2:
                recs.append(f"★ SAVE {destroys_held} Destroys for Dead Silence — he uses it repeatedly!")
            elif destroys_held == 1:
                recs.append("★ SAVE your Destroy for Dead Silence — top priority!")
            else:
                recs.append("⚠ No Destroy! If Dead Silence hits, use Exchange.")
        elif destroys_held > 0:
            recs.append("SAVE Destroy for Dead Silence if he plays it.")

    if "Black Magic" in enemy_trumps and destroys_held > 0:
        if "Dead Silence" not in enemy_trumps:
            recs.append("★ SAVE Destroy for Black Magic — bet +10 = instant death!")
        else:
            recs.append("  Also save a Destroy for Black Magic (bet +10).")

    if "Curse" in enemy_trumps and remaining:
        highest = max(remaining)
        if u_total + highest > target:
            counters = []
            if "Return" in hand_set:
                counters.append((get_weight("Return"), "'Return' to send back forced card"))
            if "Exchange" in hand_set:
                counters.append((get_weight("Exchange"), "'Exchange' to give bad card to opponent"))
            if counters:
                counters.sort(key=lambda x: x[0])
                recs.append(f"If Cursed (forced {highest}, bust to {u_total + highest}): use {counters[0][1]}")

    if "Escape" in enemy_trumps and destroys_held > 0:
        recs.append("★ SAVE Destroy for 'Escape' — otherwise wins are voided!")

    if "Mind Shift+" in enemy_trumps:
        by_weight = sorted(trump_hand, key=get_weight)[:3]
        recs.append(f"⚠ Mind Shift+: play 3 trumps or lose ALL. Burn: {', '.join(by_weight)}")
    elif "Mind Shift" in enemy_trumps:
        by_weight = sorted(trump_hand, key=get_weight)[:2]
        recs.append(f"⚠ Mind Shift: play 2 trumps or lose half. Burn: {', '.join(by_weight)}")

    if "Destroy+" in enemy_trumps:
        bet_ups = [c for c in trump_hand if c.startswith("One-Up") or c.startswith("Two-Up")]
        if len(bet_ups) > 1:
            recs.append("Don't stack all bet-ups — enemy has Destroy+ to wipe them.")

    if "Desire" in enemy_trumps or "Desire+" in enemy_trumps:
        d_type = "Desire+" if "Desire+" in enemy_trumps else "Desire"
        by_weight = sorted(trump_hand, key=get_weight)[:2]
        recs.append(f"⚠ {d_type}: dump cheap trumps to lower your bet. Burn: {', '.join(by_weight)}")

    # ── PRIORITY 3: PROACTIVE — Offensive ──
    if u_total == target:
        bet_cards = sorted([c for c in trump_hand if c in ("One-Up", "Two-Up", "Two-Up+")], key=get_weight)
        if bet_cards:
            recs.append(f"★ PERFECT {target}! Stack bet-ups: {', '.join(bet_cards)}")

    if "Love Your Enemy" in hand_set and opp_behavior != "stay":
        if o_visible_total >= target - 3:
            bust_cards = [c for c in remaining if o_visible_total + c > target]
            if bust_cards:
                recs.append(f"'Love Your Enemy' — {len(bust_cards)}/{len(remaining)} remaining cards bust opponent!")

    if gap_to_target > 0:
        draw_options = sorted(
            [(get_weight(c), c) for c in ["Perfect Draw", "Perfect Draw+", "Ultimate Draw"] if c in hand_set],
            key=lambda x: x[0]
        )
        if draw_options:
            recs.append(f"'{draw_options[0][1]}' — draws best card (need {gap_to_target} to reach {target}).")
            if len(draw_options) > 1 and not is_boss:
                recs.append(f"  (Save '{draw_options[-1][1]}' for bosses — use cheapest draw first.)")

    num_draws = []
    for card_name in ["2 Card", "3 Card", "4 Card", "5 Card", "6 Card", "7 Card"]:
        if card_name in hand_set:
            needed = int(card_name[0])
            if u_total + needed == target and needed in remaining:
                num_draws.append((get_weight(card_name), f"★ '{card_name}' gives you exactly {target}!"))
            elif u_total + needed <= target and needed in remaining:
                num_draws.append((get_weight(card_name), f"'{card_name}' is safe ({u_total}+{needed}={u_total+needed})."))
    for _, msg in sorted(num_draws, key=lambda x: x[0]):
        recs.append(msg)

    if "Two-Up+" in hand_set and opp_behavior != "stay":
        recs.append("'Two-Up+' returns opponent's card to deck AND bet +2.")

    if "Exchange" in hand_set and opp_behavior != "stay" and gap_to_target > 0:
        recs.append("'Exchange' can steal opponent's high card.")

    # ── PRIORITY 4: DEFENSIVE ──
    if player_hp <= 3:
        shield_cards = [c for c in trump_hand if c.startswith("Shield") and "Assault" not in c]
        if shield_cards:
            cheapest = min(shield_cards, key=get_weight)
            recs.append(f"LOW HP ({player_hp}) — play '{cheapest}' to reduce damage.")

    if "Harvest" in hand_set:
        recs.append("★ Play 'Harvest' first! Every trump afterward draws a replacement.")

    if "Trump Switch+" in hand_set and len(trump_hand) <= 3:
        recs.append("'Trump Switch+' — discard 1, draw 4.")
    elif "Trump Switch" in hand_set and len(trump_hand) <= 2:
        recs.append("'Trump Switch' — discard 2, draw 3.")

    if not recs:
        return []

    return recs


def apply_trump_effect(
    trump_name: str,
    u_hand: list,
    o_vis: list,
    remaining: list,
    dead_cards: list,
    target: int,
) -> dict:
    """
    Apply a trump card's mechanical effect to the game state.
    Returns dict with updated state and a description of what happened.
    """
    result = {
        "u_hand": list(u_hand),
        "o_vis": list(o_vis),
        "remaining": list(remaining),
        "dead_cards": list(dead_cards),
        "target": target,
        "msg": "",
    }

    if trump_name == "Return":
        if not result["u_hand"] or len(result["u_hand"]) < 2:
            result["msg"] = "Can't Return — need at least 2 cards in hand."
            return result
        returned = result["u_hand"].pop()
        result["remaining"].append(returned)
        result["remaining"].sort()
        result["msg"] = f"Returned card {returned} to the deck. Your hand: {result['u_hand']}, total: {sum(result['u_hand'])}"

    elif trump_name == "Remove":
        if not result["o_vis"]:
            result["msg"] = "Can't Remove — no visible opponent cards."
            return result
        removed = result["o_vis"].pop()
        result["dead_cards"].append(removed)
        result["dead_cards"] = sorted(set(result["dead_cards"]))
        result["msg"] = f"Removed opponent's card {removed}. Opponent visible: {result['o_vis']}, total: {sum(result['o_vis'])}"

    elif trump_name == "Exchange":
        if not result["u_hand"] or not result["o_vis"]:
            result["msg"] = "Can't Exchange — both sides need at least one card."
            return result
        your_card = result["u_hand"].pop()
        opp_card = result["o_vis"].pop()
        result["u_hand"].append(opp_card)
        result["o_vis"].append(your_card)
        result["msg"] = (
            f"Exchanged: gave your {your_card}, took their {opp_card}. "
            f"Your hand: {result['u_hand']} (total {sum(result['u_hand'])}), "
            f"Opponent: {result['o_vis']} (total {sum(result['o_vis'])})"
        )

    elif trump_name == "Perfect Draw":
        needed = target - sum(result["u_hand"])
        if needed in result["remaining"]:
            result["u_hand"].append(needed)
            result["remaining"].remove(needed)
            result["msg"] = f"Perfect Draw! Drew {needed} → total {sum(result['u_hand'])} = {target}!"
        else:
            # Draws the closest card to what's needed
            if result["remaining"]:
                best = min(result["remaining"], key=lambda c: abs(c - needed))
                result["u_hand"].append(best)
                result["remaining"].remove(best)
                result["msg"] = f"Perfect Draw: needed {needed} but drew {best}. Total: {sum(result['u_hand'])}"
            else:
                result["msg"] = "No cards left to draw!"

    elif trump_name in ("Go for 17", "Go for 24", "Go for 27"):
        new_target = int(trump_name.split()[-1])
        result["target"] = new_target
        result["msg"] = f"Target changed to {new_target}!"

    elif trump_name == "Love Your Enemy":
        if result["remaining"]:
            # Opponent draws a random card — we'll ask what they drew
            result["msg"] = "FORCE_DRAW"  # Signal to caller to ask for drawn card
        else:
            result["msg"] = "No cards left for opponent to draw!"

    elif trump_name == "Destroy":
        result["msg"] = "Destroyed opponent's last trump card. (No card state change needed.)"

    elif trump_name in ("Destroy+", "Destroy++"):
        result["msg"] = "Destroyed ALL opponent trump cards on the table."

    else:
        result["msg"] = f"'{trump_name}' played. (Effect is trump-only, no card state change.)"

    return result

# ============================================================
# DISPLAY HELPERS
# ============================================================
def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def print_header(title: str, width: int = 60) -> None:
    print("\n" + "=" * width)
    print(f" {title}".center(width))
    print("=" * width)


def hp_bar(current: int, maximum: int, width: int = 20) -> str:
    """Render an ASCII HP bar."""
    if maximum <= 0:
        return "[?] 0/0 (0%)"
    filled = int((current / maximum) * width)
    empty = width - filled
    pct = (current / maximum) * 100
    return f"[{'█' * filled}{'░' * empty}] {current}/{maximum} ({pct:.0f}%)"


def display_hp_status(player_hp: int, player_max: int, opp_hp: int, opp_max: int, opp_name: str) -> None:
    """Show both HP bars."""
    name_short = opp_name[:25]  # Allow longer names
    print()
    print(" ┌───────────────────────────────────────────────────────────┐")
    print(f" │ {'HP STATUS':^59s} │")
    print(" ├───────────────────────────────────────────────────────────┤")
    player_bar = hp_bar(player_hp, player_max, 15)
    opp_bar = hp_bar(opp_hp, opp_max, 15)
    print(f" │ YOU: {player_bar:<54s}│")
    print(f" │ {name_short:<25s} {opp_bar:<33s}│")
    print(" └───────────────────────────────────────────────────────────┘")


def display_card_matrix(accounted_for) -> None:
    """Show which cards (1–11) are in/out of the deck."""
    accounted_set = set(accounted_for)
    print("\n ┌" + "─" * 46 + "┐")
    print(" │" + " DECK TRACKER ".center(46) + "│")
    print(" ├" + "─" * 46 + "┤")

    def fmt(i: int) -> str:
        if i in accounted_set:
            return f"\033[91m{i:>2}:OUT\033[0m"
        return f"\033[92m{i:>2}:IN \033[0m"

    line1 = " │ " + " ".join(fmt(i) for i in range(1, 7)) + " │"
    line2 = " │ " + " ".join(fmt(i) for i in range(7, 12)) + " │"
    print(line1)
    print(line2)
    print(" └" + "─" * 46 + "┘")

    remaining = [c for c in range(1, 12) if c not in accounted_set]
    print(f" Cards remaining: {len(remaining)} | Sum available: {sum(remaining)}")


def display_trumps_reference() -> None:
    """Print full trump card reference."""
    print_header("TRUMP CARD REFERENCE")
    current_cat = None
    for name, info in TRUMPS.items():
        cat = info.get("cat", "Other")
        if cat != current_cat:
            current_cat = cat
            print(f"\n --- {current_cat.upper()} ---")
        print(f" {name:<20s} {info.get('desc','')}")
    print()


def display_opponent_info(intel: dict) -> None:
    """Print detailed opponent info with standard and special trump sections."""
    print(f"\n ┌─ TARGET: {intel['name']}")
    print(f" │ Mode: {intel.get('mode','?')}")
    print(f" │ AI Type: {intel.get('ai','?')}")

    # Standard trumps (common cards any opponent might use)
    std_trumps = intel.get("standard_trumps", [])
    special_trumps = intel.get("trumps", [])

    if std_trumps:
        print(f" │ Standard Trumps: {', '.join(std_trumps)}")
    if special_trumps:
        print(f" │ \033[96mSpecial Trumps: {', '.join(special_trumps)}\033[0m")
    elif not std_trumps:
        print(f" │ Trumps: (none observed)")

    # Show real AI parameters from CardGameBanker.hpp
    ai = get_banker_ai(intel)
    print(f" │ AI DRAW MODEL  (CardGameBanker.hpp):")
    print(f" │   Draws below {ai.take_card_border} | Stays at {ai.hand_good_border}+"
          + (" | CHICKEN MODE" if ai.is_chicken else ""))
    print(f" │   Reads YOUR hand as dangerous: {ai.player_good_low}–{ai.player_good_high}"
          f"  |  weak: {ai.player_bad_low}–{ai.player_bad_high}")
    print(f" │ TRUMP RANDOMNESS: Pool FIXED per opponent, deal ORDER randomized")
    print(f" │ CARDS (1–11): Reshuffled each round via RNG — not predetermined")
    print(f" └─ {intel.get('desc','')}")
    tip = intel.get("tip", "")
    if tip:
        print(f"\n INTEL:\n {tip}")


def display_round_history(history) -> None:
    """Print round history for current opponent."""
    if not history:
        print("\n No rounds played yet against this opponent.")
        return
    print("\n ┌─ ROUND HISTORY ──────────────────────────────────┐")
    for entry in history:
        rnd    = entry["round"]
        result = entry["result"]
        dmg    = entry["damage"]
        who    = entry.get("damage_to", "opponent" if result == "WIN" else "you")
        if result == "VOID":
            line = f" │ R{rnd}: VOID (Escape/Oblivion) — no damage"
        elif result == "TIE":
            line = f" │ R{rnd}: TIE — no damage"
        else:
            winner     = "YOU WON" if result == "WIN" else "YOU LOST"
            target_lbl = "opponent" if who == "opponent" else "you"
            line = f" │ R{rnd}: {winner} → {dmg} dmg to {target_lbl}"
        print(f"{line:<55s}│")
    print(" └─────────────────────────────────────────────────┘")


def parse_card_values(raw: str):
    """Parse space-separated card values (1-11)."""
    if not raw.strip():
        return []
    cards = list(map(int, raw.split()))
    for c in cards:
        if c < 1 or c > 11:
            raise ValueError(f"Card {c} is out of range (1-11).")
    return cards


# ============================================================
# SOLVER / PROBABILITY LOGIC
# ============================================================
def calculate_probabilities(remaining, current_total: int, target: int):
    """Return (safe_pct, bust_pct, perfect_draws)."""
    if not remaining:
        return 0.0, 0.0, []
    safe_draws = [c for c in remaining if current_total + c <= target]
    bust_draws = [c for c in remaining if current_total + c > target]
    perfect_draws = [c for c in remaining if current_total + c == target]
    total_cards = len(remaining)
    safe_pct = (len(safe_draws) / total_cards) * 100
    bust_pct = (len(bust_draws) / total_cards) * 100
    return safe_pct, bust_pct, perfect_draws


def resolve_round_outcome(your_total: int, opp_total: int, target: int) -> str:
    """Resolve winner from final totals using RE7 21 bust rules."""
    you_bust = your_total > target
    opp_bust = opp_total > target

    if not you_bust and not opp_bust:
        if your_total > opp_total:
            return "WIN"
        if your_total < opp_total:
            return "LOSS"
        return "TIE"

    if you_bust and not opp_bust:
        return "LOSS"
    if not you_bust and opp_bust:
        return "WIN"

    # both bust -> smaller bust margin wins
    your_over = your_total - target
    opp_over = opp_total - target
    if your_over < opp_over:
        return "WIN"
    if your_over > opp_over:
        return "LOSS"
    return "TIE"


def opponent_total_distribution(
    o_visible_total: int,
    remaining,
    stay_val: int,
    target: int,
    behavior: str = "auto",
    banker_ai: "BankerAI" = None,
    player_visible_total: int = 0,
):
    """
    Return probability distribution of opponent final totals.

    When banker_ai is provided (BankerAI instance), uses the REAL draw decision
    from CardGameBanker.hpp — the gray-zone player-hand-aware logic replaces the
    old flat overshoot estimate.

    behavior options:
      - stay:              opponent confirmed stopped drawing
      - hit_once:          opponent draws one card then stops
      - auto / hit_to_threshold: opponent draws using AI thresholds
    """
    behavior = behavior.lower().strip()
    deck = tuple(sorted(set(remaining)))

    if behavior == "stay":
        # Opponent stopped — hidden card is from remaining deck
        if not deck:
            return {o_visible_total: 1.0}
        p = 1.0 / len(deck)
        return {o_visible_total + c: p for c in deck}

    if o_visible_total > target:
        return {o_visible_total: 1.0}

    if behavior == "hit_once":
        if not deck:
            return {o_visible_total: 1.0}
        p = 1.0 / len(deck)
        return {o_visible_total + c: p for c in deck}

    memo = {}

    def _merge(dest: dict, src: dict, weight: float) -> None:
        for total, prob in src.items():
            dest[total] = dest.get(total, 0.0) + (prob * weight)

    def _draw_prob(total: int) -> float:
        """Returns probability the banker draws at this total."""
        if banker_ai is not None:
            # Real AI: uses BankerHandGoodBorder + player hand awareness
            return banker_ai.draw_probability(total, player_visible_total, target)
        else:
            # Legacy fallback: deterministic below stay_val, partial overshoot above
            if total < stay_val:
                return 1.0
            if total >= target:
                return 0.0
            # Old model: blend in some overshoot uncertainty
            gap_to_target = max(0, target - o_visible_total)
            overshoot_chance = min(0.50, 0.15 + (gap_to_target / target) * 0.35)
            return overshoot_chance

    def _dfs(total: int, deck_state: tuple):
        key = (total, deck_state)
        if key in memo:
            return memo[key]

        if total > target:
            memo[key] = {total: 1.0}
            return memo[key]

        if not deck_state:
            memo[key] = {total: 1.0}
            return memo[key]

        draw_p = _draw_prob(total)
        dist = {}

        if draw_p >= 0.999:
            # Definitely draws
            n = len(deck_state)
            for idx, card in enumerate(deck_state):
                next_total = total + card
                next_deck = deck_state[:idx] + deck_state[idx + 1:]
                sub = _dfs(next_total, next_deck)
                _merge(dist, sub, 1.0 / n)
        elif draw_p <= 0.001:
            # Definitely stays
            dist = {total: 1.0}
        else:
            # Mixed: weighted blend of staying vs drawing
            _merge(dist, {total: 1.0}, 1.0 - draw_p)
            n = len(deck_state)
            for idx, card in enumerate(deck_state):
                next_total = total + card
                next_deck = deck_state[:idx] + deck_state[idx + 1:]
                sub = _dfs(next_total, next_deck)
                _merge(dist, sub, draw_p / n)

        memo[key] = dist
        return dist

    return _dfs(o_visible_total, deck)


def outcome_probabilities(your_total: int, opp_dist: dict, target: int):
    """Map opponent total distribution to WIN/TIE/LOSS probabilities."""
    probs = {"win": 0.0, "tie": 0.0, "loss": 0.0}
    for opp_total, p in opp_dist.items():
        result = resolve_round_outcome(your_total, opp_total, target)
        if result == "WIN":
            probs["win"] += p
        elif result == "TIE":
            probs["tie"] += p
        else:
            probs["loss"] += p
    return probs


def evaluate_stay_hit_outcomes(
    u_total: int,
    o_visible_total: int,
    remaining,
    stay_val: int,
    target: int,
    opp_behavior: str,
    banker_ai: "BankerAI" = None,
):
    """Compute expected outcome probs for staying now vs. hitting now.
    When banker_ai is provided the opponent distribution uses the real AI model."""
    stay_opp_dist = opponent_total_distribution(
        o_visible_total, remaining, stay_val, target,
        behavior=opp_behavior, banker_ai=banker_ai, player_visible_total=u_total,
    )
    stay_probs = outcome_probabilities(u_total, stay_opp_dist, target)

    if not remaining:
        return stay_probs, {"win": 0.0, "tie": 0.0, "loss": 1.0}

    hit_probs = {"win": 0.0, "tie": 0.0, "loss": 0.0}
    draw_weight = 1.0 / len(remaining)

    for card in remaining:
        your_new_total = u_total + card
        next_remaining = [c for c in remaining if c != card]
        opp_dist_after_hit = opponent_total_distribution(
            o_visible_total, next_remaining, stay_val, target,
            behavior=opp_behavior, banker_ai=banker_ai, player_visible_total=your_new_total,
        )
        draw_outcome = outcome_probabilities(your_new_total, opp_dist_after_hit, target)
        hit_probs["win"] += draw_outcome["win"] * draw_weight
        hit_probs["tie"] += draw_outcome["tie"] * draw_weight
        hit_probs["loss"] += draw_outcome["loss"] * draw_weight

    return stay_probs, hit_probs


def estimate_opponent_total(o_visible_total: int, stay_val: int) -> int:
    """Simple heuristic: opponents tend to aim for stay_val+."""
    if o_visible_total >= stay_val:
        return o_visible_total
    return stay_val


def evaluate_bust_inline(u_total, o_visible_total, remaining, stay_val, target, behavior="auto", banker_ai=None):
    """Lightweight bust-to-win evaluation — returns best bust draw card and win probability."""
    bust_cards = [c for c in remaining if u_total + c > target]
    if not bust_cards:
        return None
    best_card = None
    best_win  = 0.0
    for draw_card in bust_cards:
        bust_total = u_total + draw_card
        deck_after = [c for c in remaining if c != draw_card]
        opp_dist = opponent_total_distribution(
            o_visible_total, deck_after, stay_val, target,
            behavior=behavior, banker_ai=banker_ai, player_visible_total=bust_total,
        )
        wins = sum(prob for opp_total, prob in opp_dist.items()
                   if bust_outcome(bust_total, opp_total, target) == "WIN")
        if wins > best_win:
            best_win  = wins
            best_card = draw_card
    return {"best_card": best_card, "bust_total": u_total + best_card if best_card else 0, "win_pct": best_win}


def evaluate_bust_win_challenge(
    u_total: int,
    o_visible_total: int,
    remaining: list,
    stay_val: int,
    target: int,
    trump_hand: list,
    intel: dict,
    player_hp: int,
    player_max: int,
    opp_hp: int,
    challenges_completed: set = None,
    banker_ai: "BankerAI" = None,
    behavior: str = "auto",
) -> list:
    """
    Comprehensive bust-win challenge guidance engine.

    Bust-win rule: when BOTH players exceed target, closer to target wins.
    e.g. target=21: you=23 vs opp=25 -> you win (2 over vs 4 over).

    Analyzes all paths: direct draw, trump setups, already-busted scenarios.
    """
    if challenges_completed is None:
        challenges_completed = set()
    if trump_hand is None:
        trump_hand = []

    bust_challenge_done = "bust_win" in challenges_completed
    lines = []
    hand_set = set(trump_hand)
    enemy_trumps = set(intel.get("trumps", []))
    opp_name = intel.get("name", "")
    already_busted = u_total > target

    # ── 1. Opponent natural bust probability ─────────────────────────────────
    opp_bust_rate = 0.0
    if remaining:
        opp_dist_base = opponent_total_distribution(
            o_visible_total, remaining, stay_val, target,
            behavior=behavior, banker_ai=banker_ai, player_visible_total=u_total,
        )
        opp_bust_rate = sum(p for t, p in opp_dist_base.items() if t > target)

    # ── 2. Direct draw paths ─────────────────────────────────────────────────
    draw_paths = []
    if not already_busted and remaining:
        for card in sorted(set(c for c in remaining if u_total + c > target)):
            bust_total = u_total + card
            deck_after = [c for c in remaining if c != card]
            opp_dist = opponent_total_distribution(
                o_visible_total, deck_after, stay_val, target,
                behavior=behavior, banker_ai=banker_ai, player_visible_total=bust_total,
            )
            win_pct = sum(p for t, p in opp_dist.items()
                          if bust_outcome(bust_total, t, target) == "WIN")
            draw_paths.append({
                "card": card, "bust_total": bust_total,
                "over_by": bust_total - target, "win_pct": win_pct,
            })
        draw_paths.sort(key=lambda x: (-x["win_pct"], x["over_by"]))

    # Win% if already busted (current total, opponent draws naturally)
    current_bust_win_pct = 0.0
    if already_busted and remaining:
        opp_dist = opponent_total_distribution(
            o_visible_total, remaining, stay_val, target,
            behavior=behavior, banker_ai=banker_ai, player_visible_total=u_total,
        )
        current_bust_win_pct = sum(p for t, p in opp_dist.items()
                                   if bust_outcome(u_total, t, target) == "WIN")

    # ── 3. Trump-assisted paths ───────────────────────────────────────────────

    # Love Your Enemy: force opponent to draw — may push them deeper bust
    lye_analysis = None
    if "Love Your Enemy" in hand_set and remaining:
        best_lye_pct  = 0.0
        best_lye_card = None
        total_lye_win = 0.0
        for forced_card in remaining:
            new_opp = o_visible_total + forced_card
            after   = [c for c in remaining if c != forced_card]
            opp_dist_after = opponent_total_distribution(
                new_opp, after, stay_val, target,
                behavior="auto", banker_ai=banker_ai, player_visible_total=u_total,
            )
            win_this = sum(
                p for t, p in opp_dist_after.items()
                if bust_outcome(u_total, t, target) == "WIN"
            ) / len(remaining)
            total_lye_win += win_this
            if win_this * len(remaining) > best_lye_pct:
                best_lye_pct  = win_this * len(remaining)
                best_lye_card = forced_card
        lye_analysis = {"win_pct": total_lye_win, "best_card": best_lye_card, "best_card_pct": best_lye_pct}

    # Go For target shifts: may un-bust you after drawing
    go_saves = []
    if not already_busted:
        if "Go for 24" in hand_set and target == 21:
            saved = [c for c in remaining if u_total + c in (22, 23, 24)]
            if saved:
                go_saves.append(("Go for 24", 24, saved))
        if "Go for 27" in hand_set and target <= 24:
            saved = [c for c in remaining if target < u_total + c <= 27]
            if saved:
                go_saves.append(("Go for 27", 27, saved))

    # ── 4. Opponent profile ───────────────────────────────────────────────────
    opp_draw_trumps  = enemy_trumps & {"Conjure", "Happiness", "Ultimate Draw", "Perfect Draw+"}
    has_go17         = "Go for 17" in enemy_trumps
    opp_can_escape   = bool(enemy_trumps & {"Escape", "Oblivion"})

    if stay_val <= 15:
        opp_bust_rating = "HIGH (stay_val {}) — draws a lot, busts often".format(stay_val)
    elif stay_val <= 17:
        opp_bust_rating = "MEDIUM (stay_val {}) — moderate draw threshold".format(stay_val)
    else:
        opp_bust_rating = "LOW (stay_val {}) — stops early, rarely busts naturally".format(stay_val)
    if opp_draw_trumps:
        opp_bust_rating += " +draws from ({})".format(", ".join(sorted(opp_draw_trumps)))

    # ── 5. Format output ─────────────────────────────────────────────────────
    header = "BUST-WIN CHALLENGE" if not bust_challenge_done else "BUST WIN (already completed)"
    lines.append("=" * 58)
    lines.append(f" {header}")
    lines.append(f" Rule: BOTH bust -> closer to {target} wins.")
    lines.append(f" Opponent natural bust chance: {opp_bust_rate * 100:.0f}%  |  {opp_bust_rating}")
    lines.append("=" * 58)

    if opp_can_escape:
        which = "Escape" if "Escape" in enemy_trumps else "Oblivion"
        lines.append(f" !! {which}: opponent may void the round — Destroy it before busting!")

    if has_go17:
        lines.append(f" !! Go for 17 in play — if active, you'll bust at 18+ on target 17.")

    if already_busted:
        over = u_total - target
        lines.append(f"")
        lines.append(f" You are BUST at {u_total} ({over} over {target}).")
        lines.append(f" Win chance AS-IS: {current_bust_win_pct * 100:.1f}%")

        if current_bust_win_pct >= 0.30:
            lines.append(f" -> Decent odds. STAY and let opponent draw into a deeper bust.")
        elif current_bust_win_pct >= 0.10:
            lines.append(f" -> Marginal. Use trumps to worsen opponent position before resolving.")
        else:
            lines.append(f" -> Poor odds. You need trumps to improve the situation.")

        # Trump improvements from busted state
        trump_helps = []
        if lye_analysis and lye_analysis["win_pct"] > current_bust_win_pct + 0.04:
            trump_helps.append(
                f"  'Love Your Enemy' -> {lye_analysis['win_pct'] * 100:.1f}% win chance "
                f"(forces card [{lye_analysis['best_card']}] on opponent)."
            )
        if "Exchange" in hand_set and o_visible_total > 0:
            trump_helps.append(
                f"  'Exchange' -> swap your last drawn card with opponent's face-up card "
                f"(opp visible: {o_visible_total}) — may un-bust or deepen their total."
            )
        if "Return" in hand_set:
            trump_helps.append(f"  'Return' -> send back your last face-up card — may un-bust you.")
        if "Go for 27" in hand_set and u_total <= 27 and target < 27:
            trump_helps.append(f"  'Go for 27' -> your {u_total} is safe at target 27! Un-busts you entirely.")
        if "Go for 24" in hand_set and u_total <= 24 and target == 21:
            trump_helps.append(f"  'Go for 24' -> your {u_total} is safe at target 24! Un-busts you entirely.")
        if trump_helps:
            lines.append(f"")
            lines.append(f" Trump options:")
            lines.extend(trump_helps)

    else:
        lines.append(f"")
        lines.append(f" You are at {u_total}. Goal: draw over {target}, stay closer to it than opponent.")

        if draw_paths:
            best = draw_paths[0]
            lines.append(f"")
            lines.append(f" BEST BUST DRAW:  card [{best['card']}]  ->  total {best['bust_total']}  ({best['over_by']} over)  |  Win {best['win_pct'] * 100:.1f}%")

            if len(draw_paths) > 1:
                lines.append(f"")
                lines.append(f" ALL BUST OPTIONS:")
                for path in draw_paths[:6]:
                    sym = "+" if path["win_pct"] >= 0.30 else ("~" if path["win_pct"] >= 0.15 else "-")
                    lines.append(
                        f"  [{sym}] Draw [{path['card']:>2}] -> {path['bust_total']:>2} "
                        f"({path['over_by']} over) | Win {path['win_pct'] * 100:.0f}%"
                    )
        else:
            lines.append(f" No single draw busts you from {u_total} — need 2 draws or a trump setup first.")

        # Trump setups
        trump_lines = []
        if go_saves:
            for trump_name, new_target, saved_cards in go_saves:
                trump_lines.append(
                    f"  '{trump_name}' first -> draw {sorted(saved_cards)} "
                    f"(bust at {target}, safe at {new_target}). Then bust vs opp at {new_target}."
                )
        if lye_analysis and lye_analysis["win_pct"] >= 0.12:
            trump_lines.append(
                f"  'Love Your Enemy' (after busting) -> {lye_analysis['win_pct'] * 100:.0f}% win. "
                f"Best forced card: [{lye_analysis['best_card']}]."
            )
        if "Remove" in hand_set and o_visible_total > 0:
            trump_lines.append(
                f"  'Remove' -> strip opponent's face-up card, forcing them to draw more -> higher bust risk."
            )
        if "Exchange" in hand_set:
            trump_lines.append(
                f"  'Exchange' after busting -> give your bust card to opponent, "
                f"deepening THEIR total if their card is lower."
            )
        if trump_lines:
            lines.append(f"")
            lines.append(f" Trump setups:")
            lines.extend(trump_lines)

    # ── Final verdict ─────────────────────────────────────────────────────────
    best_pct = 0.0
    if draw_paths:
        best_pct = draw_paths[0]["win_pct"]
    if already_busted:
        best_pct = max(current_bust_win_pct, lye_analysis["win_pct"] if lye_analysis else 0)

    if best_pct >= 0.40:
        verdict = "GOOD opportunity — go for it."
    elif best_pct >= 0.25:
        verdict = "FAIR — worth it, especially with trump support."
    elif best_pct >= 0.10:
        verdict = "RISKY — only attempt on draw-heavy opponents."
    else:
        verdict = "POOR — wait for a better setup or opponent."

    lines.append(f"")
    if not bust_challenge_done:
        lines.append(f" VERDICT: {verdict}")
        lines.append(f" Reward: Starting Trump Card +1")
    else:
        lines.append(f" (Challenge already completed.)")
    lines.append("")

    return lines


def generate_advice(
    u_total: int,
    o_visible_total: int,
    intel: dict,
    remaining,
    target: int,
    safe_pct: float,
    perfect_draws,
    player_hp: int,
    player_max: int,
    opp_hp: int,
    opp_max: int,
    opp_behavior: str = "auto",
    challenges_completed: set = None,
    available_trumps: set = None,
    trump_hand: list = None,
    banker_ai: "BankerAI" = None,
    condition_state: "TrumpConditionState" = None,
):
    """Generate strategic advice factoring in HP state + opponent trumps.
    banker_ai: real AI profile from CardGameBanker fields (improves outcome model).
    condition_state: current CardGameCondition-derived state for trump timing."""
    advice_lines = []
    priority_warnings = []
    if trump_hand is None:
        trump_hand = []
    hand_set = set(trump_hand)

    stay_val = int(intel.get("stay_val", 17))
    # Adjust opponent AI threshold when target differs from 21
    if target != 21:
        stay_val += (target - 21)
        stay_val = max(1, stay_val)  # Don't go below 1

    # ── REAL AI PROFILE DISPLAY ──
    if banker_ai is not None:
        draw_p = banker_ai.draw_probability(o_visible_total, u_total, target)
        # Only show if in the interesting gray zone (not trivially 0% or 100%)
        if 0.05 < draw_p < 0.95:
            advice_lines.append(
                f"AI MODEL: Banker draw probability at {o_visible_total} vs your {u_total} = {draw_p * 100:.0f}% "
                f"(real CardGameBanker logic: draw<{banker_ai.take_card_border}, stay≥{banker_ai.hand_good_border}"
                + (" | CHICKEN MODE" if banker_ai.is_chicken else "") + ")"
            )
        elif draw_p <= 0.05 and o_visible_total >= banker_ai.take_card_border:
            advice_lines.append(
                f"AI MODEL: Banker will likely STAY at {o_visible_total} "
                f"(satisfied threshold: {banker_ai.hand_good_border}"
                + (", CHICKEN MODE" if banker_ai.is_chicken else "") + ")"
            )

    # ── TRUMP CONDITION STATE WARNINGS ──
    if condition_state is not None:
        enemy_trumps_set = set(intel.get("trumps", []))
        high_priority_trumps = {
            "Dead Silence", "Black Magic", "Curse", "Escape",
            "Mind Shift+", "Desire+", "Go for 17",
        }
        for trump_name in (enemy_trumps_set & high_priority_trumps):
            level, reason = condition_state.trump_fire_likelihood(trump_name)
            if level in ("VERY HIGH", "HIGH"):
                priority_warnings.append(f"⚡ {trump_name} [{level}]: {reason}")
            elif level == "MEDIUM":
                advice_lines.append(f"  {trump_name} [{level}]: {reason}")
            elif level == "NONE":
                advice_lines.append(f"  {trump_name}: {reason}")  # e.g. exhausted Black Magic
    if player_hp <= 3:
        priority_warnings.append(
            f"!! LOW HP ({player_hp}/{player_max}) !! Play ultra-conservatively.\n"
            "Prioritize shields and avoid risky draws."
        )
    if opp_hp <= 2:
        advice_lines.append(f"★ OPPONENT LOW ({opp_hp}/{opp_max}) — consider stacking bet-ups to finish them.")

    # ── Opponent-specific warnings ──
    trumps = set(intel.get("trumps", []))

    if "Curse" in trumps and remaining:
        highest_card = max(remaining)
        forced_total = u_total + highest_card
        if forced_total > target:
            priority_warnings.append(
                f"!! CURSE DANGER !! Curse forces you to draw the {highest_card}.\n"
                f"Total would be {forced_total} → BUST!\n"
                "COUNTER: Hold 'Destroy' for Curse, or 'Return'/'Exchange' after."
            )
        else:
            advice_lines.append(
                f"Curse check: Highest remaining = {highest_card}. Forced total = {forced_total} — survivable."
            )

    if "Twenty-One Up" in trumps and remaining:
        cards_giving_21 = [c for c in remaining if o_visible_total + c == 21]
        if cards_giving_21:
            priority_warnings.append(
                "!! INSTANT KILL RISK !! He can hit EXACTLY 21 by drawing: "
                f"{sorted(cards_giving_21)}.\n"
                "'Twenty-One Up' sets bet to 21 — keep 'Destroy' ready."
            )

    if "Dead Silence" in trumps:
        if u_total < 17:
            priority_warnings.append(
                f"!! DEAD SILENCE RISK !! If locked at {u_total}, you likely lose.\n"
                "COUNTER: Priority-destroy Dead Silence. Consider drawing before he can play it."
            )

    if "Escape" in trumps:
        advice_lines.append("ESCAPE: He may void the round if losing. Destroy it or stack bets to one-shot.")

    if "Mind Shift" in trumps or "Mind Shift+" in trumps:
        ms_type = "Mind Shift+" if "Mind Shift+" in trumps else "Mind Shift"
        ms_effect = "ALL your trumps" if "Mind Shift+" in trumps else "half your trumps"
        advice_lines.append(f"{ms_type}: Can take {ms_effect}. Play 2+ trumps per turn to block, or Destroy it.")

    if "Desire" in trumps or "Desire+" in trumps:
        d_type = "Desire+" if "Desire+" in trumps else "Desire"
        d_effect = "full trump count" if "Desire+" in trumps else "half trump count"
        advice_lines.append(f"{d_type}: Your bet scales with your {d_effect}. Don't hoard trumps.")

    if "Shield Assault" in trumps or "Shield Assault+" in trumps:
        advice_lines.append("SHIELD ASSAULT: Negates your damage AND hurts you. Stack bet-ups to overwhelm.")

    if "Go for 17" in trumps:
        advice_lines.append("GO FOR 17: Can change target to 17 — your 20 becomes a bust! Watch for it.")

    if "Ultimate Draw" in trumps or "Perfect Draw+" in trumps:
        advice_lines.append("ULTIMATE/PERFECT DRAW+: He almost always gets the best possible card. Expect near-perfect hands.")

    if "Destroy+" in trumps or "Destroy++" in trumps:
        advice_lines.append("DESTROY+/++: Can wipe ALL your trumps at once. Don't over-commit trump cards.")

    if "Oblivion" in trumps:
        advice_lines.append("OBLIVION: Can void a round. Annoying, not fatal — replay and keep pressure.")

    # ── Enemy trump prediction (rule table + timing engine) ──
    if condition_state is not None:
        pick, conf, why = predict_enemy_trump(intel, condition_state)
        if pick and conf in ("HIGH", "VERY HIGH", "MEDIUM"):
            advice_lines.append(f"ENEMY AI [{conf}]: likely plays '{pick}' — {why}")

    # ── Core draw/stay decision ──
    behavior_key = (opp_behavior or "auto").strip().lower()

    # Use real AI thresholds in labels if available
    if banker_ai is not None:
        ai_label = (
            f"draws below {banker_ai.take_card_border}, stays at {banker_ai.hand_good_border}+"
            + (" [CHICKEN]" if banker_ai.is_chicken else "")
        )
        expected_opp_stay = banker_ai.hand_good_border
    else:
        ai_label = f"draws until {stay_val}+"
        expected_opp_stay = stay_val

    behavior_label = {
        "stay": "Opponent confirmed stopped drawing (hidden card modeled across remaining deck)",
        "auto": f"Opponent AI: {ai_label}",
        "hit_to_threshold": f"Opponent AI: {ai_label}",
    }.get(behavior_key, f"Opponent AI: {ai_label}")

    # Rough estimate for potential damage if you lose (for messaging only)
    estimated_opp = max(o_visible_total, expected_opp_stay)
    if u_total <= target:
        potential_loss_dmg = max(1, estimated_opp - u_total)
    else:
        potential_loss_dmg = (u_total - target) + max(0, target - estimated_opp)

    if u_total == target:
        advice_lines.append(f"★ PERFECT {target}! STAY. Best possible hand.")
        return priority_warnings, advice_lines

    if u_total > target:
        advice_lines.append(f"✖ BUSTED ({u_total} > {target})! Use 'Return' or 'Exchange' immediately!")
        if available_trumps and "Go for 27" in available_trumps and u_total <= 27 and target < 27:
            advice_lines.append(
                f"UNLOCKED: 'Go for 27' saves you — your {u_total} isn't bust at target 27! Press G to switch."
            )
        return priority_warnings, advice_lines

    # Outcome model: compare staying now vs hitting now using selected opponent behavior.
    stay_probs, hit_probs = evaluate_stay_hit_outcomes(
        u_total, o_visible_total, remaining, stay_val, target, behavior_key,
        banker_ai=banker_ai,
    )
    bust_pct = 100.0 - safe_pct
    advice_lines.append(f"MODEL: {behavior_label}.")
    if behavior_key == "stay":
        advice_lines.append("(Opponent stopped — hidden card modeled across all remaining cards.)")
    else:
        advice_lines.append("(Opponent hasn't stayed — odds are estimates. Select '2' when they stop drawing.)")
    advice_lines.append(
        "If YOU STAY now -> "
        f"Win {stay_probs['win'] * 100:.1f}% | Tie {stay_probs['tie'] * 100:.1f}% | "
        f"Lose {stay_probs['loss'] * 100:.1f}%."
    )
    advice_lines.append(
        "If YOU HIT now -> "
        f"Win {hit_probs['win'] * 100:.1f}% | Tie {hit_probs['tie'] * 100:.1f}% | "
        f"Lose {hit_probs['loss'] * 100:.1f}% (Bust draw chance: {bust_pct:.1f}%)."
    )

    # Force draw analysis (Love Your Enemy — only if player holds it)
    force_probs = None
    opp_bust_from_force = 0.0
    has_lye = "Love Your Enemy" in hand_set
    if remaining and behavior_key != "stay" and has_lye:
        force_probs = {"win": 0.0, "tie": 0.0, "loss": 0.0}
        card_weight = 1.0 / len(remaining)
        opp_bust_count = 0

        for forced_card in remaining:
            new_opp_total = o_visible_total + forced_card
            if new_opp_total > target:
                opp_bust_count += 1
            after_remaining = [c for c in remaining if c != forced_card]
            # After forced draw, opponent continues with normal AI
            opp_dist = opponent_total_distribution(
                new_opp_total, after_remaining, stay_val, target,
                behavior="auto", banker_ai=banker_ai, player_visible_total=u_total,
            )
            outcome = outcome_probabilities(u_total, opp_dist, target)
            force_probs["win"] += outcome["win"] * card_weight
            force_probs["tie"] += outcome["tie"] * card_weight
            force_probs["loss"] += outcome["loss"] * card_weight

        opp_bust_from_force = (opp_bust_count / len(remaining)) * 100
        advice_lines.append(
            "If you FORCE A DRAW (Love Your Enemy) -> "
            f"Win {force_probs['win'] * 100:.1f}% | Tie {force_probs['tie'] * 100:.1f}% | "
            f"Lose {force_probs['loss'] * 100:.1f}% "
            f"(busts opponent: {opp_bust_from_force:.0f}%)."
        )

    # ── Bust-win challenge analysis ─────────────────────────────────────────
    if challenges_completed is None:
        challenges_completed = set()
    if available_trumps is None:
        available_trumps = set()
    bust_challenge_done = "bust_win" in challenges_completed

    # Always compute bust inline result for use in action recommendation
    bust_result = None
    bust_cards = [c for c in remaining if u_total + c > target]
    if bust_cards and behavior_key != "stay":
        bust_result = evaluate_bust_inline(
            u_total, o_visible_total, remaining, stay_val, target, behavior_key, banker_ai=banker_ai
        )
        if bust_result and bust_result["win_pct"] >= 0.15:
            label = "INTENTIONAL BUST (challenge)" if not bust_challenge_done else "INTENTIONAL BUST"
            advice_lines.append(
                f"If you BUST ON PURPOSE [{label}] -> "
                f"best card: [{bust_result['best_card']}] (total {bust_result['bust_total']}) -> "
                f"Win {bust_result['win_pct'] * 100:.1f}%."
            )
        else:
            bust_result = None

    # ── Action recommendation ─────────────────────────────────────────────────
    options = {
        "STAY": stay_probs["win"],
        "HIT":  hit_probs["win"],
    }
    if force_probs is not None:
        options["FORCE DRAW (Love Your Enemy)"] = force_probs["win"]
    if bust_result and bust_result["win_pct"] >= 0.15:
        options["INTENTIONAL BUST"] = bust_result["win_pct"]

    best_option = max(options, key=options.get)
    best_win    = options[best_option]
    second_best = max(v for k, v in options.items() if k != best_option)
    win_edge    = best_win - second_best

    # Low-HP nudge: prefer STAY over a marginal HIT when bust risk is high
    if best_option == "HIT" and player_hp <= 2 and safe_pct < 50 and win_edge < 0.05:
        best_option = "STAY"
        best_win    = options["STAY"]
        win_edge    = best_win - options["HIT"]

    close_note = " (close call)" if abs(win_edge) < 0.05 else ""

    if win_edge >= 0.15 and not (player_hp <= 3 and safe_pct < 50 and best_option == "HIT"):
        advice_lines.append(
            f"ACTION: {best_option} — best win chance at {best_win * 100:.1f}% "
            f"(+{win_edge * 100:.1f}% over next best)."
        )
        return priority_warnings, advice_lines

    if safe_pct == 100:
        advice_lines.append("ACTION: HIT — every remaining card is safe. Free draw!")
        return priority_warnings, advice_lines

    if perfect_draws and safe_pct >= 50:
        advice_lines.append(
            f"ACTION: HIT — can reach {target} with {sorted(perfect_draws)}. Safe chance: {safe_pct:.0f}%."
        )
        return priority_warnings, advice_lines

    if u_total >= stay_val and u_total >= estimated_opp:
        advice_lines.append(f"ACTION: STAY — your {u_total} likely meets/beats his ~{estimated_opp}.")
        return priority_warnings, advice_lines

    if safe_pct >= 60:
        advice_lines.append(f"ACTION: HIT — {safe_pct:.0f}% safe. Good odds.")
    elif safe_pct >= 40:
        if player_hp <= 3:
            advice_lines.append(
                f"ACTION: STAY (LOW HP) — {safe_pct:.0f}% is too risky at {player_hp} HP.\n"
                f"Potential loss damage: ~{potential_loss_dmg}. Consider a shield/trump."
            )
        elif u_total < estimated_opp:
            advice_lines.append(
                f"ACTION: RISKY HIT — {safe_pct:.0f}% safe, but {u_total} likely loses to ~{estimated_opp}.\n"
                "Consider Perfect Draw / Exchange / Love Your Enemy instead."
            )
        else:
            advice_lines.append(f"ACTION: STAY — {safe_pct:.0f}% safe is marginal; your {u_total} might hold.")
    else:
        if u_total < estimated_opp:
            advice_lines.append(
                f"ACTION: USE TRUMP — only {safe_pct:.0f}% safe and {u_total} likely loses to ~{estimated_opp}.\n"
                "Try Perfect Draw / Exchange / Love Your Enemy / Shield."
            )
        else:
            advice_lines.append(f"ACTION: STAY — too risky ({safe_pct:.0f}% safe). Hope he busts or {u_total} holds.")

    # Bust challenge nudge inline (brief — full panel shown when player presses B)
    if bust_result and not bust_challenge_done and bust_result["win_pct"] >= 0.15:
        if "BUST" not in advice_lines[-1]:
            advice_lines.append(
                f"  ★ Bust challenge: draw [{bust_result['best_card']}] -> {bust_result['bust_total']} "
                f"({bust_result['win_pct'] * 100:.0f}% win). "
                f"Press B in fight menu for full bust analysis."
            )

    return priority_warnings, advice_lines


def bust_outcome(your_total: int, opp_total: int, target: int) -> str:
    """Resolve bust-vs-bust outcome for challenge calculations."""
    if your_total <= target:
        return "NOT_BUST"
    if opp_total <= target:
        return "LOSS"

    your_over = your_total - target
    opp_over = opp_total - target
    if your_over < opp_over:
        return "WIN"
    if your_over == opp_over:
        return "TIE"
    return "LOSS"


def evaluate_bust_challenge(u_total: int, o_visible_total: int, remaining, target: int, hidden_candidates):
    """
    Evaluate odds for the priority challenge (win while bust).
    Modes:
      - stay: bust then stay
      - force_random: bust then force random draw on opponent
      - force_highest: bust then force highest draw on opponent
    """
    modes = ("stay", "force_random", "force_highest")
    mode_results = {m: [] for m in modes}

    for draw_card in sorted(remaining):
        your_total = u_total + draw_card
        if your_total <= target:
            continue

        deck_after_you = [c for c in remaining if c != draw_card]
        valid_hidden = [h for h in hidden_candidates if h != draw_card]
        if not valid_hidden:
            continue

        for mode in modes:
            wins = 0.0
            ties = 0.0
            losses = 0.0
            hidden_weight = 1.0 / len(valid_hidden)

            for hidden in valid_hidden:
                opp_base_total = o_visible_total + hidden
                deck_after_hidden = [c for c in deck_after_you if c != hidden]

                if mode == "stay":
                    outcomes = [opp_base_total]
                    weights = [1.0]
                elif mode == "force_highest":
                    if deck_after_hidden:
                        outcomes = [opp_base_total + max(deck_after_hidden)]
                    else:
                        outcomes = [opp_base_total]
                    weights = [1.0]
                else:  # force_random
                    if deck_after_hidden:
                        outcomes = [opp_base_total + c for c in deck_after_hidden]
                        weights = [1.0 / len(outcomes)] * len(outcomes)
                    else:
                        outcomes = [opp_base_total]
                        weights = [1.0]

                for opp_total, weight in zip(outcomes, weights):
                    outcome = bust_outcome(your_total, opp_total, target)
                    p = hidden_weight * weight
                    if outcome == "WIN":
                        wins += p
                    elif outcome == "TIE":
                        ties += p
                    elif outcome == "LOSS":
                        losses += p

            mode_results[mode].append(
                {
                    "draw_card": draw_card,
                    "your_total": your_total,
                    "your_over": your_total - target,
                    "win": wins,
                    "tie": ties,
                    "loss": losses,
                }
            )

    best_by_mode = {}
    for mode, rows in mode_results.items():
        if not rows:
            best_by_mode[mode] = None
        else:
            best_by_mode[mode] = max(rows, key=lambda r: (r["win"], -r["loss"], -r["your_over"]))

    return mode_results, best_by_mode


# ============================================================
# ROUND RESULT RECORDING
# ============================================================
def record_round_result(round_num: int, player_hp: int, opp_hp: int, intel: dict = None):
    """
    Ask what happened and update HP.
    Damage in RE7 21 is based on the bet amount, not score difference.
    - Survival: 1 finger per loss (base bet = 1)
    - Survival+/Normal: voltage/saw moves by the bet amount
    Returns: (new_player_hp, new_opp_hp, round_entry_dict or None)
    """
    enemy_trumps = set(intel.get("trumps", [])) if intel else set()
    can_void = "Escape" in enemy_trumps or "Oblivion" in enemy_trumps

    print_header("ROUND RESULT")
    print(" What happened this round?\n")
    print(" 1. I WON")
    print(" 2. I LOST")
    print(" 3. TIE (no damage)")
    if can_void:
        print(" 4. VOID (Escape / Oblivion cancelled)")
    print(" 5. Cancel (go back)")

    choice = input("\n Result (1-5): ").strip()

    if choice == "5":
        return player_hp, opp_hp, None

    if choice == "4":
        entry = {"round": round_num, "result": "VOID", "damage": 0, "damage_to": "none"}
        print(" Round voided. No HP changes.")
        return player_hp, opp_hp, entry

    if choice == "3":
        entry = {"round": round_num, "result": "TIE", "damage": 0, "damage_to": "none"}
        print(" Tie. No HP changes.")
        return player_hp, opp_hp, entry

    if choice not in ("1", "2"):
        print(" Invalid choice.")
        return player_hp, opp_hp, None

    try:
        print("\n How much damage was dealt?")
        print(" (The bet amount shown on screen — base is 1, trumps raise it)")
        dmg_input = input(" Damage: ").strip()
        actual_dmg = int(dmg_input) if dmg_input else 1
        actual_dmg = max(0, actual_dmg)

        if choice == "1":
            print(f"\n → {actual_dmg} damage to opponent!")
            opp_hp = max(0, opp_hp - actual_dmg)
            entry = {
                "round": round_num,
                "result": "WIN",
                "damage": actual_dmg,
                "damage_to": "opponent",
            }
        else:
            print(f"\n → {actual_dmg} damage to YOU!")
            player_hp = max(0, player_hp - actual_dmg)
            entry = {
                "round": round_num,
                "result": "LOSS",
                "damage": actual_dmg,
                "damage_to": "you",
            }

        return player_hp, opp_hp, entry

    except ValueError:
        print(" Error reading value. Skipping.")
        return player_hp, opp_hp, None


# ============================================================
# SINGLE ROUND ANALYSIS
# ============================================================
def analyze_round(intel: dict, player_hp: int, player_max: int, opp_hp: int, opp_max: int, target: int = 21, dead_cards: list = None, challenges_completed: set = None, available_trumps: set = None, trump_hand: list = None, fight_num: int = 0, mode_key: str = "3", face_down_card: int = None, player_visible: list = None, opp_visible: list = None, banker_ai: "BankerAI" = None, condition_state: "TrumpConditionState" = None) -> tuple:
    """Run the solver for one round of 21 (read-only, no HP changes).
    Returns (updated_dead_cards, face_down_card, player_visible, opp_visible) for persistence."""
    if dead_cards is None:
        dead_cards = []
    if player_visible is None:
        player_visible = []
    if opp_visible is None:
        opp_visible = []
    display_hp_status(player_hp, player_max, opp_hp, opp_max, intel["name"])

    print(f"\n Current target: {target}")
    if target != 21:
        print(f" ★ 'Go for {target}' is ACTIVE!")

    # Default to normal AI behavior; override only if needed
    opp_behavior = "auto"

    try:
        # ── HAND MEMORY ──
        # Face-down card is locked once set (only trumps like Exchange/Return change it).
        # Visible cards accumulate as you draw. On re-analyze, just add new draws.
        has_memory = face_down_card is not None

        if has_memory:
            # Show current remembered state
            full_hand = [face_down_card] + player_visible
            print(f"\n ── REMEMBERED STATE ──")
            print(f" Your hand: {full_hand} (total {sum(full_hand)})")
            print(f"   Face-down: {face_down_card} (locked)")
            if player_visible:
                print(f"   Visible: {player_visible}")
            if opp_visible:
                print(f" Opponent visible: {opp_visible} (total {sum(opp_visible)})")

            # Ask for new draws since last analyze
            print(f"\n Did you draw new cards? (space-separated, or Enter = no change)")
            new_draw = input(" Your new cards: ").strip()
            if new_draw:
                try:
                    new_cards = [int(x) for x in new_draw.split()]
                    for c in new_cards:
                        if 1 <= c <= 11:
                            if c not in player_visible and c != face_down_card:
                                player_visible.append(c)
                            else:
                                print(f" ⚠ Card {c} already in your hand, skipping.")
                        else:
                            print(f" ⚠ Card {c} invalid (1-11).")
                except ValueError:
                    print(" Invalid input, keeping current.")

            print(f" Did opponent draw new cards? (space-separated, or Enter = no)")
            new_opp = input(" Opponent new cards: ").strip()
            if new_opp:
                try:
                    new_cards = [int(x) for x in new_opp.split()]
                    for c in new_cards:
                        if 1 <= c <= 11:
                            if c not in opp_visible:
                                opp_visible.append(c)
                            else:
                                print(f" ⚠ Card {c} already in opponent hand, skipping.")
                        else:
                            print(f" ⚠ Card {c} invalid (1-11).")
                except ValueError:
                    print(" Invalid input, keeping current.")

        else:
            # First analyze this round — get all cards from scratch
            print(f"\n Enter YOUR face-down card (the hidden card dealt to you):")
            fd_input = input(" Face-down card: ").strip()
            if not fd_input:
                print(" No cards entered.")
                return dead_cards, face_down_card, player_visible, opp_visible
            face_down_card = int(fd_input)
            if face_down_card < 1 or face_down_card > 11:
                print(f" ERROR: Card {face_down_card} invalid (1–11).")
                face_down_card = None
                return dead_cards, face_down_card, player_visible, opp_visible

            print(f" Enter your visible drawn card(s) (space-separated, or Enter if none yet):")
            vis_input = input(" Visible cards: ").strip()
            if vis_input:
                player_visible = [int(x) for x in vis_input.split()]
            else:
                player_visible = []

            print(" Enter OPPONENT'S visible card(s) (space-separated):")
            o_input = input(" Opponent cards: ").strip()
            if not o_input:
                print(" No opponent cards entered.")
                return dead_cards, face_down_card, player_visible, opp_visible
            opp_visible = [int(x) for x in o_input.split()]

        # Build full hands from memory
        u_hand = [face_down_card] + player_visible
        o_vis = list(opp_visible)

        for c in u_hand + o_vis:
            if c < 1 or c > 11:
                print(f" ERROR: Card {c} invalid (1–11).")
                return dead_cards, face_down_card, player_visible, opp_visible

        if dead_cards:
            print(f" Remembered dead cards: {sorted(dead_cards)}")
            print(" Additional dead/removed cards? (Enter = none)")
        else:
            print(" Dead/removed cards? (Enter = none)")
        d_input = input(" Dead cards: ").strip()
        new_dead = list(map(int, d_input.split())) if d_input else []
        for c in new_dead:
            if c < 1 or c > 11:
                print(f" ERROR: Card {c} invalid (1–11).")
                return dead_cards, face_down_card, player_visible, opp_visible
        dead = sorted(set(dead_cards + new_dead))

        # Duplicate check (deck has one of each)
        all_cards = u_hand + o_vis + dead
        seen = set()
        for c in all_cards:
            if c in seen:
                print(f" ⚠ WARNING: Card {c} entered twice! (Deck has one of each)")
            seen.add(c)

        accounted = sorted(set(all_cards))
        remaining = [c for c in range(1, 12) if c not in accounted]
        u_total = sum(u_hand)
        o_total = sum(o_vis)

        # What did the opponent do?
        print("\n Has the opponent stopped drawing? (y = yes, Enter = still playing)")
        beh_input = input(" > ").strip().lower()
        if beh_input == "y":
            opp_behavior = "stay"
            print(f" → Opponent stopped. Visible total: {o_total}")
            print(f"   Hidden card is one of: {sorted(remaining)}")
            print(f"   Possible totals: {sorted(o_total + c for c in remaining)}")
        else:
            opp_behavior = "auto"

        display_card_matrix(accounted)

        safe_pct, bust_pct, perfect_draws = calculate_probabilities(remaining, u_total, target)
        safe_count = len([c for c in remaining if u_total + c <= target])

        opp_label = "OPPONENT STAYED (visible)" if opp_behavior == "stay" else "OPPONENT VISIBLE"
        print(f"\n YOUR TOTAL: {u_total} (cards: {u_hand})")
        print(f" {opp_label}: {o_total} (cards: {o_vis})")
        print(f" TARGET: {target}")
        print(f" SAFE HIT CHANCE: {safe_pct:.0f}% ({safe_count}/{len(remaining)} cards)")
        print(f" BUST CHANCE: {bust_pct:.0f}%")

        if perfect_draws:
            print(f" PERFECT DRAW: Card(s) {sorted(perfect_draws)} → exactly {target}!")

        if remaining:
            print("\n If you draw:")
            for c in sorted(remaining):
                new_total = u_total + c
                status = "✓" if new_total <= target else "✖ BUST"
                perfect = " ★ PERFECT!" if new_total == target else ""
                print(f"  Card {c:>2} → total {new_total:>2} {status}{perfect}")

        # Strategic advice
        print_header("STRATEGY ADVICE")

        # Use passed-in BankerAI profile (already resolved by fight_opponent)
        _banker_ai = banker_ai if banker_ai is not None else get_banker_ai(intel)

        # Update live fields on passed-in condition_state; fall back to fresh one
        if condition_state is not None:
            _cond = condition_state
            _cond.banker_hand_sum = o_total
            _cond.player_hand_sum = u_total
            _cond.player_item_num = len(trump_hand) if trump_hand else 0
        else:
            _cond = TrumpConditionState()
            _cond.banker_hand_sum = o_total
            _cond.player_hand_sum = u_total
            _cond.player_item_num = len(trump_hand) if trump_hand else 0

        # Compute stay win% to share with both advice and trump recommendation
        _stay_val = int(intel.get("stay_val", 17))
        if target != 21:
            _stay_val += (target - 21)
            _stay_val = max(1, _stay_val)
        _stay_win_pct = None
        if u_total <= target and remaining:
            try:
                sp, _ = evaluate_stay_hit_outcomes(
                    u_total, o_total, remaining, _stay_val, target, opp_behavior,
                    banker_ai=_banker_ai,
                )
                _stay_win_pct = sp.get("win", 0.5)
            except Exception:
                _stay_win_pct = 0.5

        warnings, advice = generate_advice(
            u_total, o_total, intel, remaining, target, safe_pct, perfect_draws,
            player_hp, player_max, opp_hp, opp_max, opp_behavior,
            challenges_completed, available_trumps, trump_hand,
            banker_ai=_banker_ai, condition_state=_cond,
        )
        for w in warnings:
            print(f"\n \033[91m{w}\033[0m")
        for a in advice:
            print(f"\n {a}")

        # Trump card play recommendations (suppressed when not needed)
        if trump_hand:
            import re as _re
            trump_recs = recommend_trump_play(
                trump_hand, u_total, o_total, remaining, target, _stay_val,
                intel, player_hp, opp_hp, opp_behavior,
                fight_num=fight_num, mode_key=mode_key,
                stay_win_pct=_stay_win_pct
            )
            if trump_recs:
                print("\n ┌─ TRUMP CARD ADVICE ─────────────────────────────┐")
                for rec in trump_recs:
                    # Strip ANSI for width calculation
                    clean = _re.sub(r'\033\[[0-9;]*m', '', rec)
                    while len(clean) > 53:
                        # Print first 53 visible chars
                        print(f" │ {rec[:53 + (len(rec) - len(clean))]}│")
                        rec = rec[53 + (len(rec) - len(clean)):]
                        clean = _re.sub(r'\033\[[0-9;]*m', '', rec)
                    pad = 53 - len(clean)
                    print(f" │ {rec}{' ' * pad}│")
                print(" └─────────────────────────────────────────────────┘")

        print("\n" + "=" * 60)

        return dead, face_down_card, player_visible, opp_visible

    except ValueError:
        print(" ERROR: Enter valid numbers only.")
        return dead_cards, face_down_card, player_visible, opp_visible


# ============================================================
# FIGHT LOOP — Multiple rounds vs. one opponent until death
# ============================================================

def apply_trump_usage(trump_hand: list, raw: str) -> list:
    """Remove trumps from hand by index number(s) (space-separated)."""
    raw = (raw or "").strip()
    if not raw:
        return trump_hand
    try:
        indices = sorted({int(x) - 1 for x in raw.split()}, reverse=True)
        for idx in indices:
            if 0 <= idx < len(trump_hand):
                print(f"  - USED: {trump_hand.pop(idx)}")
            else:
                print(f"  ! No card at #{idx + 1}")
    except ValueError:
        print(" ! Enter numbers only (e.g. '1 3')")
    return trump_hand


def apply_trump_additions(trump_hand: list, raw: str, available_trumps: set = None) -> list:
    """Add trumps to hand by number(s) from PLAYER_TRUMPS list (space-separated)."""
    raw = (raw or "").strip()
    if not raw:
        return trump_hand
    pool = [c for c in PLAYER_TRUMPS if not available_trumps or c not in UNLOCKABLE or c in available_trumps]
    try:
        for idx in [int(x) - 1 for x in raw.split()]:
            if 0 <= idx < len(pool):
                trump_hand.append(pool[idx])
                print(f"  + GAINED: {pool[idx]}")
            else:
                print(f"  ! No card #{idx + 1} in list (max {len(pool)})")
    except ValueError:
        print(" ! Enter numbers only (e.g. '3 7')")
    return trump_hand


def show_trump_addition_list(available_trumps: set = None) -> None:
    """Print numbered PLAYER_TRUMPS list so user can add by number."""
    pool = [c for c in PLAYER_TRUMPS if not available_trumps or c not in UNLOCKABLE or c in available_trumps]
    print("\n ┌─ TRUMP LIST ─────────────────────────────────────┐")
    for i, name in enumerate(pool, 1):
        desc = TRUMPS.get(name, {}).get("desc", "")
        print(f" │ {i:>2}. {name:<20s} {desc[:32]:<32s}│")
    print(" └─────────────────────────────────────────────────┘")


def analyze_board_state(
    intel: dict, player_hp: int, player_max: int, opp_hp: int, opp_max: int,
    target: int, dead_cards: list, challenges_completed: set, available_trumps: set,
    trump_hand: list, *, fight_num: int = 0, mode_key: str = "3",
    face_down_card: int, player_visible: list, opp_visible: list,
    opp_behavior: str = "auto", banker_ai: "BankerAI" = None,
    condition_state: "TrumpConditionState" = None,
) -> None:
    """
    Pure display — no input(). Prints the full board state + advice.
    Called after every action (H/O/P/I/S) so the board always reflects current state.
    """
    clear_screen()
    display_hp_status(player_hp, player_max, opp_hp, opp_max, intel["name"])

    if face_down_card is None:
        print(" ⚠  No face-down card set yet.")
        return

    u_hand = [face_down_card] + list(player_visible)
    o_vis  = list(opp_visible)

    # Sync condition_state live fields
    if condition_state is not None and o_vis:
        condition_state.banker_last_faceup  = o_vis[-1]
        condition_state.banker_visible_count = len(o_vis)
        condition_state.banker_hand_sum     = sum(o_vis)
        condition_state.player_hand_sum     = sum(u_hand)

    dead       = sorted(set(dead_cards or []))
    all_seen   = set(u_hand + o_vis + dead)
    remaining  = [c for c in range(1, 12) if c not in all_seen]
    u_total    = sum(u_hand)
    o_total    = sum(o_vis)

    if target != 21:
        print(f"\n ★ TARGET IS {target}!")

    if opp_behavior == "stay":
        print(f"\n → Opponent STAYED. Their visible total: {o_total}")
        print(f"   Hidden card is one of: {sorted(remaining)}")
        print(f"   Possible totals: {sorted(o_total + c for c in remaining)}")

    display_card_matrix(sorted(all_seen))
    safe_pct, bust_pct, perfect_draws = calculate_probabilities(remaining, u_total, target)
    safe_count = len([c for c in remaining if u_total + c <= target])

    opp_label = "OPPONENT STAYED" if opp_behavior == "stay" else "OPPONENT VISIBLE"
    print(f"\n YOUR TOTAL : {u_total}  (cards: {u_hand})")
    print(f" {opp_label}: {o_total}  (cards: {o_vis})")
    print(f" TARGET     : {target}")
    print(f" SAFE HIT   : {safe_pct:.0f}%  ({safe_count}/{len(remaining)} cards safe)")
    print(f" BUST RISK  : {bust_pct:.0f}%")
    if perfect_draws:
        print(f" PERFECT    : {sorted(perfect_draws)} → exactly {target}!")

    if remaining:
        print("\n Draw outcomes:")
        for c in sorted(remaining):
            new_tot = u_total + c
            ok      = "✓" if new_tot <= target else "✖ BUST"
            star    = " ★ PERFECT!" if new_tot == target else ""
            print(f"  [{c:>2}] → {new_tot:<2} {ok}{star}")

    # Derive stay_val for advice engine
    stay_val = int(intel.get("stay_val", 17))
    if target != 21:
        stay_val = max(1, stay_val + (target - 21))
    if banker_ai is not None:
        stay_val = banker_ai.take_card_border

    _stay_win_pct = None
    if u_total <= target and remaining:
        try:
            sp, _ = evaluate_stay_hit_outcomes(
                u_total, o_total, remaining, stay_val, target, opp_behavior, banker_ai=banker_ai
            )
            _stay_win_pct = sp.get("win", 0.5)
        except Exception:
            _stay_win_pct = 0.5

    print_header("STRATEGY ADVICE")
    warnings, advice = generate_advice(
        u_total, o_total, intel, remaining, target, safe_pct, perfect_draws,
        player_hp, player_max, opp_hp, opp_max, opp_behavior,
        challenges_completed, available_trumps, trump_hand,
        banker_ai=banker_ai, condition_state=condition_state,
    )
    for w in warnings:
        print(f"\n \033[91m{w}\033[0m")
    for a in advice:
        print(f"\n {a}")

    if trump_hand:
        trump_recs = recommend_trump_play(
            trump_hand, u_total, o_total, remaining, target, stay_val,
            intel, player_hp, opp_hp, opp_behavior,
            fight_num=fight_num, mode_key=mode_key, stay_win_pct=_stay_win_pct,
        )
        if trump_recs:
            print("\n ┌─ TRUMP CARD ADVICE ─────────────────────────────┐")
            for rec in trump_recs:
                clean = re.sub(r'\033\[[0-9;]*m', '', rec)
                while len(clean) > 53:
                    print(f" │ {rec[:53 + (len(rec) - len(clean))]}│")
                    rec   = rec[53 + (len(rec) - len(clean)):]
                    clean = re.sub(r'\033\[[0-9;]*m', '', rec)
                pad = 53 - len(clean)
                print(f" │ {rec}{' ' * pad}│")
            print(" └─────────────────────────────────────────────────┘")

    print("\n" + "=" * 60)
def handle_interrupt(dead_cards: list, current_target: int, player_bet: int = 1, opp_bet: int = 1, player_visible: list = None, opp_visible: list = None, face_down_card: int = None, intel: dict = None, trump_hand: list = None, condition_state: "TrumpConditionState" = None) -> tuple:
    """
    Interrupt handler: enemy played a trump card mid-round.
    Shows opponent's known trumps and walks through effects step by step.
    Returns updated (dead_cards, current_target, player_bet, opp_bet, interrupt_msg,
                     player_visible, opp_visible, face_down_card, trump_hand).
    """
    if player_visible is None:
        player_visible = []
    if opp_visible is None:
        opp_visible = []
    if trump_hand is None:
        trump_hand = []

    # Build opponent's trump list
    opp_trumps = list(intel.get("trumps", [])) if intel else []
    std_trumps = list(intel.get("standard_trumps", [])) if intel else []
    all_opp_trumps = opp_trumps + std_trumps

    # Also check trump_behavior for detailed info
    trump_behavior = intel.get("trump_behavior", {}) if intel else {}

    print("\n ┌─ ENEMY TRUMP INTERRUPT ──────────────────────────┐")
    if all_opp_trumps:
        print(f" │ {intel['name']}'s known trumps:")
        for i, t in enumerate(all_opp_trumps, 1):
            note = ""
            if t in trump_behavior:
                note = f" — {trump_behavior[t].get('note', '')[:40]}"
            label = f"  {i}. {t}{note}"
            print(f" │{label[:53]:<53s}│")
    print(" │                                                   │")
    print(" │  O. Other / unlisted trump                        │")
    print(" │  0. Cancel                                        │")
    print(" └───────────────────────────────────────────────────┘")

    choice = input("\n > ").strip().upper()
    msg = ""

    if choice == "0":
        return dead_cards, current_target, player_bet, opp_bet, "", player_visible, opp_visible, face_down_card, trump_hand

    # Determine which trump was played
    played_trump = None
    if choice == "O":
        print(" What did the opponent play? (type trump name or describe)")
        played_trump = input(" > ").strip()
    else:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(all_opp_trumps):
                played_trump = all_opp_trumps[idx]
        except ValueError:
            pass

    if not played_trump:
        print(" Invalid selection.")
        return dead_cards, current_target, player_bet, opp_bet, "", player_visible, opp_visible, face_down_card, trump_hand

    # ── HANDLE EFFECTS BY TRUMP NAME ──
    pt = played_trump.lower().strip()

    # --- CARD DRAWS (Conjure, Happiness, etc.) ---
    if pt in ("conjure",):
        # Opponent draws 3 trumps, their bet +1
        opp_bet += 1
        msg = f"{played_trump}: Opponent draws 3 trumps, their bet +1 → {opp_bet}. (Slight advantage for you)"

    elif pt in ("happiness",):
        msg = f"{played_trump}: Both players draw a trump card."
        print(" Did you draw a trump? Use W to add it after.")

    # --- BET MODIFIERS ---
    elif pt in ("desire",):
        print(f" How many trumps do YOU hold? (currently {len(trump_hand)} tracked)")
        tc = input(" > ").strip()
        try:
            count = int(tc) if tc else len(trump_hand)
            amt = max(1, count // 2)
            player_bet += amt
            msg = f"{played_trump}: YOUR bet +{amt} (half your {count} trumps) → now {player_bet}"
        except ValueError:
            msg = f"{played_trump} played. Check your bet on screen."

    elif pt in ("desire+",):
        print(f" How many trumps do YOU hold? (currently {len(trump_hand)} tracked)")
        tc = input(" > ").strip()
        try:
            count = int(tc) if tc else len(trump_hand)
            player_bet += count
            msg = f"{played_trump}: YOUR bet +{count} (full trump count) → now {player_bet}"
        except ValueError:
            msg = f"{played_trump} played. Check your bet on screen."

    elif pt in ("shield assault",):
        player_bet += 3
        msg = f"{played_trump}: YOUR bet +3 → now {player_bet}. He sacrificed 3 Shields."

    elif pt in ("shield assault+",):
        player_bet += 5
        msg = f"{played_trump}: YOUR bet +5 → now {player_bet}."

    elif pt in ("one-up",):
        opp_bet += 1
        msg = f"{played_trump}: Opponent's bet +1 → now {opp_bet}"

    elif pt in ("two-up", "two-up+"):
        amt = 2 if pt == "two-up" else 3
        opp_bet += amt
        msg = f"{played_trump}: Opponent's bet +{amt} → now {opp_bet}"

    # --- SHIELDS ---
    elif pt in ("shield", "shield+"):
        opp_bet = max(0, opp_bet - 1)
        msg = f"{played_trump}: Opponent's bet -1 → now {opp_bet}"

    # --- TARGET MODIFIERS ---
    elif pt in ("go for 17",):
        current_target = 17
        msg = f"★ TARGET CHANGED TO 17! Your 18+ is now a bust!"

    elif pt in ("go for 24",):
        current_target = 24
        msg = f"Target changed to 24."

    # --- BOARD WIPES ---
    elif pt in ("destroy", "destroy+", "destroy++"):
        msg = f"★ {played_trump}: Enemy destroyed your table trump(s)! Use W to update hand."
        print(" Which of your trumps were destroyed? Use W after to remove them.")

    # --- DECK MANIPULATION ---
    elif pt in ("curse",):
        print(" Step 1: You lost a trump card. Use W after to remove it.")
        print(" Step 2: What card were you FORCED to draw? (highest in deck)")
        v = input(" Forced card value: ").strip()
        if v:
            try:
                val = int(v)
                if 1 <= val <= 11:
                    dead_cards = sorted(set(dead_cards + [val]))
                    if val not in player_visible and val != face_down_card:
                        player_visible.append(val)
                    msg = f"★ Cursed! Lost a trump + forced draw: {val}. Your new total includes {val}."
            except ValueError:
                msg = "Curse played. Couldn't parse forced card."
        else:
            msg = "Curse played. Enter forced card via A (re-analyze)."

    elif pt in ("black magic",):
        print(" Step 1: You lost half your trumps.")
        print(" Step 2: YOUR bet increased by how much?")
        v = input(" Bet increase: ").strip()
        try:
            amt = int(v) if v else 10
            player_bet += amt
            msg = f"★★ BLACK MAGIC! YOUR bet +{amt} → now {player_bet}. Lost half trumps. Use W to update."
        except ValueError:
            player_bet += 10
            msg = f"★★ BLACK MAGIC! YOUR bet +10 → now {player_bet}. LETHAL if you lose!"
        if condition_state is not None:
            condition_state.black_magic_uses += 1

    # --- CONTROL TRUMPS ---
    elif pt in ("dead silence",):
        msg = "★ DEAD SILENCE active — you CANNOT draw cards! Use Destroy to remove it."

    elif pt in ("oblivion",):
        msg = "★ OBLIVION — round is cancelled. Press D to end round as VOID."

    elif pt in ("mind shift",):
        print(" Did you play 2+ trumps this round? (y/n)")
        safe = input(" > ").strip().lower()
        if safe == "y":
            msg = f"{played_trump}: Blocked! You played 2+ trumps."
        else:
            print(" You lose HALF your trumps. Use W to remove them.")
            msg = f"★ {played_trump}: Lost half your trumps! Use W to update."

    elif pt in ("mind shift+",):
        print(" Did you play 3+ trumps this round? (y/n)")
        safe = input(" > ").strip().lower()
        if safe == "y":
            msg = f"{played_trump}: Blocked! You played 3+ trumps."
        else:
            print(" You lose ALL your trumps. Use W to clear hand.")
            msg = f"★★ {played_trump}: Lost ALL trumps! Use W to clear."

    elif pt in ("escape",):
        msg = f"★ {played_trump}: Opponent can void the round if losing. Use Destroy to remove!"

    elif pt in ("remove",):
        print(" Which of YOUR face-up cards was removed from play this round?")
        v = input(" Card value (1-11): ").strip()
        if v.isdigit() and 1 <= int(v) <= 11:
            val = int(v)
            if val in player_visible:
                player_visible.remove(val)
            dead_cards = sorted(set(dead_cards + [val]))
            msg = f"{played_trump}: Removed your {val} from play (dead card)."
        else:
            print(" (No valid value entered; state not updated.)")
            msg = f"{played_trump}: Remove played (value unknown). Update if possible."

    # --- DRAW CARDS ---
    elif pt in ("perfect draw", "perfect draw+", "ultimate draw"):
        print(" What card did the opponent draw?")
        v = input(" Card value: ").strip()
        if v:
            try:
                val = int(v)
                if 1 <= val <= 11:
                    if val not in opp_visible:
                        opp_visible.append(val)
                    dead_cards = sorted(set(dead_cards + [val]))
                    msg = f"{played_trump}: Opponent drew {val}."
            except ValueError:
                msg = f"{played_trump} played."
        else:
            msg = f"{played_trump} played. Re-analyze when you see the card."

    elif pt in ("twenty-one up",):
        msg = f"★ {played_trump}: Opponent gets exactly 21! You must match or use trump to counter."

    # --- EXCHANGE ---
    elif pt in ("exchange", "return"):
        print(" What card did YOU lose?")
        gave_input = input(" Card lost: ").strip()
        print(" What card did YOU gain?")
        got_input = input(" Card gained: ").strip()
        try:
            gave = int(gave_input)
            got = int(got_input)
            if gave in player_visible:
                player_visible.remove(gave)
            elif gave == face_down_card:
                face_down_card = got
                got = None
            if got is not None and 1 <= got <= 11:
                player_visible.append(got)
            if gave not in opp_visible and 1 <= gave <= 11:
                opp_visible.append(gave)
            if got is not None and got in opp_visible:
                opp_visible.remove(got)
            msg = f"{played_trump}: Lost {gave_input}, gained {got_input}."
        except ValueError:
            msg = f"{played_trump}: Card swap. Re-analyze to update."

    # --- FALLBACK ---
    else:
        print(f" '{played_trump}' — describe what happened:")
        print("  1. Changed a card (drew/removed/swapped)")
        print("  2. Changed a bet")
        print("  3. Changed the target")
        print("  4. Other effect")
        sub = input(" > ").strip()
        if sub == "1":
            print(" What card value was affected?")
            v = input(" > ").strip()
            msg = f"{played_trump} played (card effect). Update via A/W/X."
        elif sub == "2":
            print(" How much did YOUR bet change? (+ or - number)")
            v = input(" > ").strip()
            try:
                player_bet += int(v)
                msg = f"{played_trump}: Your bet → {player_bet}"
            except ValueError:
                msg = f"{played_trump} played. Check bet on screen."
        elif sub == "3":
            print(" New target? (17/21/24/27)")
            v = input(" > ").strip()
            if v in ("17", "21", "24", "27"):
                current_target = int(v)
                msg = f"{played_trump}: Target → {current_target}"
            else:
                msg = f"{played_trump} played."
        else:
            desc = input(" Describe: ").strip()
            msg = f"{played_trump}: {desc}. Use W/X/A to update state."

    if msg:
        print(f"\n \033[96m→ {msg}\033[0m")
        print(" TIP: Press A to re-analyze with updated state.")

    return dead_cards, current_target, player_bet, opp_bet, msg, player_visible, opp_visible, face_down_card, trump_hand


def fight_opponent(intel: dict, player_hp: int, player_max: int,
                   challenges_completed: set = None, available_trumps: set = None,
                   mode_key: str = "3", fight_num: int = 1,
                   trump_hand: list = None) -> tuple:
    """
    Fight one opponent across multiple rounds until one side reaches 0 HP.
    Returns (player_hp, trump_hand) so the trump hand persists across fights.
    """
    if challenges_completed is None: challenges_completed = set()
    if available_trumps     is None: available_trumps     = set()
    if trump_hand           is None: trump_hand           = []

    opp_hp       = int(intel["hp"])
    opp_max      = int(intel["hp"])
    round_num    = 0
    round_history: list = []

    print_header(f"FIGHT: vs. {intel['name']}")

    # ── Variant selection ──────────────────────────────────────────────────────
    variants       = intel.get("variants", {})
    variant_ai_key = None
    if variants:
        variant_keys = list(variants.keys())
        print(f"\n ┌─ IDENTIFY THE VARIANT ─────────────────────────────────┐")
        print(f" │ Look at the sack on their head RIGHT NOW and count:    │")
        for i, key in enumerate(variant_keys, 1):
            v          = variants[key]
            visual     = v.get("visual_id", key)
            trumps_str = ", ".join(v["trumps"]) if v["trumps"] else "None"
            print(f" │   {i}. {visual:<52s} │")
            print(f" │      Trumps: {trumps_str:<47s} │")
        not_sure = len(variant_keys) + 1
        print(f" │   {not_sure}. Can't tell — use combined loadout{' ' * 21} │")
        print(f" └─────────────────────────────────────────────────────────┘")
        v_input = input("\n > ").strip()
        try:
            v_idx = int(v_input) - 1
            if 0 <= v_idx < len(variant_keys):
                chosen_key     = variant_keys[v_idx]
                chosen         = variants[chosen_key]
                intel          = dict(intel)
                intel["trumps"] = chosen["trumps"]
                intel["tip"]    = chosen["tip"]
                base_name       = intel["name"]
                intel["name"]   = f"{base_name} ({chosen_key})"
                variant_ai_key  = {
                    ("Barbed Wire Hoffman",      "3 wires"): "barbed_3w",
                    ("Barbed Wire Hoffman",      "4 wires"): "barbed_4w",
                    ("Bloody Handprints Hoffman","2 hands"): "bloody_s_plus",
                    ("Bloody Handprints Hoffman","4 hands"): "bloody_s_plus",
                }.get((base_name, chosen_key))
                print(f"\n ★ {chosen_key} — Trumps: {', '.join(chosen['trumps'])}")
            else:
                print(" Using combined loadout.")
        except (ValueError, IndexError):
            print(" Using combined loadout.")

    # ── AI models — persist for all rounds ────────────────────────────────────
    _banker_ai = get_banker_ai(intel, variant_key=variant_ai_key)
    _condition = TrumpConditionState()
    _condition.player_finger = player_hp
    _condition.banker_finger = opp_hp

    display_opponent_info(intel)

    # ── Starting trump hand (only prompt if empty — run_mode pre-fills it) ────
    if not trump_hand:
        print("\n Enter your starting trump cards:")
        trump_hand = edit_trump_hand([], available_trumps)

    # ── Lucas scripted round 3 helper ─────────────────────────────────────────
    def _lucas_round3() -> bool:
        if mode_key != "1" or round_num != 3:
            return False
        print("\n" + "=" * 60)
        print("\033[91m" + " ★★★ LUCAS SAW ROUND — SCRIPTED SEQUENCE ★★★".center(60) + "\033[0m")
        print("=" * 60)
        print("""
 Standard probability logic is SUSPENDED.

 WHAT WILL HAPPEN:
 • Lucas plays 'Perfect Draw' → guarantees himself 21
 • Lucas plays 'Desperation' → bets 100, drawing LOCKED

 WHAT YOU MUST DO:
 1. Have 'Love Your Enemy' in hand
 2. Wait for Desperation
 3. IMMEDIATELY play 'Love Your Enemy' → he busts → you win
""")
        print("=" * 60)
        input("\n Press Enter once this round concludes...")
        return True

    # helper — re-render the board after any state change
    def _render():
        if face_down_card is None:
            return
        analyze_board_state(
            intel, player_hp, player_max, opp_hp, opp_max, current_target,
            dead_cards, challenges_completed, available_trumps, trump_hand,
            fight_num=fight_num, mode_key=mode_key,
            face_down_card=face_down_card, player_visible=player_visible,
            opp_visible=opp_visible, opp_behavior=opp_behavior,
            banker_ai=_banker_ai, condition_state=_condition,
        )

    # ══════════════════════════════════════════════════════════════════════════
    # OUTER LOOP — one pass per round
    # ══════════════════════════════════════════════════════════════════════════
    while player_hp > 0 and opp_hp > 0:
        round_num     += 1
        current_target = 21
        player_bet     = 1
        opp_bet        = 1
        opp_behavior   = "auto"
        dead_cards     = []
        player_visible = []
        opp_visible    = []
        face_down_card = None

        _condition.round                   = round_num
        _condition.player_item_num         = len(trump_hand)
        _condition.player_finger           = player_hp
        _condition.banker_finger           = opp_hp
        _condition.banker_items_used_round = 0
        _condition.player_betup_active     = False

        print_header(f"ROUND {round_num} vs. {intel['name']}")
        display_round_history(round_history)
        display_hp_status(player_hp, player_max, opp_hp, opp_max, intel["name"])

        if _lucas_round3():
            player_hp, opp_hp, entry = record_round_result(round_num, player_hp, opp_hp, intel)
            if entry is not None:
                round_history.append(entry)
            continue

        # ── Initial card entry ─────────────────────────────────────────────
        while face_down_card is None:
            fd = input("\n Your face-DOWN card (hidden, 1-11): ").strip()
            if fd.isdigit() and 1 <= int(fd) <= 11:
                face_down_card = int(fd)
            else:
                print(" Must be 1–11.")

        fu = input(" Your face-UP  card (visible, 1-11, or Enter if none): ").strip()
        if fu.isdigit() and 1 <= int(fu) <= 11:
            player_visible.append(int(fu))

        while not opp_visible:
            ov = input(" Opponent's face-up card     (1-11): ").strip()
            if ov.isdigit() and 1 <= int(ov) <= 11:
                opp_visible = [int(ov)]
            else:
                print(" Must be 1–11.")

        _render()

        # ══════════════════════════════════════════════════════════════════════
        # INNER LOOP — event-driven actions within one round
        # ══════════════════════════════════════════════════════════════════════
        while True:
            t_lbl = f" [Target:{current_target}]" if current_target != 21 else ""
            b_lbl = f" [Bet {player_bet}v{opp_bet}]" if (player_bet != 1 or opp_bet != 1) else ""
            print(f"\n ─── Round {round_num}{t_lbl}{b_lbl} [{len(trump_hand)} trumps] ───")
            print("  H  You draw a card         O  Opponent draws a card")
            print("  S  Opponent stays          \033[96mI  Enemy plays a trump\033[0m")
            print(f"  P  Play your trump  ({len(trump_hand)})    D  Resolve round")
            print("  Q  Quit fight               ?  Tools / reference")

            action = input("\n > ").strip().upper()

            # ── ? submenu ──────────────────────────────────────────────────
            if action == "?":
                print("\n  W  Edit trump hand    X  Dead cards")
                print("  T  Trump reference    F  Opponent info")
                print("  G  Round history      V  HP status")
                print("  B  Bust-win analysis  (challenge guide)")
                sub = input(" > ").strip().upper()
                action = {"F": "_OI", "G": "_HI"}.get(sub, sub)

            # ── H: You drew ────────────────────────────────────────────────
            if action == "H":
                c = input(" Card you drew (1-11): ").strip()
                if c.isdigit() and 1 <= int(c) <= 11:
                    player_visible.append(int(c))
                    _render()
                else:
                    print(" Must be 1–11.")

            # ── O: Opponent drew ───────────────────────────────────────────
            elif action == "O":
                c = input(" Card opponent drew (1-11): ").strip()
                if c.isdigit() and 1 <= int(c) <= 11:
                    opp_visible.append(int(c))
                    _condition.banker_took_card = True
                    _render()
                else:
                    print(" Must be 1–11.")

            # ── S: Opponent stopped ────────────────────────────────────────
            elif action == "S":
                opp_behavior = "stay"
                print(" ✓ Opponent is staying.")
                _render()

            # ── I: Enemy trump ─────────────────────────────────────────────
            elif action == "I":
                dead_cards, current_target, player_bet, opp_bet, _msg, \
                player_visible, opp_visible, face_down_card, trump_hand = handle_interrupt(
                    dead_cards, current_target, player_bet, opp_bet,
                    player_visible, opp_visible, face_down_card, intel, trump_hand,
                    condition_state=_condition,
                )
                _condition.banker_items_used_round += 1
                _condition.player_betup_active      = (player_bet > 1)
                _render()

            # ── P: You play a trump ────────────────────────────────────────
            elif action == "P":
                if not trump_hand:
                    print(" No trumps in hand.")
                    continue
                display_trump_hand(trump_hand)
                p = input("\n Which card? (number, Enter to cancel): ").strip()
                if not p:
                    continue
                try:
                    idx = int(p) - 1
                    if not (0 <= idx < len(trump_hand)):
                        print(" Invalid number.")
                        continue
                    played = trump_hand[idx]
                    print(f"\n Playing: {played}")
                    print(f" Effect : {TRUMPS.get(played, {}).get('desc', '?')}")

                    if played in ("Go for 17", "Go for 24", "Go for 27"):
                        current_target = int(played.split()[-1])
                        trump_hand.pop(idx)
                        print(f" ★ Target → {current_target}!")

                    elif played == "One-Up":
                        opp_bet += 1; trump_hand.pop(idx)
                        print(f" ★ Opp bet +1 → {opp_bet}. (Draw 1 trump — add via W)")

                    elif played == "Two-Up":
                        opp_bet += 2; trump_hand.pop(idx)
                        print(f" ★ Opp bet +2 → {opp_bet}. (Draw 1 trump — add via W)")

                    elif played == "Two-Up+":
                        opp_bet += 2; trump_hand.pop(idx)
                        rv = input(" Card returned to deck? (value) ").strip()
                        if rv.isdigit():
                            rv = int(rv)
                            if rv in opp_visible: opp_visible.remove(rv)
                            if rv in dead_cards:  dead_cards.remove(rv)
                        print(f" ★ Opp bet +2 → {opp_bet}. Card returned.")

                    elif played == "Shield":
                        player_bet = max(0, player_bet - 1); trump_hand.pop(idx)
                        print(f" ★ Your bet -1 → {player_bet}.")

                    elif played == "Shield+":
                        player_bet = max(0, player_bet - 2); trump_hand.pop(idx)
                        print(f" ★ Your bet -2 → {player_bet}.")

                    elif played == "Return":
                        rv = input(" Which card are you returning? (value) ").strip()
                        if rv.isdigit() and 1 <= int(rv) <= 11:
                            rv = int(rv)
                            if rv in player_visible:   player_visible.remove(rv)
                            elif rv == face_down_card: face_down_card = None
                            trump_hand.pop(idx)
                            print(f" ★ Returned {rv}.")

                    elif played == "Remove":
                        rv = input(" Opponent card removed? (value) ").strip()
                        if rv.isdigit() and 1 <= int(rv) <= 11:
                            rv = int(rv)
                            if rv in opp_visible: opp_visible.remove(rv)
                            dead_cards = sorted(set(dead_cards + [rv]))
                            trump_hand.pop(idx)
                            print(f" ★ Removed opponent's {rv}.")

                    elif played == "Exchange":
                        gave = input(" Card you gave? (value) ").strip()
                        took = input(" Card you took? (value) ").strip()
                        if gave.isdigit() and took.isdigit():
                            gave, took = int(gave), int(took)
                            if gave in player_visible:    player_visible.remove(gave)
                            elif gave == face_down_card:  face_down_card = took; took = None
                            if took is not None:          player_visible.append(took)
                            if gave not in opp_visible:   opp_visible.append(gave)
                            if took is not None and took in opp_visible: opp_visible.remove(took)
                            trump_hand.pop(idx)
                            print(f" ★ Exchanged: gave {gave}.")

                    elif played == "Love Your Enemy":
                        rv = input(" Card opponent was forced to draw? (value) ").strip()
                        if rv.isdigit() and 1 <= int(rv) <= 11:
                            opp_visible.append(int(rv))
                            trump_hand.pop(idx)
                            print(f" ★ Forced opponent to draw {rv}.")

                    elif played in ("Perfect Draw", "Perfect Draw+", "Ultimate Draw"):
                        rv = input(" Card you drew? (value) ").strip()
                        if rv.isdigit() and 1 <= int(rv) <= 11:
                            player_visible.append(int(rv))
                            if played == "Perfect Draw+":
                                opp_bet += 5
                                print(f" ★ Opp bet +5 → {opp_bet}.")
                            elif played == "Ultimate Draw":
                                print(" (Draw 2 trumps — add via W)")
                            trump_hand.pop(idx)

                    elif played in ("2 Card","3 Card","4 Card","5 Card","6 Card","7 Card"):
                        cv = int(played[0])
                        if input(f" Drew the {cv}? (y/n) ").strip().lower() == "y":
                            player_visible.append(cv)
                        trump_hand.pop(idx)

                    elif played in ("Destroy", "Destroy+", "Destroy++"):
                        trump_hand.pop(idx)
                        print(f" ★ {played} — enemy trump removed.")

                    else:
                        trump_hand.pop(idx)
                        print(f" ★ {played} played. Update state manually if needed.")

                    _condition.player_betup_active = (player_bet > 1)
                    _render()

                except (ValueError, IndexError):
                    print(" Invalid input.")

            # ── D: Resolve round ───────────────────────────────────────────
            elif action == "D":
                hid = input("\n Opponent's hidden card? (value, or Enter for manual entry): ").strip()
                if hid.isdigit() and 1 <= int(hid) <= 11:
                    hidden     = int(hid)
                    your_total = (face_down_card or 0) + sum(player_visible)
                    opp_total  = sum(opp_visible) + hidden
                    print(f" You: {your_total}  Opp: {opp_total}  Target: {current_target}")

                    if your_total > current_target and opp_total > current_target:
                        outcome = "TIE"
                    elif your_total > current_target:
                        outcome = "LOSS"
                    elif opp_total > current_target:
                        outcome = "WIN"
                    elif your_total > opp_total:
                        outcome = "WIN"
                    elif your_total < opp_total:
                        outcome = "LOSS"
                    else:
                        outcome = "TIE"

                    print(f" Outcome: {outcome}")
                    dmg_tracked = player_bet if outcome == "LOSS" else opp_bet
                    bet_in = input(f" Damage multiplier? (Enter = {dmg_tracked}): ").strip()
                    dmg = int(bet_in) if bet_in.isdigit() else dmg_tracked

                    if outcome == "WIN":
                        opp_hp = max(0, opp_hp - dmg)
                        print(f" ✓ Opponent -{dmg} HP → {opp_hp}/{opp_max}")
                        round_history.append({"round": round_num, "result": "WIN",  "damage": dmg})
                    elif outcome == "LOSS":
                        player_hp = max(0, player_hp - dmg)
                        print(f" ✖ You -{dmg} HP → {player_hp}/{player_max}")
                        round_history.append({"round": round_num, "result": "LOSS", "damage": dmg})
                    else:
                        print(" Tie — no damage.")
                        round_history.append({"round": round_num, "result": "TIE",  "damage": 0})
                else:
                    # Interactive fallback
                    player_hp, opp_hp, entry = record_round_result(round_num, player_hp, opp_hp, intel)
                    if entry is None:
                        continue
                    round_history.append(entry)

                display_hp_status(player_hp, player_max, opp_hp, opp_max, intel["name"])
                if opp_hp <= 0:
                    print(f"\n ★★★ {intel['name']} DEFEATED! ({round_num} rounds) ★★★")
                elif player_hp <= 0:
                    print(f"\n ✖✖✖ YOU DIED vs. {intel['name']} ({round_num} rounds) ✖✖✖")

                # End-of-round trump update
                print("\n ── TRUMP UPDATE ──────────────────────────────────────")
                display_trump_hand(trump_hand)
                used = input(" Trumps PLAYED this round (names/nums, or Enter): ").strip()
                if used:
                    trump_hand = apply_trump_usage(trump_hand, used)
                show_trump_addition_list(available_trumps)
                gained = input(" Trumps GAINED this round (number(s) or name, or Enter): ").strip()
                if gained:
                    trump_hand = apply_trump_additions(trump_hand, gained, available_trumps)
                break

            # ── W: Edit trump hand ─────────────────────────────────────────
            elif action == "W":
                trump_hand = edit_trump_hand(trump_hand, available_trumps)

            # ── Reference / info ───────────────────────────────────────────
            elif action == "T":
                display_trumps_reference(); input(" Press Enter to continue...")
            elif action == "_OI":
                display_opponent_info(intel)
            elif action == "_HI":
                display_round_history(round_history)
            elif action == "V":
                display_hp_status(player_hp, player_max, opp_hp, opp_max, intel["name"])

            # ── B: Bust-win challenge analysis ─────────────────────────────
            elif action == "B":
                u_total_b   = (face_down_card or 0) + sum(player_visible)
                o_vis_b     = sum(opp_visible)
                all_known_b = set(
                    ([face_down_card] if face_down_card else [])
                    + player_visible + opp_visible + dead_cards
                )
                remaining_b = [c for c in range(1, 12) if c not in all_known_b]
                opp_hp_now  = intel.get("hp", 1)
                bust_lines  = evaluate_bust_win_challenge(
                    u_total=u_total_b,
                    o_visible_total=o_vis_b,
                    remaining=remaining_b,
                    stay_val=intel.get("stay_val", 17),
                    target=current_target,
                    trump_hand=trump_hand,
                    intel=intel,
                    player_hp=player_hp,
                    player_max=player_max,
                    opp_hp=opp_hp_now,
                    challenges_completed=challenges_completed,
                    banker_ai=_banker_ai,
                    behavior=opp_behavior,
                )
                print()
                for ln in bust_lines:
                    print(ln)
                input(" Press Enter to continue...")
            elif action == "X":
                if dead_cards:
                    print(f" Dead cards: {sorted(dead_cards)}")
                    xi = input(" 'c'=clear, values to add, or Enter: ").strip().lower()
                    if xi == "c":
                        dead_cards = []
                    elif xi:
                        try:
                            dead_cards = sorted(set(dead_cards + [int(x) for x in xi.split() if 1 <= int(x) <= 11]))
                        except ValueError:
                            pass
                else:
                    xi = input(" No dead cards. Add? (values or Enter): ").strip()
                    if xi:
                        try:
                            dead_cards = sorted(set(int(x) for x in xi.split() if 1 <= int(x) <= 11))
                        except ValueError:
                            pass

            # ── Q: Quit ────────────────────────────────────────────────────
            elif action == "Q":
                if input(" Quit fight? (y/n): ").strip().lower() == "y":
                    return player_hp, trump_hand

            else:
                print(" H/O/S/I/P/D  — draw card, stay, trump, resolve")
                print(" W/X/T/F/G/V  — trump hand, dead cards, refs, info")

        if player_hp <= 0 or opp_hp <= 0:
            break

    return player_hp, trump_hand



# ============================================================
# MODE RUNNERS
# ============================================================
def get_opponent_list(mode_key: str):
    if mode_key == "1":
        return OPPONENTS_NORMAL
    if mode_key == "2":
        return OPPONENTS_SURVIVAL
    if mode_key == "3":
        # Survival+ uses dynamic selection — return pool for reference
        return OPPONENTS_SURVIVAL_PLUS
    return []


def select_survival_plus_opponent(fight_num: int, available_trumps: set = None) -> dict:
    """Select the opponent for a given Survival+ fight number (1-10)."""
    if fight_num == 5:
        print(f"\n ★ Fight #{fight_num} is ALWAYS Molded Hoffman (mid-boss)!")
        input(" Press Enter to continue...")
        return BOSS_SURVIVAL_PLUS_MID

    if fight_num == 10:
        print(f"\n ★ Fight #{fight_num} is ALWAYS Undead Hoffman (final boss)!")
        input(" Press Enter to continue...")
        return BOSS_SURVIVAL_PLUS_FINAL

    print(f"\n Who are you facing for fight #{fight_num}?")
    print(" Identify by the sack on their head:\n")

    pool = OPPONENTS_SURVIVAL_PLUS
    harvest_unlocked = available_trumps is not None and "Harvest" in available_trumps
    for i, opp in enumerate(pool):
        label = f" {i + 1}. {opp['name']} — {opp.get('desc', '')}"
        # Flag Mr. Big Head as priority if Harvest not yet unlocked
        if "Big Head" in opp["name"] and not harvest_unlocked:
            label += " \033[96m★ PRIORITY TARGET (unlocks Harvest!)\033[0m"
        print(label)

    if not harvest_unlocked:
        print(f"\n \033[96m★ TIP: If Mr. Big Head appears, prioritize beating him!\033[0m")
        print(f"   Defeating him twice unlocks 'Harvest' (trump draw after every trump you play).")

    while True:
        choice = input(f"\n Select (1-{len(pool)}): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(pool):
                selected = pool[idx]
                if "Big Head" in selected["name"] and not harvest_unlocked:
                    print(f"\n \033[96m★ Mr. Big Head — PRIORITY: Beat him to unlock Harvest!\033[0m")
                    print(f"   Watch for 'Escape' — save Destroy to counter it!")
                return selected
            print(" Invalid selection.")
        except ValueError:
            print(" Enter a number.")


def run_mode(mode_key: str, challenges_completed: set = None, available_trumps: set = None) -> None:
    """Run a full game mode — progress through opponents sequentially."""
    mode = GAME_MODES[mode_key]

    player_hp = int(mode["player_hp"])
    player_max = int(mode["player_hp"])

    if mode_key == "3":
        total_opponents = 10
    elif mode_key == "2":
        total_opponents = len(OPPONENTS_SURVIVAL)
    else:
        total_opponents = len(OPPONENTS_NORMAL)

    # ── NO-DAMAGE TRACKING ──
    # Automatically tracks whether you've taken ANY damage this run.
    # Only relevant for Survival (unlocks Ultimate Draw) — S+ is cosmetic.
    if challenges_completed is None:
        challenges_completed = set()
    no_damage_relevant = (
        mode_key == "2"
        and "no_damage_survival" not in challenges_completed
    )
    no_damage = True  # Flips to False on first damage

    print_header(f"{mode['name']}")
    print(f"\n {mode['rules']}")
    print(f"\n Starting HP: {player_hp}")
    print(f" Opponents: {total_opponents}")
    if no_damage_relevant:
        print(f" \033[92m★ NO-DAMAGE CHALLENGE ACTIVE — tracking automatically.\033[0m")
        print(f"   Take zero damage to unlock Ultimate Draw!")
    input("\n Press Enter to begin...")

    # ── Run-wide trump hand — persists across all fights ─────────────────────
    run_trump_hand: list = []
    print("\n Enter your starting trump hand for this run (persists across all fights):")
    run_trump_hand = edit_trump_hand([], available_trumps)

    for idx in range(total_opponents):
        fight_num = idx + 1

        if player_hp <= 0:
            break

        print_header(f"{mode['name']} — OPPONENT {fight_num}/{total_opponents}")
        print(f" Your HP: {player_hp}/{player_max}")

        if mode_key == "3":
            # Survival+ — dynamic selection
            opp = select_survival_plus_opponent(fight_num, available_trumps)
        else:
            # Normal / Survival — fixed order
            opponents = get_opponent_list(mode_key)
            opp = opponents[idx]

        print(f" Next: {opp['name']} ({opp.get('ai','?')}) — {opp['hp']} HP")

        if idx > 0:
            ready = input("\n Ready? (Enter = yes, q = quit): ").strip().lower()
            if ready == "q":
                print(" Returning to menu.")
                return

        hp_before_fight = player_hp
        player_hp, run_trump_hand = fight_opponent(
            opp, player_hp, player_max, challenges_completed, available_trumps,
            mode_key=mode_key, fight_num=fight_num, trump_hand=run_trump_hand
        )

        if player_hp <= 0:
            print_header("GAME OVER")
            print(f" Defeated by {opp['name']}.")
            print(f" Opponents beaten: {idx}/{total_opponents}")
            return

        # ── NO-DAMAGE CHECK ──
        damage_this_fight = hp_before_fight - player_hp
        if no_damage_relevant and no_damage and damage_this_fight > 0:
            no_damage = False
            print(f"\n \033[91m✖ NO-DAMAGE CHALLENGE FAILED — took {damage_this_fight} damage vs {opp['name']}.\033[0m")
            remaining_fights = total_opponents - fight_num
            if remaining_fights > 0:
                print(f"   {remaining_fights} fights remaining. Ultimate Draw requires zero damage.")
                print(f"   \033[96mRestart run for a fresh no-damage attempt? (y/n)\033[0m")
                if input("   > ").strip().lower() == "y":
                    print(" Restarting run...")
                    return
                print("   Continuing run (no-damage challenge voided).")

        # ── RUN RESTART SUGGESTION ──
        # If HP is critically low in the first half, the run is likely doomed.
        remaining_fights = total_opponents - fight_num
        if remaining_fights > 0 and fight_num <= 4:
            # Heuristic: need roughly 1 HP per remaining fight minimum
            # For S+: 10 fights, if you have 3 HP after fight 4 with 6 fights left → bad
            # For S: 5 fights, if you have 1 HP after fight 2 with 3 left → bad
            hp_per_fight_needed = 1.0  # Minimum theoretical
            projected_min = remaining_fights * hp_per_fight_needed
            survival_ratio = player_hp / remaining_fights if remaining_fights > 0 else 1.0

            if survival_ratio < 0.5:
                print(f"\n \033[91m⚠ WARNING: {player_hp} HP with {remaining_fights} fights remaining.\033[0m")
                print(f" \033[91m  Win probability is very low (~{int(survival_ratio * 100)}% survival rate per fight needed).\033[0m")
                print(f" \033[91m  RECOMMENDATION: Consider restarting the run for a better attempt.\033[0m")
                restart = input("\n Restart run? (y/n): ").strip().lower()
                if restart == "y":
                    print(" Restarting run...")
                    return
            elif survival_ratio < 0.8 and fight_num >= 2:
                print(f"\n \033[96m⚠ HP check: {player_hp} HP, {remaining_fights} fights left — playing tight.\033[0m")

    if player_hp > 0:
        print_header(f"★ {mode['name']} COMPLETE! ★")
        print(f" All {total_opponents} opponents defeated!")
        print(f" Remaining HP: {player_hp}/{player_max}")

        if no_damage_relevant and no_damage:
            print(f"\n \033[92m★★★ NO-DAMAGE RUN COMPLETE! ★★★\033[0m")
            print(f" \033[92m Unlocked: Ultimate Draw!\033[0m")

        if mode_key == "2":
            print(" UNLOCKED: Survival+ mode!")
        elif mode_key == "3":
            print(" UNLOCKED: 'Perfect Draw' trump card!")
            print(" TROPHY: Survival+ complete!")


def run_free_play(challenges_completed: set = None, available_trumps: set = None) -> None:
    """Pick any opponent for practice."""
    print_header("FREE PLAY — SELECT OPPONENT")

    all_opps = []
    sections = [
        ("Normal", OPPONENTS_NORMAL),
        ("Survival", OPPONENTS_SURVIVAL),
        ("Survival+ (Random Pool)", OPPONENTS_SURVIVAL_PLUS),
        ("Survival+ (Bosses)", [BOSS_SURVIVAL_PLUS_MID, BOSS_SURVIVAL_PLUS_FINAL]),
    ]

    for section_name, opp_list in sections:
        print(f"\n --- {section_name} ---")
        for opp in opp_list:
            all_opps.append(opp)
            print(f" {len(all_opps):>2}. {opp['name']} — {opp.get('ai','?')} ({opp['hp']} HP)")

    choice = input(f"\n Select opponent (1-{len(all_opps)}): ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(all_opps):
            opp = all_opps[idx]
            print("\n Set YOUR starting HP (default 10):")
            hp_input = input(" > ").strip()
            player_hp = int(hp_input) if hp_input else 10
            player_max = player_hp
            fight_opponent(opp, player_hp, player_max, challenges_completed, available_trumps,
                          mode_key="3", fight_num=0, trump_hand=[])
        else:
            print(" Invalid selection.")
    except ValueError:
        print(" Invalid input.")



# ============================================================
# MAIN MENU
# ============================================================
def main() -> None:
    challenges_completed, available_trumps = setup_challenge_progress()

    while True:
        print_header("RESIDENT EVIL 7: 21 — CARD GAME SOLVER")
        print("\n SELECT MODE:\n")
        print(" 1. Normal 21 (vs. Lucas — tutorial) ⚠ limited accuracy")
        print(" 2. Survival 21 (5-opponent gauntlet)")
        print(" 3. Survival+ 21 (10-opponent hard gauntlet)")
        print(" 4. Free Play (pick any opponent)")
        print()
        print(" R. Trump Card Reference")
        print(f" U. Update challenge progress ({len(challenges_completed)} completed)")
        print(" Q. Quit")

        choice = input("\n Select: ").strip().upper()

        if choice == "Q":
            print("\n Good luck, Clancy. Don't let Lucas win.\n")
            break
        elif choice == "R":
            display_trumps_reference()
            input(" Press Enter to continue...")
        elif choice == "U":
            challenges_completed, available_trumps = setup_challenge_progress(force_prompt=True)
            input(" Press Enter to continue...")
        elif choice in ("1", "2", "3"):
            run_mode(choice, challenges_completed, available_trumps)
            input("\n Press Enter to return to menu...")
        elif choice == "4":
            run_free_play(challenges_completed, available_trumps)
            input("\n Press Enter to return to menu...")
        else:
            print(" Invalid selection.")


if __name__ == "__main__":
    main()
