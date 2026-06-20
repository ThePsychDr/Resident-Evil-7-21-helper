# RE7:21 RNG trace targets

Use REFramework **Object Explorer** + `il2cpp_dump.json` from your RE7 install to confirm field/method names. Names below match existing solver comments and typical RE7 RT exports; **verify on your build** (Steam RT vs non-RT may differ).

## Primary singleton

```
app.CardGameMaster
sdk.get_managed_singleton("app.CardGameMaster")
```

### Fields to dump each round

| Field (expected) | Purpose |
|------------------|---------|
| `StockCardList` | Remaining / shuffled 1–11 deck order |
| `RandomIndexList` | Trump deal order for this fight |
| `Round` / round counter | Correlate shuffle with round index |
| `KillCount` | Survival+ fight index |
| Player/banker hand lists | Cross-check draws vs stock |

### Methods to hook (search TDB)

| Method pattern | Log when called |
|----------------|-----------------|
| `*Shuffle*` / `*Stock*` / `*InitCard*` | Pre/post `StockCardList` + `Random.state` |
| `*Draw*` / `*TakeCard*` | Card value + stock before/after |
| `*Init*` on round start | Possible `Random.InitState` nearby |

## Unity RNG

```
UnityEngine.Random
```

| API | Hook goal |
|-----|-----------|
| `InitState(int seed)` | Capture seed at fight/round start |
| `get_state` / `set_state` | Snapshot full PRNG state |
| `Range(int, int)` | Count calls during shuffle vs draw |
| `value` | Float draws (trump % rolls?) |

**Hypothesis under test:** numbered cards use `StockCardList` reshuffled per round via Unity RNG; trump order uses `RandomIndexList` once per fight.

## Trump draw RNG (`Per25`)

From `hoffman_rule_table.json` / `fsm_spcarddraw.fsm.16`:

- 25% roll at standard trigger points
- Pool pick uses `CheckCondition1/2/3` → `RandomSPcard_*` tables

Log when FSM hits `Per25` node: record bool result + subsequent trump ID.

## Capture protocol (minimum viable session)

For a useful first log, record **two full sessions**:

1. **Session A:** Normal 21 vs Lucas — 3 rounds, note every draw order
2. **Session B:** Survival fight #1 (Tally Mark) — 3+ rounds, same inputs where possible

Then:

```bash
python3 research/rng/analyze_rng_log.py captures/session_a.jsonl captures/session_b.jsonl
```

Compare verdicts across sessions. `SESSION_FIXED` in both with **different** seeds → not console-deducible. Same shuffle given same round index across restarts → investigate `DEDUCIBLE` path.

## Object Explorer checklist

- [ ] Locate `app.CardGameMaster` under Singletons
- [ ] Confirm `StockCardList` element type (card no / struct)
- [ ] Find shuffle method name; add to Lua `METHOD_CANDIDATES`
- [ ] Locate `UnityEngine.Random` type; verify `InitState` exists on your dump
- [ ] Optional: `app.CardGameItemTable` for trump pool indices

Update `re7_21_rng_trace.lua` `FIELD_CANDIDATES` once confirmed.
