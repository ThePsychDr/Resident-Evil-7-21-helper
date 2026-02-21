
#This project’s public build is paused.
Using REFramework, I can deduce the actual 21 game rules (trumps, damage, AI behavior) and bring the simulator extremely close to the in-game logic.

What I won’t ship publicly is a solution that requires tracing/instrumentation to reconstruct RNG state or seeds—because that only guarantees perfect prediction on PC, and this tool was meant to help console players.

If it turns out the game uses a fixed or in-game-deducible seed (something you can determine without special tools), I’ll revisit a public release. Otherwise, the tool can still be useful as a rules-accurate simulator + probability/strategy solver rather than a perfect “next card” predictor.

If anyone wants to continue and publish their own build using my work as a base, please give credit.

Its pretty accurate already from using internet sources and in game testing but still has some issues

# Resident Evil 7: 21 — Card Game Solver

A terminal-based companion tool for the **21** card game from the *Resident Evil 7: Biohazard — Banned Footage Vol. 2* DLC. Tracks cards, computes odds, models opponent AI, and gives strategic advice in real time as you play.

## Core Functionality

This solver has been upgraded from a basic probability calculator into a highly predictive, state-aware companion application.

* **Deck Tracking Warning:** The shared deck contains exactly 11 cards (1–11) with absolutely no duplicates. **It is absolutely vital that you meticulously input every single card drawn, returned, or exchanged into the terminal prompt.** If you fail to input an opponent's card draw, the entire combinatorial matrix becomes corrupted and the mathematical integrity of the system is compromised.
* **Predictive AI Modeling:** The solver does not treat all AI as identical. At the start of a sequence, you will be prompted for the visual descriptors of the current AI you are facing (sack markings, variant cuts/hands/wires). This profile is stored in a persistent memory object that actively dictates the heuristic weighting applied to all trump card suggestions.
* **Dynamic Trump Recommendation Engine:** The solver utilizes a 4-tier priority engine that scores your held cards based on utility weight, the active opponent profile, and your position in the gauntlet. It prioritizes long-term resource conservation — for example, automatically outputting "SAVE DESTROY CARDS FOR FIGHT #10" when facing non-boss opponents in Survival+. **Smart suppression:** Trump advice only appears when it matters — when you're busted, losing, at low HP, fighting a boss, or facing enemy trump threats. Comfortable early-game wins against weak opponents get no unnecessary clutter.
* **Standard vs Special Trump Display:** Opponent profiles now separate standard trumps (One-Up, Shield — common cards any opponent uses) from special trumps (Desire, Mind Shift, Curse — unique dangerous abilities). Special trumps are highlighted in the target info panel.
* **Hand Memory:** The solver remembers your full hand (face-down card + visible cards) and opponent's visible cards between re-analyzes within the same round. On re-analyze, it shows remembered state and lets you add new cards (`v 3` to add your visible card, `o 5` to add opponent's card) or reset (`r`). Face-down card is locked once set — only a trump card effect can change it.
* **Run Restart Suggestion:** After each fight in the first half of a gauntlet, the solver evaluates your HP-to-remaining-fights ratio. If survival probability is critically low (e.g., 2 HP with 6 fights left), it recommends restarting the run rather than grinding out a doomed attempt.
* **Mr. Big Head Priority:** In Survival+, if Harvest is not yet unlocked, Mr. Big Head is flagged as a priority target when he appears. Defeating him twice unlocks Harvest — one of the strongest trump cards in the game.
* **No-Damage Tracking:** Automatically tracks damage across a Survival run. The instant you take damage, it flags the challenge as failed and offers to restart. Completing all 5 fights at full HP confirms the Ultimate Draw unlock.
* **Challenge Integration:** All challenges (bust-win, no-damage, 15 trump cards, Big Head priority) are tracked through normal gameplay — no separate Challenge Lab menu. Bust-win suggestions are gated: only shown when the challenge is incomplete, HP > 2, you're not winning comfortably, and it's not round 1 at full HP.
* **Opponent-Specific Interrupt System:** When the opponent plays a trump card mid-round, press **I** and the solver shows that specific opponent's known trump cards. Select which one they played and the solver walks you through the effects step by step — updating bets, target, hand memory, and dead cards automatically. No more guessing which category an effect falls into.
* **Failed Draw Deduction:** When playing a numbered draw card (2–7 Card) and it fails (card not in deck), the solver automatically deduces that the opponent holds that card as their hidden face-down card. This transitions the opponent from a probabilistic range to a mathematical certainty.
* **Utility Weight System:** Every trump card has an internal `utility_weight` (0–100) and `effect_type` classification. Weights are **never shown to the user** — they drive sorting and prioritization silently. When multiple cards solve the same problem, the cheapest is suggested first. High-weight cards (≥60) get "SAVE for bosses" warnings on non-boss fights.
* **Auto Bet & Target Tracking:** Bets and target values update automatically when you play trump cards (P) or declare enemy interrupts (I). One-Up, Two-Up, Shield, Perfect Draw+, Desire, Shield Assault — all tracked live. Go For cards auto-change the target. Everything resets between rounds since table cards clear.
* **Silent Challenge Tracker:** All challenges are integrated into normal gameplay — no separate menu required. The solver automatically detects challenge opportunities (bust-win, no-damage, 15 trumps) and provides contextual advice only when conditions are right.

## The Lucas Tutorial (Normal Mode) Restrictions

**CRITICAL DISCLAIMER:** Standard algorithmic advice is intentionally suspended during the final "Saw" round of the tutorial match against Lucas Baker.

