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
- Goal: get closer to target (21, or 24 if "Go for 24" is active) without going over.
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
        "desc": "Tutorial opponent. Plays standard 21 with basic trumps.",
        "ai": "BASIC",
        "trumps": ["One Up", "Two Up", "Shield"],
        "stay_val": 17,
        "hp": 10,
        "tip": (
            "Lucas plays conservatively. He'll stay around 17+.\n"
            "Use this match to learn trump card timing.\n"
            "Save strong trumps when possible — play solid fundamentals."
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
        "desc": "Sack head with tally marks. No special trumps but sharper AI.",
        "ai": "BASIC+",
        "trumps": [],
        "stay_val": 17,
        "hp": 10,
        "tip": (
            "No special trump cards, but smarter than Survival version.\n"
            "The more marks on the sack, the deadlier the variant.\n"
            "Decent player — don't underestimate."
        ),
    },
    {
        "name": "Bloody Handprints Hoffman",
        "mode": "Survival+",
        "desc": "Sack head covered in bloody handprints.",
        "ai": "TRUMP STEALER",
        "trumps": ["Desire", "Mind Shift", "Happiness"],
        "stay_val": 16,
        "hp": 10,
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
        "mode": "Survival+",
        "desc": "Sack head with barbed wire / side-to-side slash marks.",
        "ai": "SHIELD SPAMMER",
        "trumps": ["Shield Assault", "Shield Assault+"],
        "stay_val": 14,
        "hp": 10,
        "tip": (
            "Always packs lots of Shield cards, then sacrifices them.\n"
            "'Shield Assault' removes 3 Shields to raise YOUR bet by 3.\n"
            "'Shield Assault+' removes 2 Shields to raise YOUR bet by 5.\n"
            "COUNTER: Use 'Destroy' on Shield Assault+.\n"
            "Stack bet-ups to push damage past his shields."
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
    "trumps": ["Curse", "Black Magic", "Conjure"],
    "stay_val": 17,
    "hp": 10,
    "tip": (
        "!! MID-BOSS — ALWAYS FIGHT #5 !!\n"
        "'Curse' discards one of your trumps AND forces you to draw\n"
        "the HIGHEST remaining card.\n"
        "'Black Magic' discards half your trumps, raises bet by 10\n"
        "(instant death if you lose!), AND he draws the best card.\n"
        "'Conjure' lets him draw 3 trumps (his bet +1 — slight advantage for you).\n"
        "STRATEGY: Save 'Destroy' for Black Magic (highest priority!).\n"
        "Use 'Return'/'Exchange' to fix forced bad draws.\n"
        "Card-count obsessively — know what Curse will force."
    ),
}

BOSS_SURVIVAL_PLUS_FINAL = {
    "name": "Undead Hoffman (Final Boss)",
    "mode": "Survival+",
    "desc": "Knives and scissors embedded in head. ALWAYS opponent #10.",
    "ai": "GAME BREAKER",
    "trumps": ["Oblivion", "Dead Silence", "Perfect Draw"],
    "stay_val": 18,
    "hp": 10,
    "tip": (
        "!! FINAL BOSS — MOST DANGEROUS OPPONENT !!\n"
        "Has tons of Perfect Draws — almost always gets high numbers.\n"
        "'Dead Silence' prevents you from drawing ANY cards (even via trumps).\n"
        "'Oblivion' cancels the entire round — annoying but not fatal.\n"
        "STRATEGY:\n"
        " 1) Save 'Destroy' for Dead Silence (highest priority).\n"
        " 2) If he uses Perfect Draw and you know his total, use\n"
        "    'Exchange' — if your last card > his, it busts him.\n"
        " 3) Oblivion wastes your good hands but keep pressure up.\n"
        " 4) 'Perfect Draw' (if unlocked) is huge here."
    ),
}

# ============================================================
# TRUMP CARD DATABASE
# ============================================================
TRUMPS = {
    "One Up": {"cat": "Bet", "desc": "Increases the bet (damage) by 1."},
    "Two Up": {"cat": "Bet", "desc": "Increases the bet (damage) by 2. Stackable."},
    "Three Up": {"cat": "Bet", "desc": "Increases the bet (damage) by 3. Stackable."},
    "Twenty-One Up": {"cat": "Bet", "desc": "Sets bet to 21 (often instant-kill territory)."},
    "Shield": {"cat": "Defense", "desc": "Reduces damage taken this round by 1."},
    "Shield+": {"cat": "Defense", "desc": "Reduces damage taken this round by 2."},
    "Shield Assault": {"cat": "Defense", "desc": "Reduces damage by 3; deals 1 damage to you when played."},
    "Shield Assault+": {"cat": "Defense", "desc": "Reduces damage by 5; deals 1 damage to you when played."},
    "Return": {"cat": "Cards", "desc": "Returns your last drawn card to the deck."},
    "Exchange": {"cat": "Cards", "desc": "Swaps one of your cards with a random remaining card."},
    "Perfect Draw": {"cat": "Cards", "desc": "Draws the exact card needed for 21 (unlockable)."},
    "Curse": {"cat": "Cards", "desc": "Forces opponent to draw the HIGHEST remaining card."},
    "Black Magic": {"cat": "Cards", "desc": "Forces opponent to draw a specific chosen card."},
    "Conjure": {"cat": "Cards", "desc": "Adds a card from outside the deck to the user's hand."},
    "Destroy": {"cat": "Counter", "desc": "Removes the LAST trump card the opponent played."},
    "Destroy+": {"cat": "Counter", "desc": "Removes ALL opponent trump cards played this round."},
    "Love Your Enemy": {"cat": "Attack", "desc": "Forces opponent to draw a card (often causing a bust)."},
    "Mind Shift": {"cat": "Attack", "desc": "Steals one of the opponent's trump cards."},
    "Escape": {"cat": "Special", "desc": "Cancels the round. No damage to either side."},
    "Oblivion": {"cat": "Special", "desc": "Cancels the round — no winner, no loser."},
    "Dead Silence": {"cat": "Special", "desc": "Prevents opponent from drawing any more cards."},
    "Desire": {"cat": "Special", "desc": "Increases bet based on opponent's trump count."},
    "Happiness": {"cat": "Special", "desc": "Heals the user when they win the round."},
    "Go for 24": {"cat": "Special", "desc": "Changes round target from 21 to 24 (unlockable)."},
    "Harvest": {"cat": "Special", "desc": "Draw a trump whenever any trump is used."},
}

# ============================================================
# CHALLENGE DATA (priority objectives + source links)
# ============================================================
CHALLENGE_GOALS = {
    "bust_win": {
        "name": "Defeat an opponent despite being bust",
        "reward": "Starting Trump Card +1",
        "priority": "PRIORITY",
    },
    "fifteen_trumps": {
        "name": "Win a round having used at least 15 trump cards",
        "reward": "Trump Switch+",
        "priority": "HIGH",
    },
    "no_damage_survival": {
        "name": "Complete Survival without being tortured once",
        "reward": "Ultimate Draw",
        "priority": "HIGH",
    },
    "no_damage_survival_plus": {
        "name": "Complete Survival+ without being tortured once",
        "reward": "Grand Reward",
        "priority": "HIGH",
    },
}

CHALLENGE_SOURCES = [
    ("RE Wiki - 21 rewards list", "https://residentevil.fandom.com/wiki/21"),
    ("RE Wiki - basic rules", "https://residentevil.fandom.com/wiki/Card_Game_%2221%22_-_Basic_Rules"),
    ("RE Wiki - trump cards", "https://residentevil.fandom.com/wiki/Trump_cards"),
    ("TrueAchievements - Survival+ strategy discussion", "https://www.trueachievements.com/a229688/you-gotta-know-when-to-hold-em-achievement"),
    ("EntranceJew odds helper", "https://entrancejew.itch.io/re7-21-tool"),
]

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
    """Print detailed opponent info."""
    print(f"\n ┌─ TARGET: {intel['name']}")
    print(f" │ Mode: {intel.get('mode','?')}")
    print(f" │ AI Type: {intel.get('ai','?')}")
    print(f" │ Trumps: {', '.join(intel.get('trumps', []))}")
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
      - stay: opponent does not draw
      - hit_once: opponent draws one card then stops
      - auto / hit_to_threshold: opponent hits until reaching stay_val or bust
    """
    behavior = behavior.lower().strip()
    deck = tuple(sorted(set(remaining)))

    if behavior == "stay" or o_visible_total > target:
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

    def _dfs(total: int, deck_state: tuple):
        key = (total, deck_state)
        if key in memo:
            return memo[key]

        if total > target:
            memo[key] = {total: 1.0}
            return memo[key]

        if behavior in ("auto", "hit_to_threshold"):
            if total >= stay_val or not deck_state:
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
):
    """Generate strategic advice factoring in HP state + opponent trumps."""
    advice_lines = []
    priority_warnings = []

    stay_val = int(intel.get("stay_val", 17))
    # Adjust opponent AI threshold when target is raised (e.g., Go for 24)
    if target > 21:
        stay_val += (target - 21)

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

    if "Mind Shift" in trumps:
        advice_lines.append("MIND SHIFT: He can steal your trumps. Destroy it immediately if you can.")

    if "Desire" in trumps:
        advice_lines.append("DESIRE: Bet scales with YOUR trump count. Don't hoard trumps.")

    if "Shield Assault" in trumps or "Shield Assault+" in trumps:
        advice_lines.append("SHIELD ASSAULT: Negates your damage AND hurts you. Stack bet-ups to overwhelm.")

    if "Oblivion" in trumps:
        advice_lines.append("OBLIVION: Can void a round. Annoying, not fatal — replay and keep pressure.")

    # ── Core draw/stay decision ──
    estimated_opp = estimate_opponent_total(o_visible_total, stay_val)
    behavior_key = (opp_behavior or "auto").strip().lower()

    behavior_label = {
        "stay": "Opponent stopped drawing",
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
        return priority_warnings, advice_lines

    # Outcome model: compare staying now vs hitting now using selected opponent behavior.
    stay_probs, hit_probs = evaluate_stay_hit_outcomes(
        u_total, o_visible_total, remaining, stay_val, target, behavior_key
    )
    bust_pct = 100.0 - safe_pct
    advice_lines.append(f"MODEL: {behavior_label}.")
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

    # Force draw analysis (Love Your Enemy — stay at your total, force opponent to draw)
    force_probs = None
    opp_bust_from_force = 0.0
    if remaining and behavior_key != "stay":
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

    # ── Action recommendation ──
    # Find the best option among STAY, HIT, and FORCE DRAW
    options = {
        "STAY": stay_probs["win"],
        "HIT": hit_probs["win"],
    }
    if force_probs is not None:
        options["FORCE A DRAW (Love Your Enemy)"] = force_probs["win"]

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
def record_round_result(round_num: int, player_hp: int, opp_hp: int):
    """
    Ask what happened and update HP.
    Damage in RE7 21 is based on the bet amount, not score difference.
    - Survival: 1 finger per loss (base bet = 1)
    - Survival+/Normal: voltage/saw moves by the bet amount
    Returns: (new_player_hp, new_opp_hp, round_entry_dict or None)
    """
    print_header("ROUND RESULT")
    print(" What happened this round?\n")
    print(" 1. I WON")
    print(" 2. I LOST")
    print(" 3. TIE (no damage)")
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
def analyze_round(intel: dict, player_hp: int, player_max: int, opp_hp: int, opp_max: int, target: int = 21, dead_cards: list = None) -> list:
    """Run the solver for one round of 21 (read-only, no HP changes).
    Returns updated dead_cards list for persistence across rounds."""
    if dead_cards is None:
        dead_cards = []
    display_hp_status(player_hp, player_max, opp_hp, opp_max, intel["name"])

    print(f"\n Current target: {target}")
    if target > 21:
        print(f" ★ 'Go for 24' is ACTIVE — target is {target}!")

    # Default to normal AI behavior; override only if needed
    opp_behavior = "auto"

    try:
        print(f"\n Enter YOUR card values (space-separated, e.g., '10 6'):")
        u_input = input(" > ").strip()
        if not u_input:
            print(" No cards entered.")
            return dead_cards
        u_hand = list(map(int, u_input.split()))
        for c in u_hand:
            if c < 1 or c > 11:
                print(f" ERROR: Card {c} invalid (1–11).")
                return dead_cards

        print(" Enter OPPONENT'S visible card(s) (space-separated):")
        o_input = input(" > ").strip()
        if not o_input:
            print(" No opponent cards entered.")
            return dead_cards
        o_vis = list(map(int, o_input.split()))
        for c in o_vis:
            if c < 1 or c > 11:
                print(f" ERROR: Card {c} invalid (1–11).")
                return dead_cards

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
                return dead_cards
        dead = sorted(set(dead_cards + new_dead))
        for c in dead:
            if c < 1 or c > 11:
                print(f" ERROR: Card {c} invalid (1–11).")
                return dead_cards

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
        print("  2. Opponent stayed (done drawing)")
        print("  3. I forced a draw (Love Your Enemy / similar)")
        beh_input = input(" > ").strip()
        if beh_input == "2":
            opp_behavior = "stay"
            print(" What's their total? (shown on screen)")
            opp_total_raw = input(" > ").strip()
            if opp_total_raw:
                new_total = int(opp_total_raw)
                hidden_sum = new_total - o_total
                if 1 <= hidden_sum <= 11 and hidden_sum in remaining:
                    # Single hidden card, auto-remove from deck
                    remaining.remove(hidden_sum)
                    accounted = sorted(set(accounted + [hidden_sum]))
                    print(f" → Hidden card: {hidden_sum} (removed from deck)")
                elif hidden_sum > 11:
                    # Multiple hidden cards — ask
                    print(f" Hidden cards sum to {hidden_sum}. Enter card values (space-separated):")
                    hidden_raw = input(" > ").strip()
                    if hidden_raw:
                        for hc in [int(x) for x in hidden_raw.split()]:
                            if hc in remaining:
                                remaining.remove(hc)
                            if hc not in accounted:
                                accounted = sorted(set(accounted + [hc]))
                o_total = new_total
                print(f" → Opponent locked in at {o_total}")
            else:
                print(f" → Using visible total: {o_total}")
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

        opp_label = "OPPONENT FINAL" if opp_behavior == "stay" else "OPPONENT VISIBLE"
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
        warnings, advice = generate_advice(
            u_total, o_total, intel, remaining, target, safe_pct, perfect_draws,
            player_hp, player_max, opp_hp, opp_max, opp_behavior
        )
        for w in warnings:
            print(f"\n \033[91m{w}\033[0m")
        for a in advice:
            print(f"\n {a}")

        tip = intel.get("tip", "")
        if tip:
            print(f"\n OPPONENT TIP:\n {tip}")
        print("\n" + "=" * 60)

        return dead

    except ValueError:
        print(" ERROR: Enter valid numbers only.")
        return dead_cards


# ============================================================
# FIGHT LOOP — Multiple rounds vs. one opponent until death
# ============================================================
def fight_opponent(intel: dict, player_hp: int, player_max: int) -> int:
    """
    Fight one opponent across multiple rounds until one side reaches 0 HP.
    Returns player's remaining HP when the fight ends.
    """
    opp_hp = int(intel["hp"])
    opp_max = int(intel["hp"])
    round_num = 0
    round_history = []
    current_target = 21  # Persists across rounds; toggle with 'G'
    dead_cards = []       # Cards removed by Destroy etc.; persists across rounds

    print_header(f"FIGHT: vs. {intel['name']}")
    display_opponent_info(intel)

    while player_hp > 0 and opp_hp > 0:
        round_num += 1
        print_header(f"ROUND {round_num} vs. {intel['name']}")
        display_round_history(round_history)
        display_hp_status(player_hp, player_max, opp_hp, opp_max, intel["name"])

        while True:
            target_label = f" [Target: {current_target}]" if current_target != 21 else ""
            print(f"\n ─── Round {round_num} Menu ───{target_label}")
            print(" A. Analyze hand (get advice)")
            print(" D. Done — record round result")
            print(f" G. Toggle 'Go for 24' (currently: {'ON → target 24' if current_target == 24 else 'OFF → target 21'})")
            dead_label = f" ({sorted(dead_cards)})" if dead_cards else " (none)"
            print(f" X. Dead cards{dead_label}")
            print(" T. Trump card reference")
            print(" I. Opponent intel")
            print(" H. Round history")
            print(" S. HP status")
            print(" Q. Quit fight")

            action = input("\n Action: ").strip().upper()

            if action == "A":
                dead_cards = analyze_round(intel, player_hp, player_max, opp_hp, opp_max, current_target, dead_cards)

            elif action == "G":
                current_target = 24 if current_target == 21 else 21
                print(f" ★ Target set to {current_target}!")

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
                player_hp, opp_hp, entry = record_round_result(round_num, player_hp, opp_hp)
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

                # Round recorded and neither died → next round
                break

            elif action == "T":
                display_trumps_reference()
                input(" Press Enter to continue...")

            elif action == "I":
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
                print(" Invalid action. Use A/D/G/T/I/H/S/Q.")

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


def select_survival_plus_opponent(fight_num: int) -> dict:
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
    for i, opp in enumerate(pool):
        print(f" {i + 1}. {opp['name']} — {opp.get('desc', '')}")

    while True:
        choice = input(f"\n Select (1-{len(pool)}): ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(pool):
                return pool[idx]
            print(" Invalid selection.")
        except ValueError:
            print(" Enter a number.")


def run_mode(mode_key: str) -> None:
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

    print_header(f"{mode['name']}")
    print(f"\n {mode['rules']}")
    print(f"\n Starting HP: {player_hp}")
    print(f" Opponents: {total_opponents}")
    input("\n Press Enter to begin...")

    for idx in range(total_opponents):
        fight_num = idx + 1

        if player_hp <= 0:
            break

        print_header(f"{mode['name']} — OPPONENT {fight_num}/{total_opponents}")
        print(f" Your HP: {player_hp}/{player_max}")

        if mode_key == "3":
            # Survival+ — dynamic selection
            opp = select_survival_plus_opponent(fight_num)
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

        player_hp = fight_opponent(opp, player_hp, player_max)

        if player_hp <= 0:
            print_header("GAME OVER")
            print(f" Defeated by {opp['name']}.")
            print(f" Opponents beaten: {idx}/{total_opponents}")
            return

    if player_hp > 0:
        print_header(f"★ {mode['name']} COMPLETE! ★")
        print(f" All {total_opponents} opponents defeated!")
        print(f" Remaining HP: {player_hp}/{player_max}")

        if mode_key == "2":
            print(" UNLOCKED: Survival+ mode!")
        elif mode_key == "3":
            print(" UNLOCKED: 'Perfect Draw' trump card!")
            print(" TROPHY: Survival+ complete!")


def run_free_play() -> None:
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
            fight_opponent(opp, player_hp, player_max)
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
        if target not in (21, 24, 27):
            print(" Unsupported target. Use 21, 24, or 27.")
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
    print(" Constraint: at most 5 permanent trumps active at once.\n")

    try:
        used = int(input(" Trumps used this round so far: ").strip() or "0")
        active_perm = int(input(" Permanent trumps currently active (0-5): ").strip() or "0")
        non_perm_hand = int(input(" Non-permanent trumps in hand (estimate): ").strip() or "0")
        perm_hand = int(input(" Permanent trumps in hand (estimate): ").strip() or "0")

        active_perm = max(0, min(5, active_perm))
        need = max(0, 15 - used)
        slots_left = max(0, 5 - active_perm)
        immediate_capacity = non_perm_hand + min(perm_hand, slots_left)

        print(f"\n Need {need} more trump uses to reach 15.")
        print(f" Permanent slots left: {slots_left}/5")
        print(f" Immediate usable estimate: {immediate_capacity}")

        if need == 0:
            print(" Requirement met. Secure the round win now.")
            return

        if immediate_capacity < need:
            print(
                "\n You likely need additional cycling (Trump Switch/Trump Switch+) or extra draw generation."
            )
        else:
            print("\n You likely have enough cards to hit 15 this round.")

        print(
            "\n Recommended sequence:\n"
            " 1) Spend non-permanent effects first.\n"
            " 2) Fill permanent slots only when necessary.\n"
            " 3) Once count reaches 15, convert to a safe winning board."
        )

    except ValueError:
        print(" Invalid numeric input.")


def show_no_damage_blueprint() -> None:
    """Display strategy for no-damage Survival and Survival+ runs."""
    print_header("NO-DAMAGE BLUEPRINT")
    print(" Objectives:")
    print(f" - {CHALLENGE_GOALS['no_damage_survival']['name']}")
    print(f" - {CHALLENGE_GOALS['no_damage_survival_plus']['name']}\n")
    print(
        " Core policy:\n"
        " - Card count every round (1-11, one each).\n"
        " - Play for win or draw; if losing is forced, shield to avoid damage.\n"
        " - Save Destroy/Destroy+ for lethal enemy trumps.\n"
        " - Avoid unnecessary bet inflation until kill turns."
    )
    print(
        "\n High-risk trump counters:\n"
        " - Curse / Black Magic lines: keep Return/Exchange ready.\n"
        " - Mind Shift variants: remove immediately when possible.\n"
        " - Dead Silence / Twenty-One Up turns: hold counter cards before committing."
    )
    print(
        "\n Run discipline:\n"
        " - For strict no-damage attempts, reset on first unavoidable damage.\n"
        " - Keep at least one emergency answer card for late opponents."
    )


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
        print("\n 1. Bust-Win Planner [PRIORITY]")
        print(" 2. 15-Trump Planner")
        print(" 3. No-Damage Blueprint")
        print(" 4. Internet Sources")
        print(" Q. Back")

        choice = input("\n Select: ").strip().upper()
        if choice == "1":
            run_bust_win_planner()
            input("\n Press Enter to continue...")
        elif choice == "2":
            run_fifteen_trump_planner()
            input("\n Press Enter to continue...")
        elif choice == "3":
            show_no_damage_blueprint()
            input("\n Press Enter to continue...")
        elif choice == "4":
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
    while True:
        print_header("RESIDENT EVIL 7: 21 — CARD GAME SOLVER")
        print("\n SELECT MODE:\n")
        print(" 1. Normal 21 (vs. Lucas — tutorial)")
        print(" 2. Survival 21 (5-opponent gauntlet)")
        print(" 3. Survival+ 21 (10-opponent hard gauntlet)")
        print(" 4. Free Play (pick any opponent)")
        print(" C. Challenge Lab (priority unlock planner)")
        print()
        print(" R. Trump Card Reference")
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
        elif choice in ("1", "2", "3"):
            run_mode(choice)
            input("\n Press Enter to return to menu...")
        elif choice == "4":
            run_free_play()
            input("\n Press Enter to return to menu...")
        else:
            print(" Invalid selection.")


if __name__ == "__main__":
    main()
