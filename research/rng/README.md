# Phase H — RNG characterization (private research)

Answers the README open question: **can the 21 minigame deck/trump order be predicted without PC instrumentation?**

This folder is **research-only**. Nothing here ships perfect next-card prediction to console players. It provides:

1. **Capture** — REFramework Lua script hooks `CardGameMaster` + Unity `Random`
2. **Analyze** — Python tools score whether shuffles are session-fixed, round-derived, or opaque
3. **Recover** — Brute-force / state-step checks against Unity's PRNG (PC validation only)

## Quick start (PC + RE7 + REFramework)

1. Copy `reframework/autorun/re7_21_rng_trace.lua` into your RE7 install:
   ```
   <RE7>/reframework/autorun/re7_21_rng_trace.lua
   ```
2. Launch 21 (Normal or Survival). Open REFramework overlay → confirm `[RE7-21 RNG]` lines.
3. Play rounds. Press **F9** for manual snapshots; round transitions auto-log when detected.
4. Logs land in `<RE7>/reframework/data/re7_21_rng_trace.jsonl`
5. Copy the log into `research/captures/` (gitignored) and analyze:

   ```bash
   python3 research/rng/analyze_rng_log.py research/captures/my_session.jsonl
   python3 research/rng/analyze_rng_log.py research/captures/my_session.jsonl --recover-seed
   ```

## Verdict meanings

| Verdict | Meaning | Public solver implication |
|---------|---------|---------------------------|
| `DEDUCIBLE` | Shuffle matches a function of observable state (round index, cards seen, etc.) | Could revisit public perfect prediction |
| `SESSION_FIXED` | One Unity seed drives all rounds until mode restart | PC-only seed capture; console stays probabilistic |
| `OPAQUE` | No pattern across sessions/rounds; seed recovery fails | Keep rules-accurate simulator only |

## RE targets (from existing solver notes)

| Type | What to trace |
|------|----------------|
| `app.CardGameMaster` | `StockCardList`, shuffle/reshuffle, draw pop |
| `CardGameItemTable` | Trump pool + `RandomIndexList` deal order |
| `UnityEngine.Random` | `InitState`, `state`, `Range`, `value` call sites |
| `fsm_spcarddraw.fsm.16` | `Per25` trump-draw roll (25% gate) |

## Files

| File | Role |
|------|------|
| `reframework/autorun/re7_21_rng_trace.lua` | In-game capture script |
| `analyze_rng_log.py` | Session analysis + verdict |
| `unity_random.py` | Unity legacy PRNG (for seed recovery attempts) |
| `TARGETS.md` | Hook checklist for Object Explorer / il2cpp_dump |
| `test_analyze_rng_log.py` | Unit tests with synthetic logs |
