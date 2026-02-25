# Resident Evil 7: 21 — Card Game Solver

A terminal-based companion tool for the **21** card game from *Resident Evil 7: Biohazard — Banned Footage Vol. 2*.  
It tracks the round state, computes odds, models opponent behavior, and gives practical trump-card advice in real time.

---

## What’s new in the latest build

- **“Remove” is now modeled consistently everywhere as a *dead-card* effect.**  
  **Remove takes a face-up number card out of play for the rest of the round** (it becomes a *dead card*). That description is synced in both the Python `TRUMPS` database and the Hoffman rule table JSON.

- **Enemy “Remove” interrupt is now state-aware.**  
  If the opponent plays **Remove**, the interrupt flow updates your round state by removing the affected **face-up number card** from your table and adding it to **dead cards**.

- **Dead-card tracking is explicit (and used by the odds engine).**  
  The solver keeps a `dead_cards` list for values that are no longer drawable this round (see “Dead cards” below). This directly changes remaining-deck odds.

- **Hoffman rule table JSON stayed in sync with newly-found cards + corrected descriptions.**  
  The `hoffman_rule_table.json` file includes a trump catalog (names + categories + effect types + weights) and Hoffman decision rules, so you can tweak AI logic without touching code.

---

## Core functionality

- **Deck tracking (1–11, no duplicates):** every round has exactly **11 cards (1–11)**. If you miss inputs (especially enemy draws/returns), odds will drift.
- **Hand memory:** remembers your face-down + visible cards and opponent visible cards between re-analyzes within a round.
- **Opponent-specific AI modeling:** different Hoffman variants have different trump kits and behavior notes.
- **Dynamic trump recommendations:** ranks your held trumps by utility + context (boss fight, low HP, busted, etc.) and avoids clutter in easy spots.
- **Interrupt system:** when the opponent plays a trump mid-round, press **I** to apply the effect step-by-step and keep state consistent (bets, target, hand memory, dead cards).
- **Gauntlet resource awareness (Survival+):** warns you when to conserve high-value trumps for Fight #5 / Fight #10.
- **Challenge-aware suggestions:** (bust-win, no-damage, etc.) are integrated into normal play and only appear when conditions make sense.

---

## Dead cards (important)

In the real minigame, the round deck is “1–11 once each,” and most effects are draws/returns/swaps.

In **this solver**, a **dead card** means:  
> a card value that is treated as **not available to be drawn again this round**.

Dead cards can happen when:

- **Remove** is used (solver model): the chosen face-up number card is **removed from play for the rest of the round**.
- **Forced draws** you can fully observe and confirm (e.g., enemy Perfect/Ultimate Draw) — once you confirm the drawn value, it can be treated as “accounted for” in remaining-deck math.
- **Curse** (solver tracking): if the opponent forces a “highest remaining card” draw and you confirm it, that value is marked accounted for.

Dead cards reset every round.

---

## Supported game modes

| Mode | Opponents | Your HP | Opponent HP | Mechanic |
|------|-----------|---------|-------------|----------|
| **Normal 21** | Lucas (1 match, 3 rounds) | 10 | 10 | Tutorial — fingers, shock, saw |
| **Survival** | 5 Hoffmans | 5 (carries over) | 5 each | Finger-chopping |
| **Survival+** | 10 Hoffmans | 10 (carries over) | 10 each | Electric rig |

### Survival+ structure

- Fights **1–4** and **6–9** are drawn from variant pools (Tally Marks, Bloody Handprints, Barbed Wire, Mr. Big Head).
- Two fights are fixed:
  - **Fight #5 — Molded Hoffman (mid-boss)**: nasty specials (Curse / Conjure / etc.)
  - **Fight #10 — Undead Hoffman (final boss)**: Dead Silence / Oblivion / Ultimate Draw chains

---

## The Lucas tutorial (Normal mode) restriction

**Important:** standard algorithmic advice is intentionally suspended during the final “Saw” round vs Lucas.

Lucas is scripted to use **Desperation** (locks draws / massive bet) and **Perfect Draw** (guarantees 21).  
The solver will switch into “scripted survival instructions” mode for that round.

---

## How to use it during a game

1. Run the script:
   ```bash
   python3 re7_helper.py
   ```
2. Pick mode (Normal / Survival / Survival+).
3. Identify your opponent when prompted (variant markers).
4. Enter your starting trump hand (the solver asks up front).
5. During the fight loop:
   - **A — Analyze:** input/confirm face-down + visible cards + opponent visible cards.
   - **H — You drew / O — Opponent drew:** quick state updates.
   - **I — Interrupt:** enemy played a trump → apply effect step-by-step (including **Remove** → dead cards).
   - **P — Play a trump:** apply your trump effects; target/bets update where applicable.
   - **W — Edit trump hand:** fix inventory after draws/discards/steals.
   - **D — Done:** record the round result (win/loss/tie/void) and advance.

---

## Trump card database

The solver includes a trump database with:

- **Category** (Bet / Cards / Target / Defense / Switch / Special / Enemy-only, etc.)
- **Effect type** (Bet modifier, draw forcer, board wipe, target modifier, control, etc.)
- **Utility weight** used internally for prioritization (not shown in UI)

Notable tracked effects include:

- **Go For** targets (**17 / 24 / 27**)  
- **Numbered draws** (**2–7 Card**) with “failed draw ⇒ hidden-card deduction” logic  
- **Two-Up+** return-to-deck tracking  
- **Dead Silence / Oblivion / Mind Shift / Escape** as interrupt-aware control trumps  
- **Remove** as **dead-card removal** in this solver model

---

## Hoffman rule table (JSON)

`hoffman_rule_table.json` is the “rules engine” side:

- contains a Hoffman decision list (priority-ordered rules)
- contains the trump catalog used for UI descriptions and classification
- keeps card descriptions consistent with what the solver actually does (especially important for interrupts)

If you edit the JSON, keep in mind: **rules are evaluated top-to-bottom** and the first match wins.

---

## Requirements

- Python **3.6+**
- No external dependencies

