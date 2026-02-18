# BETA/ WIP


# Resident Evil 7: 21 — Card Game Solver

A terminal-based companion tool for the **21** card game from the *Resident Evil 7: Biohazard — Banned Footage Vol. 2* DLC. Tracks cards, computes odds, models opponent AI, and gives strategic advice in real time as you play.

## Requirements

- Python 3.6+
- No external dependencies — runs with the standard library only

## Quick Start

```bash
python3 re7_helper.py
```

## What It Does

The 21 minigame is a high-stakes blackjack variant where you draw from a shared deck of cards numbered 1–11 (no duplicates). Losing means torture. This solver helps you make optimal decisions by:

- **Tracking the deck** — Shows which of the 11 cards are still available vs. already played
- **Computing draw odds** — Exact probability of safe draws, busts, and perfect 21s
- **Modeling opponent AI** — Simulates what the opponent will do based on their stay threshold and adjusts when "Go for 24" shifts the target
- **Comparing STAY vs. HIT** — Full probability breakdown of win/tie/loss for both options
- **Opponent-specific warnings** — Alerts for dangerous trump cards like Curse, Dead Silence, Black Magic, and Twenty-One Up based on who you're fighting
- **HP-aware advice** — Adjusts risk tolerance based on your remaining health

## Supported Game Modes

| Mode | Opponents | Your HP | Opponent HP | Mechanic |
|------|-----------|---------|-------------|----------|
| **Normal 21** | Lucas (1 match, 3 rounds) | 10 | 10 | Tutorial — fingers, shock, saw |
| **Survival** | 5 Hoffmans | 5 (carries over) | 5 each | Finger-chopping |
| **Survival+** | 10 Hoffmans | 10 (carries over) | 10 each | Electric rig |

### Survival+ Opponent Structure

Opponents 1–4 and 6–9 are drawn randomly from a pool of variant types. Two fights are always fixed:

- **Fight #5** — Molded Hoffman (mid-boss). Uses Curse, Black Magic, and Conjure.
- **Fight #10** — Undead Hoffman (final boss). Uses Dead Silence, Oblivion, and tons of Perfect Draws.
- **Mr. Big Head** — Rare random encounter with the Escape trump card.

Since the order is random, the tool asks you to identify each opponent by the markings on their sack (tally marks, bloody handprints, barbed wire, or cartoon mask).

## How to Use It During a Game

### 1. Select your mode from the main menu

```
 1. Normal 21 (vs. Lucas — tutorial)
 2. Survival 21 (5-opponent gauntlet)
 3. Survival+ 21 (10-opponent hard gauntlet)
 4. Free Play (pick any opponent)
 C. Challenge Lab (priority unlock planner)
```

### 2. Fight loop

Each fight runs a loop of rounds. Within each round, the menu offers:

| Key | Action |
|-----|--------|
| **A** | **Analyze hand** — Enter your cards, opponent's visible cards, and dead cards. The solver computes everything. |
| **D** | **Done** — Record the round result (win/loss/tie/void) and update HP. |
| **G** | **Toggle "Go for 24"** — Flips the target between 21 and 24. Persists across rounds so you don't have to re-enter it. |
| **T** | Trump card reference |
| **I** | Opponent intel (trumps, AI type, tips) |
| **H** | Round history |
| **S** | HP status bars |
| **Q** | Quit fight |

### 3. Analyzing a hand

When you press **A**, you'll enter:

1. Your card values (e.g., `10 6`)
2. Opponent's visible cards (e.g., `8`)
3. Dead/removed cards if any
4. Opponent's draw behavior (already stayed, normal AI, or forced hit)

The solver then shows:

- **Deck tracker** — Color-coded grid of which cards (1–11) are in or out
- **Draw table** — Every possible card you could draw and the resulting total
- **STAY vs. HIT probabilities** — Full win/tie/loss breakdown for both choices
- **Action recommendation** — HIT, STAY, or USE TRUMP with reasoning
- **Opponent-specific warnings** — Curse danger, Dead Silence risk, instant-kill alerts, etc.

### Example Output

```
 YOUR TOTAL: 16 (cards: [10, 6])
 OPPONENT VISIBLE: 8 (cards: [8])
 TARGET: 21
 SAFE HIT CHANCE: 71% (5/7 cards)

 If you draw:
  Card  1 → total 17 ✓
  Card  2 → total 18 ✓
  Card  3 → total 19 ✓
  Card  4 → total 20 ✓
  Card  5 → total 21 ✓ ★ PERFECT!
  Card  9 → total 25 ✖ BUST
  Card 11 → total 27 ✖ BUST

 MODEL: Opponent follows AI stay threshold (17+).
 If YOU STAY now -> Win 25.0% | Tie 8.3% | Lose 66.7%.
 If YOU HIT now  -> Win 60.2% | Tie 5.1% | Lose 34.7%.
 ACTION: HIT — model gives +35.2% win chance over staying.
```

## "Go for 24" — How It Works

"Go for 24" is a trump card that changes the round target from 21 to 24. It stays on the table until removed. The solver handles this in two ways:

1. **Your odds update** — Bust threshold shifts to 24, so cards that would bust you at 21 become safe draws.
2. **Opponent AI adjusts** — The opponent's stay threshold increases by the difference (e.g., an opponent who normally stays at 17 will stay at 20 when the target is 24). This prevents the solver from assuming the opponent will stand on a losing hand like 18 when the real target is 24.

Toggle it with **G** in the fight menu. It persists until you toggle it off.

## Challenge Lab

Press **C** from the main menu to access specialized tools for DLC challenges:

- **Bust-Win Planner** — Computes the best way to win a round while busted (both sides over target, closest wins). Shows odds for staying, forcing a random draw, or forcing the highest draw on the opponent.
- **15-Trump Planner** — Tracks progress toward using 15 trump cards in a single round for the Trump Switch+ unlock.
- **No-Damage Blueprint** — Strategy guide for completing Survival and Survival+ without taking any damage.

## Opponent Database

Every opponent variant is catalogued with:

- **AI type** and stay threshold
- **Unique trump cards** and what they actually do
- **Counter-strategies** for each dangerous trump
- **Commonly played** standard trumps

The data is sourced from the [RE Wiki](https://residentevil.fandom.com/wiki/21), [RE Wiki — Hoffman](https://residentevil.fandom.com/wiki/Hoffman), community guides, and in-game testing.

## File Structure

Single file — `re7_helper.py`. No config files, no saves, no dependencies. Just run it.

## Tips

- **Card count every round.** The deck is only 11 cards with no duplicates. Knowing what's left is the single biggest advantage you have.
- **Save Destroy cards** for the most dangerous opponent trumps (Dead Silence, Black Magic, Curse, Escape).
- **Don't hoard trumps** against Bloody Handprints Hoffman — his Desire card punishes you for holding them.
- **The solver is a guide, not gospel.** It models the opponent as a probability distribution, but the actual game AI can behave unpredictably, especially in Survival+.
