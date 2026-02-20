# Resident Evil 7: 21 — Card Game Solver

A terminal-based companion tool for the **21** card game from the *Resident Evil 7: Biohazard — Banned Footage Vol. 2* DLC. Tracks cards, computes odds, models opponent AI, and gives strategic advice in real time as you play.

## Core Functionality

This solver has been upgraded from a basic probability calculator into a highly predictive, state-aware companion application.

* **Deck Tracking Warning:** The shared deck contains exactly 11 cards (1–11) with absolutely no duplicates. **It is absolutely vital that you meticulously input every single card drawn, returned, or exchanged into the terminal prompt.** If you fail to input an opponent's card draw, the entire combinatorial matrix becomes corrupted and the mathematical integrity of the system is compromised.
* **Predictive AI Modeling:** The solver does not treat all AI as identical. At the start of a sequence, you will be prompted for the visual descriptors of the current AI you are facing (sack markings, variant cuts/hands/wires). This profile is stored in a persistent memory object that actively dictates the heuristic weighting applied to all trump card suggestions.
* **Dynamic Trump Recommendation Engine:** The solver utilizes a 4-tier priority engine that scores your held cards based on utility weight, the active opponent profile, and your position in the gauntlet. It prioritizes long-term resource conservation — for example, automatically outputting "SAVE DESTROY CARDS FOR FIGHT #10" when facing non-boss opponents in Survival+. **Smart suppression:** Trump advice only appears when it matters — when you're busted, losing, at low HP, fighting a boss, or facing enemy trump threats. Comfortable early-game wins against weak opponents get no unnecessary clutter.
* **Standard vs Special Trump Display:** Opponent profiles now separate standard trumps (One-Up, Shield — common cards any opponent uses) from special trumps (Desire, Mind Shift, Curse — unique dangerous abilities). Special trumps are highlighted in yellow in the target info panel.
* **Run Restart Suggestion:** After each fight in the first half of a gauntlet, the solver evaluates your HP-to-remaining-fights ratio. If survival probability is critically low (e.g., 2 HP with 6 fights left), it recommends restarting the run rather than grinding out a doomed attempt.
* **Mr. Big Head Priority:** In Survival+, if Harvest is not yet unlocked, Mr. Big Head is flagged as a priority target when he appears. Defeating him twice unlocks Harvest — one of the strongest trump cards in the game.
* **Interrupt-Driven State Recalculation:** When the opponent plays a trump card mid-round that alters the board (card removal, bet changes, exchanges, Dead Silence, Curse, etc.), press **I** to declare the interrupt. The solver updates the game state and you can immediately re-analyze with corrected probabilities.
* **Failed Draw Deduction:** When playing a numbered draw card (2–7 Card) and it fails (card not in deck), the solver automatically deduces that the opponent holds that card as their hidden face-down card. This transitions the opponent from a probabilistic range to a mathematical certainty.
* **Utility Weight System:** Every trump card has an internal `utility_weight` (0–100) and `effect_type` classification. Weights are **never shown to the user** — they drive sorting and prioritization silently. When multiple cards solve the same problem, the cheapest is suggested first. High-weight cards (≥60) get "SAVE for bosses" warnings on non-boss fights.
* **Auto Bet & Target Tracking:** Bets and target values update automatically when you play trump cards (P) or declare enemy interrupts (I). One-Up, Two-Up, Shield, Perfect Draw+, Desire, Shield Assault — all tracked live. Go For cards auto-change the target. Everything resets between rounds since table cards clear.
* **Silent Challenge Tracker:** The manual configuration menus for challenges have been removed. The solver operates as a silent background daemon that automatically identifies non-standard board states — such as achieving a victory while holding a busted hand — and proactively flashes instructions to secure achievements.

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
3.  Identify your opponent when prompted.
4.  Follow the main fight loop:
    * **A. Analyze hand:** Enter your cards and visible opponent cards. Get full probability breakdown + strategic advice.
    * **I. Interrupt:** Enemy played a trump card? Press I immediately to declare what happened (card added/removed, bet change, swap, Dead Silence, Curse, etc.) — bets and target update automatically.
    * **P. Play a trump card:** Select from your hand. Bets and target auto-update when you play bet cards (One-Up, Two-Up, Shield, etc.) or Go For cards. For numbered draw cards (2–7), a failed draw triggers hidden card deduction.
    * **W. Edit trump hand:** Update your current inventory after draws, discards, or enemy effects.
    * **D. Done:** Conclude the round and input the winner/damage. Target and bets reset automatically for the next round.
    * **O. Opponent intel:** View enemy AI profile, trumps, and tips.

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

The `utility_weight` values drive the solver's internal prioritization — lower-weight cards are burned first, higher-weight cards are preserved for bosses. These values are never displayed to the user.

## Challenge Tracking

The solver automatically monitors for these achievement conditions during play:

| Challenge | Reward | Auto-Detection |
|-----------|--------|----------------|
| Win while bust | Starting Trump +1 | Gated: only shown when HP > 2, stay win% < 65%, and odds ≥ 15% |
| Use 15 trumps in 1 round | Trump Switch+ | Interactive planner with Survival vs S+ analysis and live tracker |
| Hit 21 three times in a row | Go for 27 | Monitors consecutive perfect scores |
| Beat Survival without damage | Ultimate Draw | Auto-tracked in Survival mode — detects damage, offers restart |
| Beat Survival+ without damage | Grand Reward | Cosmetic only — not tracked |

### No-Damage Survival (Built-In)

No-damage tracking is **automatic** when playing Survival mode. The solver compares HP before and after each fight — the instant you take damage, it flags the challenge as failed and offers to restart the run. If you complete all 5 fights at full HP, it congratulates you and confirms the Ultimate Draw unlock. The Challenge Lab still has a strategy guide with per-fight advice and restart decision trees.

### 15-Trump Round (Challenge Lab)

Research confirms this challenge is **very difficult in Survival** (5 HP opponents = short fights) but **recommended in Survival+** (10 HP opponents = longer fights with more cycling). Requires Harvest + Trump Switch. The planner includes a live tracker with projected capacity calculations.

## Running

```bash
python3 re7_helper.py
```

Requires Python 3.6+. No external dependencies.