This is due to the game's hard-coded narrative cheating. Lucas will inevitably play 'Desperation' (permanently locking all card draws, setting bets to 100) and 'Perfect Draw' (guaranteeing himself a perfect 21). Standard probability logic or target manipulation cannot overcome this scripted sequence.

**To survive:** You must hold the **"Love Your Enemy"** trump card. When the solver detects this round (Normal mode, Round 3), it suspends all calculations and outputs explicit instructions to use Love Your Enemy, which forces Lucas to draw past 21 and bust.

## Supported Game Modes

| Mode | Opponents | Your HP | Opponent HP | Mechanic |
|------|-----------|---------|-------------|----------|
| **Normal 21** | Lucas (1 match, 3 rounds) | 10 | 10 | Tutorial — fingers, shock, saw |
| **Survival** | 5 Hoffmans | 5 (carries over) | 5 each | Finger-chopping |
| **Survival+** | 10 Hoffmans | 10 (carries over) | 10 each | Electric rig |

### Survival+ Opponent Structure

Opponents 1–4 and 6–9 are drawn randomly from a pool of variant types. The solver will ask you to identify them by their sack markings (Tally Marks, Bloody Handprints, Barbed Wire, Mr. Big Head) and then by their specific sub-variant (e.g., 2 cuts vs. 3 cuts).

Two fights are always fixed:
* **Fight #5** — Molded Hoffman (mid-boss). Uses Curse, Black Magic, Conjure.
* **Fight #10** — Undead Hoffman (final boss). Uses Dead Silence, Oblivion, Ultimate Draw. Can chain multiple special trumps per round.

### Gauntlet Resource Management

The solver tracks your position in the gauntlet (`fight_num`) and automatically:
- **Fights 1–4:** Advises saving Destroy cards for Molded Hoffman (fight #5)
- **Fights 6–9:** Urgently advises saving ALL Destroy cards for Undead Hoffman (fight #10)
- **Boss fights:** Activates opponent-specific counter-strategies

## How to Use It During a Game

1.  Run the script: `python3 re7_helper.py`
2.  Select your mode (Normal, Survival, or Survival+).
3.  Identify your opponent when prompted (sack markings, variant).
4.  Enter your starting trump cards — the solver asks immediately.
5.  Follow the main fight loop:
    * **A. Analyze hand:** Enter your face-down card (locked once set), visible cards, and opponent's visible cards. The solver remembers your full hand between re-analyzes — on subsequent calls, add new cards with `v 3` (your card) or `o 5` (opponent card), or `r` to reset.
    * **I. Interrupt:** Enemy played a trump? Press I — the solver shows the opponent's known trump list and walks you through the effects step by step. Bets, target, and hand memory update automatically.
    * **P. Play a trump card:** Select from your hand. Bets and target auto-update for bet cards and Go For cards. Failed numbered draws (2–7 Card) trigger hidden card deduction.
    * **W. Edit trump hand:** Update your inventory after draws, discards, or enemy effects.
    * **D. Done:** Record the round result (win/loss/tie/void). Cancelling with option 5 keeps you in the current round. Target and bets reset for the next round.
    * **O. Opponent intel:** View enemy AI profile with standard and special trumps.

## Trump Card Database

The solver categorizes and tracks all 37+ trump cards across 7 types:

| Type | Examples | Weight Range |
|------|----------|-------------|
| Bet Modifier | One-Up, Two-Up, Two-Up+ | 10–50 |
| Draw Forcer | Perfect Draw, Ultimate Draw, 2-7 Card | 15–100 |
| Board Wipe | Destroy, Destroy+, Destroy++ | 60–100 |
| Target Modifier | Go for 17/24/27 | 30–40 |
| Defensive | Shield, Shield+ | 10–20 |
| Special | Trump Switch, Harvest | 20–50 |
| Attack (enemy-only) | Curse, Dead Silence, Desire | 0 (not player-obtainable) |

The `utility_weight` values drive the solver's internal prioritization — lower-weight cards are burned first, higher-weight cards are preserved for bosses. These values are never displayed to the user. Trump card advice only appears when necessary — boss fights, losing positions, or challenge opportunities.

## Challenge Tracking

All challenges are integrated into normal gameplay. There is no separate Challenge Lab menu — the solver detects opportunities and warns you automatically.

| Challenge | Reward | How It Works |
|-----------|--------|--------------|
| Win while bust | Starting Trump +1 | Shown only when: challenge incomplete, HP > 2, not winning comfortably, not early-game full HP, and bust win% ≥ 20% |
| Use 15+ trumps in 1 round | Trump Switch+ | Very difficult in Survival (short fights), recommended in Survival+ (10 HP opponents). Requires Harvest + Trump Switch |
| Hit 21 three times in a row | Go for 27 | Monitors consecutive perfect scores |
| Beat Survival without damage | Ultimate Draw | Auto-tracked in Survival mode. Detects any damage, offers immediate restart. Congratulates on completion |
| Beat Survival+ without damage | Grand Reward | Cosmetic only — not tracked |
| Defeat Mr. Big Head | Harvest | Auto-flagged as priority target in Survival+ when Harvest is not yet unlocked |

### No-Damage Survival

No-damage tracking is **automatic** when playing Survival mode. The solver compares HP before and after each fight — the instant you take damage, it flags the challenge as failed and offers to restart the run. Complete all 5 fights at full HP to unlock Ultimate Draw.

### 15-Trump Round

This challenge is **very difficult in Survival** (5 HP opponents = 3-5 round fights) but **recommended in Survival+** (10 HP opponents = 5-10 rounds, more time to cycle). Required setup: Harvest (every trump played draws a replacement) + Trump Switch/Switch+ (discard old, draw new).

## Running

```bash
python3 re7_helper.py
```

Requires Python 3.6+. No external dependencies.
