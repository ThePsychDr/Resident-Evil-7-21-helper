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
        "trumps": ["Happiness", "Desire", "Mind Shift"],
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
                "trumps": ["Happiness", "Return", "Desire", "Mind Shift"],
                "tip": (
                    "2-CUT VARIANT (less dangerous):\n"
                    "Trumps: Happiness, Return, Desire, Mind Shift\n"
                    "'Desire' raises YOUR bet by half your trump count.\n"
                    "'Mind Shift' — you lose half trumps unless you play 2 this round.\n"
                    "STRATEGY: Don't hoard trumps. Play 2 per round to block Mind Shift."
                ),
            },
            "3 cuts": {
                "trumps": ["One-Up", "Two-Up", "Desire", "Happiness"],
                "tip": (
                    "3-CUT VARIANT:\n"
                    "Trumps: One-Up, Two-Up, Desire, Happiness\n"
                    "Has bet-raising cards (One-Up, Two-Up) — can stack damage.\n"
                    "'Desire' raises YOUR bet by half your trump count.\n"
                    "STRATEGY: Don't hoard trumps. Destroy his bet-ups if stacking."
                ),
            },
        },
        # Fallback if no variant selected (union of all)
        "trumps": ["One-Up", "Two-Up", "Happiness", "Return", "Desire", "Mind Shift"],
        "tip": (
            "Variants based on cut count (select variant at fight start):\n"
            " 2 cuts: Happiness, Return, Desire, Mind Shift\n"
            " 3 cuts: One-Up, Two-Up, Desire, Happiness\n"
            "STRATEGY: Don't hoard trumps — Desire punishes it."
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
                "trumps": ["Happiness", "Return", "Desire", "Mind Shift"],
                "tip": (
                    "2-HAND VARIANT:\n"
                    "Trumps: Happiness, Return, Desire, Mind Shift\n"
                    "Same loadout as 2-cut Tally Mark.\n"
                    "'Mind Shift' — play 2 trumps to remove it.\n"
                    "STRATEGY: Spend trumps, don't hoard."
                ),
            },
            "4 hands": {
                "trumps": ["Happiness", "Desire+", "Mind Shift+"],
                "tip": (
                    "4-HAND VARIANT (DANGEROUS):\n"
                    "Trumps: Happiness, Desire+, Mind Shift+\n"
                    "'Desire+' raises YOUR bet by your FULL trump count!\n"
                    "'Mind Shift+' — you lose ALL trumps unless you play 3 this round!\n"
                    "STRATEGY: Spend trumps AGGRESSIVELY. Never hold more than 3-4.\n"
                    "This is one of the most punishing non-boss opponents."
                ),
            },
        },
        "trumps": ["Desire", "Desire+", "Mind Shift", "Mind Shift+", "Happiness", "Return"],
        "tip": (
            "Variants based on handprint count (select variant at fight start):\n"
            " 2 hands: Happiness, Return, Desire, Mind Shift\n"
            " 4 hands: Happiness, Desire+, Mind Shift+ (DANGEROUS)\n"
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
    "trumps": ["Ultimate Draw", "Two-Up+", "Perfect Draw+", "Dead Silence", "Oblivion", "Remove"],
    "stay_val": 18,
    "hp": 10,
    "trump_behavior": {
        "Dead Silence": {"freq": "very_high", "when": "early", "repeats": True,
                         "note": "Uses most often. Will replay after Destroy. Priority Destroy target."},
        "Perfect Draw+": {"freq": "high", "when": "any", "repeats": True,
                          "note": "Almost always gets 21. Exchange can bust him if his drawn card > yours."},
        "Ultimate Draw": {"freq": "high", "when": "any", "repeats": True,
                          "note": "Gets best card + 2 trumps. Very dangerous."},
        "Oblivion": {"freq": "medium", "when": "losing", "repeats": True,
                     "note": "Cancels the round when he's losing. Cannot be countered. Just restart."},
        "Two-Up+": {"freq": "medium", "when": "winning", "repeats": True,
                    "note": "Returns your last card AND raises bet. Use when he thinks he'll win."},
        "Remove": {"freq": "medium", "when": "any", "repeats": True,
                   "note": "Takes your last face-up card. Common disruption."},
    },
    "tip": (
        "!! FINAL BOSS — MOST DANGEROUS OPPONENT !!\n"
        "'Ultimate Draw' and 'Perfect Draw+' — almost always gets perfect cards.\n"
        "'Dead Silence' prevents you from drawing ANY cards (even via trumps).\n"
        "  He uses Dead Silence REPEATEDLY — save multiple Destroys!\n"
        "'Oblivion' cancels the entire round — wastes your good hands. CANNOT be countered.\n"
        "'Two-Up+' returns your last card AND raises bet by 2.\n"
        "He also uses 'Remove' to take your face-up cards!\n"
        "STRATEGY:\n"
        " 1) Save 'Destroy' for Dead Silence (highest priority). He WILL replay it.\n"
        " 2) If Dead Silence is up and you can't Destroy: use Exchange to try busting him.\n"
        " 3) Stack shields — he hits HARD.\n"
        " 4) Be patient — Oblivion wastes rounds but doesn't hurt you.\n"
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
    "Remove": {"cat": "Cards", "desc": "Return opponent's last face-up card to the deck.", "weight": 45, "etype": "Draw Forcer"},
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
    "Go for 17": {"cat": "Target", "desc": "Closest to 17 wins while on table. Replaces other 'Go For' cards.", "weight": 30, "etype": "Target Modifier"},
    "Go for 24": {"cat": "Target", "desc": "Closest to 24 wins while on table. Replaces other 'Go For' cards.", "weight": 35, "etype": "Target Modifier"},
    "Go for 27": {"cat": "Target", "desc": "Closest to 27 wins while on table. Replaces other 'Go For' cards.", "weight": 40, "etype": "Target Modifier"},

    # ── Trump Draw ──
    "Harvest": {"cat": "Switch", "desc": "Draw a trump card after every trump you use while on table.", "weight": 50, "etype": "Special"},
    "Love Your Enemy": {"cat": "Cards", "desc": "Opponent draws the best possible card for THEM from the deck.", "weight": 60, "etype": "Draw Forcer"},

    # ── Enemy-exclusive trump cards (weight 0 = not player-obtainable) ──
    "Happiness": {"cat": "Switch", "desc": "Both players draw 1 trump card. (Enemy-used)", "weight": 0, "etype": "Attack"},
    "Desire": {"cat": "Attack", "desc": "YOUR bet increased by half YOUR held trump count while on table. (Enemy-used)", "weight": 0, "etype": "Attack"},
    "Desire+": {"cat": "Attack", "desc": "YOUR bet increased by YOUR full held trump count while on table. (Enemy-used)", "weight": 0, "etype": "Attack"},
    "Mind Shift": {
        "cat": "Attack",
        "desc": "You lose half your trumps at end of round. Removed if you play 2 trumps in a round. (Enemy-used)",
        "weight": 0, "etype": "Attack",
    },
    "Mind Shift+": {
        "cat": "Attack",
        "desc": "You lose ALL trumps at end of round. Removed if you play 3 trumps in a round. (Enemy-used)",
        "weight": 0, "etype": "Attack",
    },
    "Shield Assault": {
        "cat": "Attack",
        "desc": "Enemy removes 3 of HIS Shields. YOUR bet +3 while on table. (Enemy-used)",
        "weight": 0, "etype": "Attack",
    },
    "Shield Assault+": {
        "cat": "Attack",
        "desc": "Enemy removes 2 of HIS Shields. YOUR bet +5 while on table. (Enemy-used)",
        "weight": 0, "etype": "Attack",
    },
    "Curse": {"cat": "Attack", "desc": "Discard one of your trumps at random. You draw the highest card in deck. (Enemy-used)", "weight": 0, "etype": "Attack"},
    "Black Magic": {
        "cat": "Attack",
        "desc": "Remove half your trumps. Your bet +10. Enemy draws best possible card. (Enemy-used)",
        "weight": 0, "etype": "Attack",
    },
    "Conjure": {"cat": "Attack", "desc": "Enemy draws 3 trumps. Enemy's bet +1 while on table. (Enemy-used)", "weight": 0, "etype": "Attack"},
    "Dead Silence": {"cat": "Attack", "desc": "You cannot draw cards (even via trump effects) while on table. (Enemy-used)", "weight": 0, "etype": "Attack"},
    "Twenty-One Up": {"cat": "Attack", "desc": "Enemy must hit exactly 21. YOUR bet +21 while on table. (Boss-only)", "weight": 0, "etype": "Attack"},

    # ── Special ──
    "Escape": {"cat": "Special", "desc": "You don't take damage if you lose while on table. Match resets if used.", "weight": 0, "etype": "Special"},
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

CHALLENGE_SOURCES = [
    ("RE Wiki - 21 rewards list", "https://residentevil.fandom.com/wiki/21"),
    ("RE Wiki - basic rules", "https://residentevil.fandom.com/wiki/Card_Game_%2221%22_-_Basic_Rules"),
    ("RE Wiki - trump cards", "https://residentevil.fandom.com/wiki/Trump_cards"),
    ("TrueAchievements - Survival+ strategy discussion", "https://www.trueachievements.com/a229688/you-gotta-know-when-to-hold-em-achievement"),
    ("EntranceJew odds helper", "https://entrancejew.itch.io/re7-21-tool"),
]

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
# PLAYER TRUMP HAND TRACKING
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
    # Cards that require unlocking — if available_trumps is set, filter these
    UNLOCKABLE = {"Perfect Draw+", "Ultimate Draw", "Trump Switch+", "Shield+",
                  "Two-Up+", "Go for 24", "Go for 27", "Harvest"}

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
                print(f"  {i:>2}. {name}")
            if available_trumps is not None:
                locked = [c for c in UNLOCKABLE if c not in available_trumps]
                if locked:
                    print(f"\n  🔒 Locked ({len(locked)}): {', '.join(sorted(locked))}")
            print(f"\n Enter numbers to add (e.g., '1 3 7'), or card names:")
            raw = input(" > ").strip()
            if raw:
                # Try parsing as numbers first
                try:
                    indices = [int(x) for x in raw.split()]
                    for idx in indices:
                        if 1 <= idx <= len(allowed):
                            trump_hand.append(allowed[idx - 1])
                            print(f"  + {allowed[idx - 1]}")
                except ValueError:
                    # Try as card names (partial match)
                    for part in raw.split(","):
                        part = part.strip()
                        matches = [n for n in allowed if part.lower() in n.lower()]
                        if len(matches) == 1:
                            trump_hand.append(matches[0])
                            print(f"  + {matches[0]}")
                        elif len(matches) > 1:
                            print(f"  Multiple matches for '{part}': {matches}")
                        else:
                            print(f"  No match for '{part}'")
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
    name_short = opp_name[:18]
    print()
    print(" ┌─────────────────────────────────────────────────────┐")
    print(f" │ {'HP STATUS':^53s} │")
    print(" ├─────────────────────────────────────────────────────┤")
    print(f" │ YOU: {hp_bar(player_hp, player_max, 15):<40s}│")
    print(f" │ {name_short:<12s} {hp_bar(opp_hp, opp_max, 15):<40s}│")
    print(" └─────────────────────────────────────────────────────┘")


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
        print(f" │ \033[93mSpecial Trumps: {', '.join(special_trumps)}\033[0m")
    elif not std_trumps:
        print(f" │ Trumps: (none observed)")

    print(f" │ Stays at: {intel.get('stay_val','?')}+")
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
        rnd = entry["round"]
        result = entry["result"]
        dmg = entry["damage"]
        who = entry["damage_to"]
        if result == "VOID":
            line = f" │ R{rnd}: VOID (Escape/Oblivion) — no damage"
        elif result == "TIE":
            line = f" │ R{rnd}: TIE — no damage"
        else:
            winner = "YOU WON" if result == "WIN" else "YOU LOST"
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


def opponent_total_distribution(o_visible_total: int, remaining, stay_val: int, target: int, behavior: str = "auto"):
    """
    Return probability distribution of opponent final totals.

    behavior options:
      - stay: opponent does not draw (confirmed)
      - hit_once: opponent draws one card then stops
      - auto / hit_to_threshold: opponent hits until reaching stay_val or bust,
        BUT blends in uncertainty (30% chance of drawing one more past threshold)
        because we're guessing — the real AI may be more aggressive.
    """
    behavior = behavior.lower().strip()
    deck = tuple(sorted(set(remaining)))

    if behavior == "stay":
        # Opponent stopped drawing. They have a hidden card we can't see.
        # Their total = visible total + one unknown card from the remaining deck.
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
    # How far below target the opponent is — more room = more likely they draw again
    gap_to_target = max(0, target - o_visible_total)
    # Uncertainty: 30% base chance of drawing past threshold, higher if far from target
    overshoot_chance = min(0.50, 0.15 + (gap_to_target / target) * 0.35)

    def _merge(dest: dict, src: dict, weight: float) -> None:
        for total, prob in src.items():
            dest[total] = dest.get(total, 0.0) + (prob * weight)

    def _dfs(total: int, deck_state: tuple):
        key = (total, deck_state)
        if key in memo:
            return memo[key]

        if total > target:
            memo[key] = {total: 1.0}
            return memo[key]

        if behavior in ("auto", "hit_to_threshold"):
            if total >= stay_val or not deck_state:
                if total >= stay_val and deck_state and total < target:
                    # Blend: opponent MIGHT draw one more even past threshold
                    dist = {}
                    # Chance they stay
                    _merge(dist, {total: 1.0}, 1.0 - overshoot_chance)
                    # Chance they gamble and draw one more
                    n = len(deck_state)
                    for idx, card in enumerate(deck_state):
                        next_total = total + card
                        _merge(dist, {next_total: 1.0}, overshoot_chance / n)
                    memo[key] = dist
                    return dist
                memo[key] = {total: 1.0}
                return memo[key]

        if not deck_state:
            memo[key] = {total: 1.0}
            return memo[key]

        dist = {}
        n = len(deck_state)
        for idx, card in enumerate(deck_state):
            next_total = total + card
            next_deck = deck_state[:idx] + deck_state[idx + 1 :]
            sub = _dfs(next_total, next_deck)
            _merge(dist, sub, 1.0 / n)

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
):
    """Compute expected outcome probs for staying now vs. hitting now."""
    stay_opp_dist = opponent_total_distribution(
        o_visible_total, remaining, stay_val, target, behavior=opp_behavior
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
            o_visible_total, next_remaining, stay_val, target, behavior=opp_behavior
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


def evaluate_bust_inline(u_total: int, o_visible_total: int, remaining, stay_val: int, target: int, behavior: str = "auto"):
    """
    Lightweight bust-to-win evaluation for inline strategy advice.
    Returns best bust draw card and its win probability, or None if no bust cards.
    Uses the same opponent distribution model as the main solver.
    """
    bust_cards = [c for c in remaining if u_total + c > target]
    if not bust_cards:
        return None

    best_card = None
    best_win = 0.0

    for draw_card in bust_cards:
        bust_total = u_total + draw_card
        deck_after = [c for c in remaining if c != draw_card]

        # Model opponent's final total distribution
        opp_dist = opponent_total_distribution(o_visible_total, deck_after, stay_val, target, behavior)

        # Use bust_outcome logic: both bust → closest to target wins
        wins = 0.0
        for opp_total, prob in opp_dist.items():
            result = bust_outcome(bust_total, opp_total, target)
            if result == "WIN":
                wins += prob

        if wins > best_win:
            best_win = wins
            best_card = draw_card

    return {"best_card": best_card, "bust_total": u_total + best_card if best_card else 0, "win_pct": best_win}


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
):
    """Generate strategic advice factoring in HP state + opponent trumps.
    trump_hand: player's current held trumps — used to gate Love Your Enemy / bust suggestions."""
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

    # ── HP-aware urgency ──
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

    # ── Core draw/stay decision ──
    estimated_opp = estimate_opponent_total(o_visible_total, stay_val)
    behavior_key = (opp_behavior or "auto").strip().lower()

    behavior_label = {
        "stay": "Opponent stopped drawing (hidden card modeled across remaining deck)",
        "auto": f"Opponent AI draws until {stay_val}+",
        "hit_to_threshold": f"Opponent AI draws until {stay_val}+",
    }.get(behavior_key, f"Opponent AI draws until {stay_val}+")

    # Rough estimate for potential damage if you lose (for messaging only)
    if u_total <= target:
        potential_loss_dmg = max(1, estimated_opp - u_total)
    else:
        # bust-ish estimate: how far over + opponent closeness-ish
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
        u_total, o_visible_total, remaining, stay_val, target, behavior_key
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
                new_opp_total, after_remaining, stay_val, target, behavior="auto"
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

    # Bust-to-win analysis — gated by multiple conditions
    bust_result = None
    if challenges_completed is None:
        challenges_completed = set()
    if available_trumps is None:
        available_trumps = set()
    bust_challenge_done = "bust_win" in challenges_completed
    bust_cards = [c for c in remaining if u_total + c > target]

    # Gate bust suggestion: only show when it makes sense
    # - Challenge not yet completed
    # - Bust cards exist and opponent hasn't stayed
    # - Player HP > 2 (too risky otherwise — you WILL take damage if you bust-lose)
    # - Stay win% isn't already dominant (>65% means just play normally)
    show_bust = (
        bust_cards
        and behavior_key != "stay"
        and not bust_challenge_done
        and player_hp > 2
        and stay_probs["win"] < 0.65  # Don't throw away a comfortable win
    )

    if show_bust:
        bust_result = evaluate_bust_inline(u_total, o_visible_total, remaining, stay_val, target, behavior_key)
        if bust_result and bust_result["win_pct"] >= 0.15:  # Only show if decent odds
            advice_lines.append(
                f"If you BUST ON PURPOSE -> "
                f"Best card: {bust_result['best_card']} (total {bust_result['bust_total']}) → "
                f"Win {bust_result['win_pct'] * 100:.1f}%."
                f" [Completes bust-win challenge!]"
            )
        elif bust_result and bust_result["win_pct"] < 0.15:
            bust_result = None  # Too low — don't include in options

    # Unlocked trump card reminders
    if u_total < estimated_opp and u_total < target:
        if "Perfect Draw+" in available_trumps:
            advice_lines.append("UNLOCKED: You have Perfect Draw+ — guaranteed best card from the deck.")
        if "Ultimate Draw" in available_trumps:
            advice_lines.append("UNLOCKED: You have Ultimate Draw — draws the best possible card.")

    # ── Action recommendation ──
    # Find the best option among STAY, HIT, FORCE DRAW, and INTENTIONAL BUST
    options = {
        "STAY": stay_probs["win"],
        "HIT": hit_probs["win"],
    }
    if force_probs is not None:
        options["FORCE A DRAW (Love Your Enemy)"] = force_probs["win"]
    if bust_result and bust_result["win_pct"] >= 0.15:
        options["INTENTIONAL BUST ★ challenge"] = bust_result["win_pct"]

    best_option = max(options, key=options.get)
    best_win = options[best_option]
    second_best_win = max(v for k, v in options.items() if k != best_option)
    win_edge = best_win - second_best_win

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

    # If you're already at/above their likely stay value and beating their likely total, stay
    if u_total >= stay_val and u_total >= estimated_opp:
        advice_lines.append(f"ACTION: STAY — your {u_total} likely meets/beats his ~{estimated_opp}.")
        return priority_warnings, advice_lines

    # Otherwise decision based on odds + HP risk
    if safe_pct >= 60:
        advice_lines.append(f"ACTION: HIT — {safe_pct:.0f}% safe. Good odds.")
    elif safe_pct >= 40:
        if player_hp <= 3:
            advice_lines.append(
                f"ACTION: STAY (LOW HP) — {safe_pct:.0f}% is too risky at {player_hp} HP.\n"
                f"Potential loss damage estimate: ~{potential_loss_dmg}. Consider a shield/trump."
            )
        elif u_total < estimated_opp:
            advice_lines.append(
                f"ACTION: RISKY HIT — {safe_pct:.0f}% safe, but {u_total} likely loses to ~{estimated_opp}.\n"
                "Consider using a trump (Perfect Draw / Exchange / Love Your Enemy) instead."
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

    # Bust challenge nudge (when not yet completed and bust has decent odds)
    if bust_result and not bust_challenge_done and bust_result["win_pct"] >= 0.15:
        if "BUST" not in advice_lines[-1]:
            advice_lines.append(
                f"💡 BUST CHALLENGE: Drawing {bust_result['best_card']} (→{bust_result['bust_total']}) "
                f"has {bust_result['win_pct'] * 100:.0f}% win chance. "
                f"Completing this unlocks Starting Trump +1!"
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
def analyze_round(intel: dict, player_hp: int, player_max: int, opp_hp: int, opp_max: int, target: int = 21, dead_cards: list = None, challenges_completed: set = None, available_trumps: set = None, trump_hand: list = None, fight_num: int = 0, mode_key: str = "3", face_down_card: int = None) -> tuple:
    """Run the solver for one round of 21 (read-only, no HP changes).
    Returns (updated_dead_cards, face_down_card) for persistence."""
    if dead_cards is None:
        dead_cards = []
    display_hp_status(player_hp, player_max, opp_hp, opp_max, intel["name"])

    print(f"\n Current target: {target}")
    if target != 21:
        print(f" ★ 'Go for {target}' is ACTIVE!")

    # Default to normal AI behavior; override only if needed
    opp_behavior = "auto"

    try:
        # Face-down card memory
        if face_down_card is not None:
            print(f"\n Your face-down card: {face_down_card} (remembered)")
            print(f" Enter your OTHER visible card(s) (space-separated):")
            u_input = input(" > ").strip()
            if not u_input:
                u_hand = [face_down_card]
            else:
                u_hand = [face_down_card] + list(map(int, u_input.split()))
        else:
            print(f"\n Enter YOUR card values (space-separated, e.g., '10 6'):")
            print(f" (First card = your face-down card — will be remembered)")
            u_input = input(" > ").strip()
            if not u_input:
                print(" No cards entered.")
                return dead_cards, face_down_card
            u_hand = list(map(int, u_input.split()))
            if u_hand:
                face_down_card = u_hand[0]  # Remember face-down card
        for c in u_hand:
            if c < 1 or c > 11:
                print(f" ERROR: Card {c} invalid (1–11).")
                return dead_cards, face_down_card

        print(" Enter OPPONENT'S visible card(s) (space-separated):")
        o_input = input(" > ").strip()
        if not o_input:
            print(" No opponent cards entered.")
            return dead_cards, face_down_card
        o_vis = list(map(int, o_input.split()))
        for c in o_vis:
            if c < 1 or c > 11:
                print(f" ERROR: Card {c} invalid (1–11).")
                return dead_cards, face_down_card

        if dead_cards:
            print(f" Remembered dead cards: {sorted(dead_cards)}")
            print(" Enter ADDITIONAL dead/removed cards (or Enter to keep as-is):")
        else:
            print(" Enter DEAD/REMOVED cards (or Enter for none):")
        d_input = input(" > ").strip()
        new_dead = list(map(int, d_input.split())) if d_input else []
        for c in new_dead:
            if c < 1 or c > 11:
                print(f" ERROR: Card {c} invalid (1–11).")
                return dead_cards, face_down_card
        dead = sorted(set(dead_cards + new_dead))
        for c in dead:
            if c < 1 or c > 11:
                print(f" ERROR: Card {c} invalid (1–11).")
                return dead_cards, face_down_card

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
        print("\n What did the opponent do? (Enter = nothing yet / still playing)")
        print("  2. Opponent stayed (done drawing, hidden card still unknown)")
        print("  3. I forced a draw (Love Your Enemy / similar)")
        beh_input = input(" > ").strip()
        if beh_input == "2":
            opp_behavior = "stay"
            # They stopped drawing but hidden card is unknown
            print(f" → Opponent stopped drawing. Visible total: {o_total}")
            print(f"   Hidden card is one of: {sorted(remaining)}")
            print(f"   Possible totals: {sorted(o_total + c for c in remaining)}")
        elif beh_input == "3":
            forced_raw = input(" What card did they draw? ").strip()
            if forced_raw:
                forced_card = int(forced_raw)
                if 1 <= forced_card <= 11:
                    o_total += forced_card
                    o_vis.append(forced_card)
                    if forced_card in remaining:
                        remaining.remove(forced_card)
                    if forced_card not in accounted:
                        accounted = sorted(set(accounted + [forced_card]))
                    print(f" → Opponent now at {o_total} (drew {forced_card})")
                else:
                    print(" Invalid card, ignoring.")
            opp_behavior = "auto"  # After forced draw, they continue with normal AI
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

        # Compute stay win% to share with both advice and trump recommendation
        _stay_val = int(intel.get("stay_val", 17))
        if target != 21:
            _stay_val += (target - 21)
            _stay_val = max(1, _stay_val)
        _stay_win_pct = None
        if u_total <= target and remaining:
            try:
                sp, _ = evaluate_stay_hit_outcomes(
                    u_total, o_total, remaining, _stay_val, target, opp_behavior
                )
                _stay_win_pct = sp.get("win", 0.5)
            except Exception:
                _stay_win_pct = 0.5

        warnings, advice = generate_advice(
            u_total, o_total, intel, remaining, target, safe_pct, perfect_draws,
            player_hp, player_max, opp_hp, opp_max, opp_behavior,
            challenges_completed, available_trumps, trump_hand
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

        return dead, face_down_card

    except ValueError:
        print(" ERROR: Enter valid numbers only.")
        return dead_cards, face_down_card


# ============================================================
# FIGHT LOOP — Multiple rounds vs. one opponent until death
# ============================================================
def handle_interrupt(dead_cards: list, current_target: int, player_bet: int = 1, opp_bet: int = 1) -> tuple:
    """
    Interrupt handler: enemy played a trump card mid-round.
    Lets user declare what happened so we can update game state.
    Returns updated (dead_cards, current_target, player_bet, opp_bet, interrupt_msg).
    """
    print("\n ┌─ ENEMY TRUMP INTERRUPT ──────────────────────────┐")
    print(" │ What did the opponent just do?                   │")
    print(" │                                                  │")
    print(" │  1. Drew/added a card (to their hand)            │")
    print(" │  2. Removed one of YOUR cards (Two-Up+, etc.)    │")
    print(" │  3. Raised YOUR bet (Desire, Shield Assault)     │")
    print(" │  4. Swapped/exchanged cards                      │")
    print(" │  5. Changed target (Go for 17, etc.)             │")
    print(" │  6. Used Destroy on YOUR trump                   │")
    print(" │  7. Played Dead Silence (you can't draw)         │")
    print(" │  8. Played Oblivion (round cancelled)            │")
    print(" │  9. Used Curse (discard trump + forced draw)     │")
    print(" │ 10. Lowered THEIR bet (Shield on their side)     │")
    print(" │ 11. Other / multiple effects                     │")
    print(" │  0. Cancel                                       │")
    print(" └──────────────────────────────────────────────────┘")

    choice = input("\n > ").strip()
    msg = ""

    if choice == "1":
        print(" What card value did opponent draw/add?")
        v = input(" > ").strip()
        if v:
            try:
                val = int(v)
                if 1 <= val <= 11 and val not in dead_cards:
                    dead_cards = sorted(set(dead_cards + [val]))
                    msg = f"Opponent drew {val}. Removed from available deck."
                else:
                    msg = f"Card {v} already accounted for or invalid."
            except ValueError:
                msg = "Invalid input."

    elif choice == "2":
        print(" What card value was removed from YOUR hand?")
        v = input(" > ").strip()
        if v:
            try:
                val = int(v)
                if 1 <= val <= 11:
                    # Card goes back to deck (available pool)
                    if val in dead_cards:
                        dead_cards.remove(val)
                    msg = f"Your card {val} returned to deck pool. Re-analyze to update odds."
            except ValueError:
                msg = "Invalid input."

    elif choice == "3":
        print(" Which enemy card raised YOUR bet?")
        print("  1. Desire (+ half your trump count)")
        print("  2. Desire+ (+ your full trump count)")
        print("  3. Shield Assault (+3)")
        print("  4. Shield Assault+ (+5)")
        print("  5. One-Up (+1 to your bet)")
        print("  6. Other (enter amount)")
        sub = input(" > ").strip()
        if sub == "1":
            print(" How many trumps do you hold?")
            tc = input(" > ").strip()
            try:
                amt = max(1, int(tc) // 2)
                player_bet += amt
                msg = f"Desire: your bet +{amt} → now {player_bet}"
            except ValueError:
                msg = "Invalid."
        elif sub == "2":
            print(" How many trumps do you hold?")
            tc = input(" > ").strip()
            try:
                amt = int(tc)
                player_bet += amt
                msg = f"Desire+: your bet +{amt} → now {player_bet}"
            except ValueError:
                msg = "Invalid."
        elif sub == "3":
            player_bet += 3
            msg = f"Shield Assault: your bet +3 → now {player_bet}"
        elif sub == "4":
            player_bet += 5
            msg = f"Shield Assault+: your bet +5 → now {player_bet}"
        elif sub == "5":
            player_bet += 1
            msg = f"Enemy One-Up: your bet +1 → now {player_bet}"
        elif sub == "6":
            print(" How much did YOUR bet increase by?")
            v = input(" > ").strip()
            try:
                player_bet += int(v)
                msg = f"Your bet +{v} → now {player_bet}"
            except ValueError:
                msg = "Invalid."

    elif choice == "4":
        print(" What card did YOU lose? (value)")
        gave = input(" > ").strip()
        print(" What card did YOU gain? (value)")
        got = input(" > ").strip()
        msg = f"Swapped: lost {gave}, gained {got}. Re-analyze to recalculate."

    elif choice == "5":
        print(" New target value? (17 / 21 / 24 / 27)")
        t = input(" > ").strip()
        if t in ("17", "21", "24", "27"):
            current_target = int(t)
            msg = f"Target changed to {current_target} by opponent!"
        else:
            msg = "Invalid target."

    elif choice == "6":
        msg = "Enemy destroyed your trump. Use W to update your trump hand."

    elif choice == "7":
        msg = "★ DEAD SILENCE active — you cannot draw cards! Use Destroy to remove it."

    elif choice == "8":
        msg = "★ OBLIVION — round cancelled. Press D to end round as VOID."

    elif choice == "9":
        print(" You lost a random trump. What card were you FORCED to draw? (highest in deck)")
        v = input(" > ").strip()
        if v:
            try:
                val = int(v)
                if 1 <= val <= 11:
                    dead_cards = sorted(set(dead_cards + [val]))
                    msg = f"Cursed! Forced draw: {val}. Added to your hand. Use W to remove lost trump."
            except ValueError:
                msg = "Invalid input."

    elif choice == "10":
        print(" How much did opponent's bet decrease by?")
        v = input(" > ").strip()
        try:
            opp_bet = max(0, opp_bet - int(v))
            msg = f"Opponent's bet reduced → now {opp_bet}"
        except ValueError:
            msg = "Invalid."

    elif choice == "11":
        print(" Describe what happened (for your notes):")
        desc = input(" > ").strip()
        msg = f"Enemy action: {desc}. Use W/X to manually update state."

    elif choice == "0":
        msg = ""

    if msg:
        print(f"\n \033[93m→ {msg}\033[0m")
        print(" TIP: Press A to re-analyze with updated state.")

    return dead_cards, current_target, player_bet, opp_bet, msg


def fight_opponent(intel: dict, player_hp: int, player_max: int,
                   challenges_completed: set = None, available_trumps: set = None,
                   mode_key: str = "3", fight_num: int = 1) -> int:
    """
    Fight one opponent across multiple rounds until one side reaches 0 HP.
    Returns player's remaining HP when the fight ends.
    mode_key: "1" Normal, "2" Survival, "3" Survival+
    fight_num: which opponent number in the gauntlet (1-10)
    """
    opp_hp = int(intel["hp"])
    opp_max = int(intel["hp"])
    round_num = 0
    round_history = []
    current_target = 21  # Reset each round (Go For cards are "while on table")
    trump_hand = []  # Player's held trump cards — persists across rounds

    print_header(f"FIGHT: vs. {intel['name']}")

    # Variant selection — if opponent has sub-variants, let player pick
    variants = intel.get("variants", {})
    if variants:
        print(f"\n Which variant of {intel['name']}?")
        print(" (Look at the sack on their head to identify)\n")
        variant_keys = list(variants.keys())
        for i, key in enumerate(variant_keys, 1):
            v = variants[key]
            trumps_str = ", ".join(v["trumps"]) if v["trumps"] else "None"
            print(f"  {i}. {key} — Trumps: {trumps_str}")
        print(f"  {len(variant_keys) + 1}. Not sure (use combined loadout)")

        v_input = input("\n > ").strip()
        try:
            v_idx = int(v_input) - 1
            if 0 <= v_idx < len(variant_keys):
                chosen = variants[variant_keys[v_idx]]
                intel = dict(intel)  # Copy so we don't mutate original
                intel["trumps"] = chosen["trumps"]
                intel["tip"] = chosen["tip"]
                intel["name"] = f"{intel['name']} ({variant_keys[v_idx]})"
                print(f"\n ★ Set to: {variant_keys[v_idx]}")
                print(f"   Trumps: {', '.join(chosen['trumps'])}")
            else:
                print(f" Using combined loadout (all possible trumps).")
        except (ValueError, IndexError):
            print(f" Using combined loadout (all possible trumps).")

    display_opponent_info(intel)

    # Initial trump hand setup
    print("\n Do you want to enter your starting trump cards? (y/n)")
    if input(" > ").strip().lower() == "y":
        trump_hand = edit_trump_hand(trump_hand, available_trumps)

    while player_hp > 0 and opp_hp > 0:
        round_num += 1
        dead_cards = []  # Fresh deck each round
        player_bet = 1   # Base bet — modified by trumps (resets each round)
        opp_bet = 1      # Base opponent bet (resets each round)
        current_target = 21  # Go For cards are "while on table" — reset each round
        face_down_card = None  # Your face-down card — remembered across re-analyzes
        print_header(f"ROUND {round_num} vs. {intel['name']}")
        display_round_history(round_history)
        display_hp_status(player_hp, player_max, opp_hp, opp_max, intel["name"])

        # ── LUCAS SAW ROUND HARD BYPASS ──
        # Normal 21 final round: Lucas cheats with Desperation + Perfect Draw.
        # Standard math is INVALID. Only solution: Love Your Enemy.
        if mode_key == "1" and round_num == 3:
            print("\n" + "=" * 60)
            print("\033[91m" + " ★★★ CRITICAL: LUCAS SAW ROUND — SCRIPTED SEQUENCE ★★★".center(60) + "\033[0m")
            print("=" * 60)
            print("""
 Standard probability logic is SUSPENDED for this round.
 This is a scripted narrative sequence that breaks normal rules.

 WHAT WILL HAPPEN:
 • Lucas will play 'Perfect Draw' → guarantees himself 21
 • Lucas will play 'Desperation' → bets become 100, NO drawing

 WHAT YOU MUST DO:
 1. Make sure 'Love Your Enemy' is in your trump hand
 2. Wait for Lucas to play Desperation
 3. IMMEDIATELY play 'Love Your Enemy'
 4. This forces Lucas to draw → he busts past 21 → YOU WIN

 ⚠ Do NOT try to beat him with standard probability or
   target manipulation. Drawing is permanently locked.
 ⚠ If you don't have 'Love Your Enemy', you CANNOT win.
""")
            print("=" * 60)
            input("\n Press Enter once this round concludes...")
            player_hp, opp_hp, entry = record_round_result(round_num, player_hp, opp_hp, intel)
            if entry is not None:
                round_history.append(entry)
            continue

        while True:
            target_label = f" [Target: {current_target}]" if current_target != 21 else ""
            trump_count = len(trump_hand)
            bet_label = ""
            if player_bet != 1 or opp_bet != 1:
                bet_label = f" [Your bet: {player_bet} | Opp bet: {opp_bet}]"
            print(f"\n ─── Round {round_num} Menu ───{target_label}{bet_label}")
            print(" A. Analyze hand (get advice)")
            print(f" \033[93mI. Interrupt — enemy played a trump!\033[0m")
            print(f" P. Play a trump card ({trump_count} in hand)")
            print(f" W. Edit trump hand ({trump_count} cards)")
            print(" D. Done — record round result")
            dead_label = f" ({sorted(dead_cards)})" if dead_cards else " (none)"
            print(f" X. Dead cards{dead_label}")
            print(" T. Trump card reference")
            print(" O. Opponent intel")
            print(" H. Round history")
            print(" S. HP status")
            print(" Q. Quit fight")

            action = input("\n Action: ").strip().upper()

            if action == "A":
                dead_cards, face_down_card = analyze_round(intel, player_hp, player_max, opp_hp, opp_max, current_target, dead_cards, challenges_completed, available_trumps, trump_hand, fight_num=fight_num, mode_key=mode_key, face_down_card=face_down_card)

            elif action == "P":
                if not trump_hand:
                    print(" No trump cards in hand. Use W to add them.")
                    continue
                display_trump_hand(trump_hand)
                print("\n Which card to play? (number, or Enter to cancel)")
                p_input = input(" > ").strip()
                if not p_input:
                    continue
                try:
                    idx = int(p_input) - 1
                    if 0 <= idx < len(trump_hand):
                        played = trump_hand[idx]
                        print(f"\n Playing: {played}")
                        print(f" Effect: {TRUMPS.get(played, {}).get('desc', '?')}")

                        # Handle target changers — auto-updates target
                        if played in ("Go for 17", "Go for 24", "Go for 27"):
                            new_target = int(played.split()[-1])
                            current_target = new_target
                            trump_hand.pop(idx)
                            print(f" ★ Target changed to {current_target}!")

                        # Handle bet modifiers — auto-updates bets
                        elif played == "One-Up":
                            opp_bet += 1
                            trump_hand.pop(idx)
                            print(f" ★ Opponent's bet +1 → now {opp_bet}. (Also draw 1 trump — use W to add it.)")

                        elif played == "Two-Up":
                            opp_bet += 2
                            trump_hand.pop(idx)
                            print(f" ★ Opponent's bet +2 → now {opp_bet}. (Also draw 1 trump — use W to add it.)")

                        elif played == "Two-Up+":
                            opp_bet += 2
                            trump_hand.pop(idx)
                            print(f" ★ Returned opponent's last face-up card to deck. Opp bet +2 → now {opp_bet}.")
                            print(" What card was returned? (value, to remove from dead cards)")
                            r_input = input(" > ").strip()
                            if r_input:
                                try:
                                    rv = int(r_input)
                                    if rv in dead_cards:
                                        dead_cards.remove(rv)
                                        print(f" Card {rv} returned to deck pool.")
                                except ValueError:
                                    pass

                        elif played == "Shield":
                            player_bet = max(0, player_bet - 1)
                            trump_hand.pop(idx)
                            print(f" ★ Your bet -1 → now {player_bet}.")

                        elif played == "Shield+":
                            player_bet = max(0, player_bet - 2)
                            trump_hand.pop(idx)
                            print(f" ★ Your bet -2 → now {player_bet}.")

                        # Handle Return (needs current hand state — ask for card)
                        elif played == "Return":
                            print(" Which card are you returning? (card value)")
                            ret_input = input(" > ").strip()
                            if ret_input:
                                try:
                                    ret_card = int(ret_input)
                                    if 1 <= ret_card <= 11:
                                        print(f" ★ Returned {ret_card} to deck.")
                                        trump_hand.pop(idx)
                                    else:
                                        print(" Invalid card value.")
                                except ValueError:
                                    print(" Invalid input.")
                            else:
                                print(" Cancelled.")

                        # Handle Remove
                        elif played == "Remove":
                            print(" Which opponent card was removed? (card value)")
                            rem_input = input(" > ").strip()
                            if rem_input:
                                try:
                                    rem_card = int(rem_input)
                                    if 1 <= rem_card <= 11:
                                        dead_cards = sorted(set(dead_cards + [rem_card]))
                                        print(f" ★ Removed opponent's {rem_card}. Added to dead cards.")
                                        trump_hand.pop(idx)
                                    else:
                                        print(" Invalid card value.")
                                except ValueError:
                                    print(" Invalid input.")
                            else:
                                print(" Cancelled.")

                        # Handle Exchange
                        elif played == "Exchange":
                            print(" What card did you give? (your card value)")
                            give_input = input(" > ").strip()
                            print(" What card did you take? (opponent's card value)")
                            take_input = input(" > ").strip()
                            if give_input and take_input:
                                try:
                                    gave = int(give_input)
                                    took = int(take_input)
                                    print(f" ★ Exchanged: gave {gave}, took {took}.")
                                    trump_hand.pop(idx)
                                except ValueError:
                                    print(" Invalid input.")
                            else:
                                print(" Cancelled.")

                        # Handle Love Your Enemy
                        elif played == "Love Your Enemy":
                            print(" What card did the opponent draw?")
                            lye_input = input(" > ").strip()
                            if lye_input:
                                try:
                                    drawn = int(lye_input)
                                    if 1 <= drawn <= 11:
                                        print(f" ★ Forced opponent to draw {drawn}.")
                                        trump_hand.pop(idx)
                                    else:
                                        print(" Invalid card value.")
                                except ValueError:
                                    print(" Invalid input.")
                            else:
                                print(" Cancelled.")

                        # Handle Perfect Draw / Ultimate Draw
                        elif played in ("Perfect Draw", "Perfect Draw+", "Ultimate Draw"):
                            print(" What card did you draw?")
                            pd_input = input(" > ").strip()
                            if pd_input:
                                try:
                                    drawn = int(pd_input)
                                    if 1 <= drawn <= 11:
                                        print(f" ★ Drew {drawn} via {played}.")
                                        if played == "Perfect Draw+":
                                            opp_bet += 5
                                            print(f" ★ Opponent's bet +5 → now {opp_bet}.")
                                        elif played == "Ultimate Draw":
                                            print(" (Also draw 2 trumps — use W to add them.)")
                                        trump_hand.pop(idx)
                                    else:
                                        print(" Invalid card value.")
                                except ValueError:
                                    print(" Invalid input.")
                            else:
                                print(" Cancelled.")

                        # Handle numbered draw cards (2-7 Card) — with failed draw deduction
                        elif played in ("2 Card", "3 Card", "4 Card", "5 Card", "6 Card", "7 Card"):
                            card_val = int(played[0])
                            print(f"\n Did the draw succeed? (Was {card_val} still in the deck?)")
                            print(f"  Y = yes, drew {card_val}")
                            print(f"  N = no, nothing happened (card not in deck)")
                            result = input(" > ").strip().upper()
                            if result == "Y":
                                dead_cards = sorted(set(dead_cards + [card_val]))
                                trump_hand.pop(idx)
                                print(f" ★ Drew {card_val}. Added to your hand.")
                            elif result == "N":
                                trump_hand.pop(idx)
                                # ── CRITICAL DEDUCTION ──
                                # Card not in deck = opponent has it (face-down hidden card)
                                # unless it's already visible on the board
                                if card_val not in dead_cards:
                                    print(f"\n \033[93m★★ INTEL: {card_val} is NOT in the deck!\033[0m")
                                    print(f" \033[93m   → Opponent's hidden card is almost certainly {card_val}.\033[0m")
                                    print(f"   (Unless {card_val} was already drawn and you forgot to track it.)")
                                else:
                                    print(f" {card_val} was already out of the deck.")
                            else:
                                print(" Cancelled.")

                        else:
                            # Generic trump — just remove from hand
                            trump_hand.pop(idx)
                            print(f" ★ {played} played.")
                    else:
                        print(" Invalid number.")
                except ValueError:
                    print(" Invalid input.")

            elif action == "I":
                # ── INTERRUPT: Enemy played a trump card ──
                dead_cards, current_target, player_bet, opp_bet, int_msg = handle_interrupt(
                    dead_cards, current_target, player_bet, opp_bet
                )

            elif action == "W":
                trump_hand = edit_trump_hand(trump_hand, available_trumps)

            elif action == "X":
                if dead_cards:
                    print(f"\n Dead cards: {sorted(dead_cards)}")
                    print(" Options: Enter = keep, 'c' = clear all, or enter cards to add")
                    x_input = input(" > ").strip().lower()
                    if x_input == "c":
                        dead_cards = []
                        print(" Dead cards cleared.")
                    elif x_input:
                        try:
                            new_cards = [int(x) for x in x_input.split()]
                            dead_cards = sorted(set(dead_cards + [c for c in new_cards if 1 <= c <= 11]))
                            print(f" Dead cards: {dead_cards}")
                        except ValueError:
                            print(" Invalid input.")
                else:
                    print("\n No dead cards yet. Enter cards to add (or Enter to skip):")
                    x_input = input(" > ").strip()
                    if x_input:
                        try:
                            dead_cards = sorted(set(int(x) for x in x_input.split() if 1 <= int(x) <= 11))
                            print(f" Dead cards: {dead_cards}")
                        except ValueError:
                            print(" Invalid input.")

            elif action == "D":
                player_hp, opp_hp, entry = record_round_result(round_num, player_hp, opp_hp, intel)
                if entry is not None:
                    round_history.append(entry)

                display_hp_status(player_hp, player_max, opp_hp, opp_max, intel["name"])

                if opp_hp <= 0:
                    print(f"\n ★★★ {intel['name']} DEFEATED! ★★★")
                    print(f" Rounds fought: {round_num}")
                    wins = sum(1 for e in round_history if e["result"] == "WIN")
                    losses = sum(1 for e in round_history if e["result"] == "LOSS")
                    voids = sum(1 for e in round_history if e["result"] == "VOID")
                    ties = sum(1 for e in round_history if e["result"] == "TIE")
                    print(f" Record: {wins}W / {losses}L / {ties}T / {voids}V")
                    break

                if player_hp <= 0:
                    print(f"\n ✖✖✖ YOU DIED vs. {intel['name']} ✖✖✖")
                    print(f" Rounds survived: {round_num}")
                    break

                # Round recorded and neither died → ask about trump changes
                enemy_trump_effects = [t for t in intel.get("trumps", [])
                                       if t in ("Curse", "Mind Shift", "Mind Shift+", "Desire", "Desire+", "Happiness")]
                if enemy_trump_effects or trump_hand:
                    print(f"\n Did your trump hand change this round? (opponent trumps, draws, etc.)")
                    print(f"  Current hand: {trump_hand if trump_hand else '(empty)'}")
                    print(f"  Y = edit hand, Enter = no changes")
                    if input(" > ").strip().lower() == "y":
                        trump_hand = edit_trump_hand(trump_hand, available_trumps)
                break

            elif action == "T":
                display_trumps_reference()
                input(" Press Enter to continue...")

            elif action == "O":
                display_opponent_info(intel)

            elif action == "H":
                display_round_history(round_history)

            elif action == "S":
                display_hp_status(player_hp, player_max, opp_hp, opp_max, intel["name"])

            elif action == "Q":
                confirm = input(" Quit fight? Progress is lost. (y/n): ").strip().lower()
                if confirm == "y":
                    return player_hp

            else:
                print(" Invalid action. Use A/I/P/W/D/X/T/O/H/S/Q.")

    return player_hp


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
            label += " \033[93m★ PRIORITY TARGET (unlocks Harvest!)\033[0m"
        print(label)

    if not harvest_unlocked:
        print(f"\n \033[93m★ TIP: If Mr. Big Head appears, prioritize beating him!\033[0m")
        print(f"   Defeating him twice unlocks 'Harvest' (trump draw after every trump you play).")

    while True:
        choice = input(f"\n Select (1-{len(pool)}): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(pool):
                selected = pool[idx]
                if "Big Head" in selected["name"] and not harvest_unlocked:
                    print(f"\n \033[93m★ Mr. Big Head — PRIORITY: Beat him to unlock Harvest!\033[0m")
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
        player_hp = fight_opponent(opp, player_hp, player_max, challenges_completed, available_trumps,
                                   mode_key=mode_key, fight_num=fight_num)

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
                print(f"   \033[93mRestart run for a fresh no-damage attempt? (y/n)\033[0m")
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
                print(f"\n \033[93m⚠ HP check: {player_hp} HP, {remaining_fights} fights left — playing tight.\033[0m")

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
                          mode_key="3", fight_num=0)
        else:
            print(" Invalid selection.")
    except ValueError:
        print(" Invalid input.")


# ============================================================
# CHALLENGE LAB
# ============================================================
def run_bust_win_planner() -> None:
    """Priority challenge planner: defeat opponent while bust."""
    print_header("PRIORITY CHALLENGE: WIN WHILE BUST")
    print(" Goal reward: Starting Trump Card +1")
    print(" Rule: if BOTH bust, the one closer to target wins.\n")

    try:
        tgt_input = input(" Target total (default 21, supports 24/27): ").strip()
        target = int(tgt_input) if tgt_input else 21
        if target not in (17, 21, 24, 27):
            print(" Unsupported target. Use 17, 21, 24, or 27.")
            return

        print("\n Enter YOUR current cards (space-separated):")
        u_hand = parse_card_values(input(" > ").strip())
        print(" Enter OPPONENT visible cards:")
        o_vis = parse_card_values(input(" > ").strip())
        print(" Enter known dead/removed cards (Enter for none):")
        dead = parse_card_values(input(" > ").strip())

        hidden_raw = input(" Opponent hidden card if known (Enter if unknown): ").strip()
        known_hidden = int(hidden_raw) if hidden_raw else None
        if known_hidden is not None and not (1 <= known_hidden <= 11):
            print(" Hidden card must be 1-11.")
            return

        known_cards = u_hand + o_vis + dead
        if known_hidden is not None:
            known_cards.append(known_hidden)

        # One-of-each deck warning
        seen = set()
        for c in known_cards:
            if c in seen:
                print(f" WARNING: Card {c} appears more than once in your input.")
            seen.add(c)

        accounted = sorted(set(known_cards))
        remaining = [c for c in range(1, 12) if c not in accounted]
        u_total = sum(u_hand)
        o_visible_total = sum(o_vis)

        display_card_matrix(accounted)
        print(f"\n Your total now: {u_total}")
        print(f" Opponent visible total: {o_visible_total}")
        print(f" Candidate cards remaining: {len(remaining)}")

        if not remaining:
            print(" No remaining cards to evaluate.")
            return

        hidden_candidates = [known_hidden] if known_hidden is not None else remaining[:]
        _, best = evaluate_bust_challenge(u_total, o_visible_total, remaining, target, hidden_candidates)

        labels = {
            "stay": "Bust then STAY",
            "force_random": "Bust then FORCE RANDOM draw",
            "force_highest": "Bust then FORCE HIGHEST draw",
        }

        print_header("BUST-WIN ODDS")
        for mode in ("stay", "force_random", "force_highest"):
            rec = best.get(mode)
            if rec is None:
                print(f"\n {labels[mode]}: No valid bust line.")
                continue
            print(
                f"\n {labels[mode]}:\n"
                f"  Best draw card: {rec['draw_card']} -> you reach {rec['your_total']} (+{rec['your_over']} over)\n"
                f"  Win {rec['win'] * 100:.1f}% | Tie {rec['tie'] * 100:.1f}% | Loss {rec['loss'] * 100:.1f}%"
            )

        candidates = [v for v in best.values() if v is not None]
        if candidates:
            top = max(candidates, key=lambda r: (r["win"], -r["loss"]))
            top_mode = next(k for k, v in best.items() if v == top)
            print_header("RECOMMENDED LINE")
            print(
                f" {labels[top_mode]}\n"
                f" Draw {top['draw_card']} -> total {top['your_total']}.\n"
                " Keep your bust small and force opponent to over-bust."
            )
        else:
            print("\n No feasible bust setup from this state.")

        print(
            "\n Practical execution:\n"
            " - Prefer busting by +1 or +2 only.\n"
            " - Then force opponent draw if you can (Love Your Enemy / Curse / Black Magic lines).\n"
            " - Track whether 9/10/11 are still live before committing."
        )

    except ValueError as exc:
        print(f" Input error: {exc}")


def run_fifteen_trump_planner() -> None:
    """Plan a 15-trump win round for Trump Switch+ unlock."""
    print_header("CHALLENGE: WIN ROUND USING 15 TRUMPS")
    print(" Goal reward: Trump Switch+")
    print(" Constraint: max 5 permanent trumps active on table at once.\n")

    print(" ─── SURVIVAL vs SURVIVAL+ ───\n")
    print(" SURVIVAL (21):")
    print("   Opponents have 5 HP → fights last 3-5 rounds.")
    print("   Fewer trump draws per round, limited cycling.")
    print("   \033[93mVERY DIFFICULT — possible only with Harvest + Trump Switch.\033[0m")
    print("   You need a long round against Molded Hoffman (boss).")
    print()
    print(" SURVIVAL+ (21+):")
    print("   Opponents have 10 HP → fights last 5-10 rounds.")
    print("   More time to accumulate and cycle trumps.")
    print("   \033[92mRECOMMENDED — best chance against Barbed Wire or boss fights.\033[0m")
    print("   With Harvest active, every trump you play draws a replacement.")
    print()
    print(" ─── REQUIRED SETUP ───\n")
    print(" MUST HAVE:")
    print("   ★ Harvest (play first — every trump after draws a replacement)")
    print("   ★ Trump Switch or Trump Switch+ (cycle: discard old, draw new)")
    print()
    print(" IDEAL COMBO:")
    print("   1. Play Harvest (use 1, now drawing replacements)")
    print("   2. Play cheap trumps: Shield, One-Up, numbered cards (use 2-5)")
    print("   3. Trump Switch+ → discard 1, draw 4 (use 6, gain 4 cards)")
    print("   4. Play all 4 new cards (use 7-10)")
    print("   5. Trump Switch → discard 2, draw 3 (use 11, gain 3)")
    print("   6. Play remaining (use 12-15)")
    print("   7. Win the round!")
    print()
    print(" KEY: Non-permanent trumps (numbered cards, Return, Exchange)")
    print(" don't take table slots. Permanent trumps (Shield, One-Up, etc.)")
    print(" take 1 of 5 slots. Prioritize non-permanent plays.\n")

    try:
        print(" ─── LIVE TRACKER ───")
        used = int(input("\n Trumps used this round so far: ").strip() or "0")
        active_perm = int(input(" Permanent trumps on table (0-5): ").strip() or "0")
        non_perm_hand = int(input(" Non-permanent trumps in hand: ").strip() or "0")
        perm_hand = int(input(" Permanent trumps in hand: ").strip() or "0")
        has_harvest = input(" Is Harvest active? (y/n): ").strip().lower() == "y"
        has_switch = input(" Have Trump Switch/Switch+? (y/n): ").strip().lower() == "y"

        active_perm = max(0, min(5, active_perm))
        need = max(0, 15 - used)
        slots_left = max(0, 5 - active_perm)
        immediate_capacity = non_perm_hand + min(perm_hand, slots_left)

        print(f"\n ── STATUS ──")
        print(f" Used: {used}/15 | Need: {need} more")
        print(f" Permanent slots: {5 - slots_left}/5 used ({slots_left} left)")
        print(f" Playable right now: {immediate_capacity}")
        if has_harvest:
            print(" Harvest: ACTIVE ★ (each play draws a replacement)")
        if has_switch:
            print(" Trump Switch available: can cycle for +1-3 net cards")

        if need == 0:
            print(f"\n \033[92m★ Requirement MET! Win the round now!\033[0m")
            return

        projected = immediate_capacity
        if has_harvest:
            projected += min(immediate_capacity, 3)  # Harvest replacements
        if has_switch:
            projected += 3  # Net gain from switch

        if projected >= need:
            print(f"\n \033[92m✓ You can likely reach 15 this round (projected: ~{used + projected}).\033[0m")
        else:
            shortfall = need - projected
            print(f"\n \033[93m⚠ Short by ~{shortfall}. Need more cycling or trump draws.\033[0m")
            if not has_harvest:
                print("   → Play Harvest first if you have it!")
            if not has_switch:
                print("   → Trump Switch would help cycle cards.")

        print(
            "\n Sequence:\n"
            " 1) Non-permanent effects first (don't waste table slots).\n"
            " 2) Fill permanent slots only when needed.\n"
            " 3) Use Trump Switch to cycle when hand is low.\n"
            " 4) Once at 15, secure the round win."
        )

    except ValueError:
        print(" Invalid input.")


def show_no_damage_blueprint() -> None:
    """Strategy guide for no-damage Survival runs. Live tracking is built into run_mode."""
    print_header("NO-DAMAGE SURVIVAL — STRATEGY GUIDE")
    print(f" Objective: {CHALLENGE_GOALS['no_damage_survival']['name']}")
    print(f" Reward: {CHALLENGE_GOALS['no_damage_survival']['reward']}")
    print()
    print(" \033[92m★ Live tracking is automatic when you play Survival mode.\033[0m")
    print("   The solver detects damage and offers to restart immediately.")
    print("   Survival+ no-damage is cosmetic only — not tracked.\n")

    print(" KEY PRINCIPLES:")
    print("  - Win 5 fights taking ZERO total damage.")
    print("  - Save Shields for emergencies (reduce loss damage to 0).")
    print("  - Save Destroy for Molded Hoffman's Curse (fight #5).")
    print("  - If you take ANY damage, restart immediately.\n")

    print(" ─── PER-FIGHT STRATEGY ───")
    print()
    print(" Fight 1 (Tally Mark): Easy. Stay at 17+. Don't use valuable trumps.")
    print("   → If you lose R1 with bet=1, Shield negates it. Otherwise restart.")
    print()
    print(" Fight 2 (Bloody Handprints): Desire + Mind Shift.")
    print("   → Dump cheap trumps (play 2/round to block Mind Shift).")
    print("   → Don't hoard — Desire punishes it.")
    print()
    print(" Fight 3 (Barbed Wire): Shield spam + Shield Assault.")
    print("   → Destroy Shield Assault immediately.")
    print("   → Watch for Go for 17 target change.")
    print()
    print(" Fight 4 (Tally Mark Upgraded): Slightly harder basic.")
    print("   → Clean play. Save trumps for boss.")
    print()
    print(" Fight 5 (Molded Hoffman BOSS): Curse + Conjure.")
    print("   → MUST have Destroy ready for Curse.")
    print("   → Return/Exchange to fix forced bad draws.")
    print("   → Card-count obsessively.\n")

    print(" ─── RESTART DECISION TREE ───")
    print()
    print(" RESTART IMMEDIATELY IF:")
    print("   ✖ You take ANY damage (challenge void)")
    print("   ✖ All Destroy cards gone before fight #5")
    print()
    print(" CONSIDER RESTARTING IF:")
    print("   ⚠ Used Shield early (none left for emergencies)")
    print("   ⚠ Used Destroy on non-Curse target (need it for fight #5)")
    print()
    print(" KEEP GOING IF:")
    print("   ✓ Full HP through fight #3")
    print("   ✓ Have 1+ Destroy and 1+ Shield entering fight #5")


def display_challenge_sources() -> None:
    """Show the internet sources used for challenge strategy."""
    print_header("CHALLENGE SOURCES")
    for label, url in CHALLENGE_SOURCES:
        print(f" - {label}: {url}")
    print(
        "\n Source notes:\n"
        " - Core rules/rewards from RE wiki pages.\n"
        " - Execution details are community-tested tactics."
    )


def run_challenge_lab() -> None:
    """Focused tools for high-value challenge clears."""
    while True:
        print_header("CHALLENGE LAB")
        print("\n Bust-Win challenge is now integrated into normal play advice.")
        print(" When you have a good chance to win while bust, the solver will tell you.\n")
        print(" 1. 15-Trump Planner")
        print(" 2. No-Damage Blueprint")
        print(" 3. Internet Sources")
        print(" Q. Back")

        choice = input("\n Select: ").strip().upper()
        if choice == "1":
            run_fifteen_trump_planner()
            input("\n Press Enter to continue...")
        elif choice == "2":
            show_no_damage_blueprint()
            input("\n Press Enter to continue...")
        elif choice == "3":
            display_challenge_sources()
            input("\n Press Enter to continue...")
        elif choice == "Q":
            return
        else:
            print(" Invalid selection.")


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
        print(" C. Challenge Lab (priority unlock planner)")
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
        elif choice == "C":
            run_challenge_lab()
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
