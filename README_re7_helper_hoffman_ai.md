# re7_helper_hoffman_ai.py — README / Changelog

This file is a fork/extension of your `re7_helper (3).py` that adds a **Survival / Survival+ enemy AI “Hoffman thinkset” prediction layer** on top of your existing CardGame solver + Trump timing logic.

It does **not** “reverse the EXE AI” — it’s a **data-driven approximation** based on:
- the Hoffman module filenames / strings you extracted (Attacker / Defence / Tricky / Molded / LassBoss / Rare), and
- your existing `TrumpConditionState.trump_fire_likelihood()` timing engine.

---

## What’s new (high level)

### 1) Hoffman AI rule-table layer (new)
A new section is added:

**`HOFFMAN SURVIVAL / SURVIVAL+ AI (RULE TABLE LAYER)`**

It introduces:
- `HOFFMAN_TRUMP_ALIASES`  
  Normalizes plus variants for matching (e.g. `Perfect Draw+` → `Perfect Draw`).

- `_norm_trump(name)`  
  Applies the alias map.

- `infer_hoffman_thinkset(intel)`  
  Best-effort mapping from the opponent’s trump kit/name into a thinkset:
  - `LassBoss` if it sees signature trumps like `Dead Silence` or `Oblivion`
  - `Rare` if the kit is basically just `Escape`
  - `Molded` if it sees `Curse / Black Magic / Conjure`
  - `Defence` if it sees `Shield Assault`
  - `Tricky` if it sees `Mind Shift / Desire / Happiness`
  - otherwise defaults to `Attacker`

- `_level_to_score(level)`  
  Converts your timing engine’s levels (`VERY HIGH/HIGH/MEDIUM/LOW/NONE`) into numeric scores.

- `predict_enemy_trump(intel, condition_state) -> (pick, confidence, reason)`  
  This is the “brain”:
  1. Makes a **thinkset-based pick** (fast heuristics based on your current round totals + trump counts)
  2. Computes the **best timing-engine pick** using `trump_fire_likelihood()`
  3. Combines them:
     - If the thinkset pick also looks plausible by timing, it boosts it
     - Otherwise it reports the timing pick but mentions what the thinkset suggested

**Key point:** This is designed so you can refine it later with exact node params from 010 / BHVT.

---

### 2) New advice line in the UI output
In your advice output, it now adds a line like:

`ENEMY AI PREDICT [MEDIUM]: likely plays 'Curse' next — Molded: banker weak (16) vs you (18) | Curse [LOW]: thinkset-driven`

This is appended **after** your existing priority warnings / timing warnings.

---

### 3) Condition-state fields kept “fresh” each round
In the main Survival loop, the helper now updates additional fields used by the prediction layer:

- `round`
- `kill_count` (approx proxy for Survival+ progression)
- `banker_item_num` (approx from enemy trump kit size)
- `player_item_num` (your current trump hand size)

This makes the prediction respond as the fight evolves.

---

### 4) Trump-hand editor: optional lock filtering
`edit_trump_hand()` now optionally accepts `available_trumps` and will:
- show locked trumps as a “🔒 Locked” list
- hide truly locked trumps from the add menu (unless you pass `available_trumps=None`)

This is quality-of-life so your run input matches your unlock state.

---

## What did NOT change
- Your core solver math logic and round analysis flow remain the same.
- The timing engine (`TrumpConditionState`) is still the authority for “when a trump is likely.”
- The Hoffman layer doesn’t attempt to model hidden card knowledge, deck knowledge beyond remaining values, or EXE-only heuristics.

---

## How to use

### Run it like your previous helper
Use the new file exactly as you ran the old one:

- pick opponent / mode
- enter your hand, trumps, totals
- the assistant prints round advice
- you’ll now also get an **ENEMY AI PREDICT** line when enough state exists

### Make the prediction smarter (recommended knobs)
These are the intended tuning points:

1. **Hard-map thinksets per opponent**
   In `infer_hoffman_thinkset()`, you can replace heuristics with a dictionary like:
   ```python
   THINKSET_BY_NAME = {"Hoffman 3": "Tricky_p", "Molded A": "Molded", ...}
   ```
   Use the heuristics as fallback.

2. **Replace placeholder triggers with exact node params**
   The heuristics use simple bands (like 10–18 for Perfect Draw).
   Once you inspect nodes in 010/BHVT and find exact compare values, swap those in.

3. **Improve “player_item_num / banker_item_num”**
   Right now `banker_item_num` is approximated from the opponent’s kit size.
   If you track actual **remaining enemy trumps** mid-match, pass that count instead.

---

## Known limitations (important)
- Some Survival/S+ behaviors are likely EXE-driven or influenced by hidden state, so this won’t be 100% identical.
- If the enemy uses trumps not present in `intel['trumps'] + intel['standard_trumps']`, the predictor can’t pick them.
- The prediction is designed to be **useful**, not “prove the AI.”

---

## Mini changelog (diff vs `re7_helper (3).py`)

### Added
- New Hoffman rule-table section:
  - `HOFFMAN_TRUMP_ALIASES`
  - `_norm_trump()`
  - `infer_hoffman_thinkset()`
  - `_level_to_score()`
  - `predict_enemy_trump()`

### Modified
- Advice generation now appends:
  - `ENEMY AI PREDICT [...] ...` when `condition_state` exists
- Survival loop now updates condition fields each round:
  - `round`, `kill_count`, `banker_item_num`, `player_item_num`
- `edit_trump_hand()` optionally filters locked trumps using `available_trumps`

---

## If you want a “next step”
If you export/inspect **one** Hoffman module with concrete node params (e.g., `8_lassboss.fsm.16`), we can replace the heuristic bands with exact thresholds and the predictor will become scary accurate.

