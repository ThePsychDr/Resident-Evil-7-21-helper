#!/usr/bin/env python3
"""
Analyze RE7:21 RNG trace logs (Phase H).

Usage:
  python3 analyze_rng_log.py capture.jsonl [capture2.jsonl ...]
  python3 analyze_rng_log.py capture.jsonl --recover-seed
  python3 analyze_rng_log.py capture.jsonl --json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# Allow running from repo root or research/rng/
_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from unity_random import brute_force_seed_from_shuffle, fisher_yates_shuffle, UnityRandom


Event = Dict[str, Any]
Verdict = str  # DEDUCIBLE | SESSION_FIXED | OPAQUE


def load_events(paths: Sequence[Path]) -> List[Event]:
    events: List[Event] = []
    for path in paths:
        with path.open("r", encoding="utf-8") as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    print(f"warn: {path}:{lineno} invalid JSON: {exc}", file=sys.stderr)
    return events


def extract_shuffles(events: List[Event]) -> List[Dict[str, Any]]:
    """Collect stock orders from stock_shuffle / round_start / snapshot events."""
    shuffles: List[Dict[str, Any]] = []
    for ev in events:
        if ev.get("event") not in ("stock_shuffle", "round_start", "snapshot"):
            continue
        stock = ev.get("stock")
        if not stock or not isinstance(stock, list):
            continue
        try:
            nums = [int(x) for x in stock]
        except (TypeError, ValueError):
            continue
        if len(nums) < 2:
            continue
        shuffles.append({
            "round": ev.get("round"),
            "stock": nums,
            "reason": ev.get("reason") or ev.get("event"),
            "random": ev.get("random") or {},
        })
    return shuffles


def extract_init_seeds(events: List[Event]) -> List[int]:
    seeds = []
    for ev in events:
        if ev.get("event") != "random_init_state":
            continue
        s = ev.get("seed")
        if s is not None:
            try:
                seeds.append(int(s))
            except (TypeError, ValueError):
                pass
    return seeds


def dedupe_shuffles(shuffles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for s in shuffles:
        key = (s.get("round"), tuple(s["stock"]))
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return out


def test_round_index_determinism(shuffles: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """
    If same round number always yields same stock order within a session,
    shuffle may be round-index derived (console-observable).
    """
    by_round: Dict[Any, List[tuple]] = defaultdict(list)
    for s in shuffles:
        by_round[s.get("round")].append(tuple(s["stock"]))

    conflicts = []
    for rnd, orders in by_round.items():
        unique = set(orders)
        if len(unique) > 1:
            conflicts.append((rnd, unique))

    if conflicts:
        return False, f"round index not deterministic ({len(conflicts)} conflicting rounds)"
    if len(by_round) >= 2:
        return True, "stock order is a function of round index within session"
    return False, "insufficient round diversity"


def test_cross_session(shuffles_a: List[Dict[str, Any]], shuffles_b: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Same round index, different sessions — if orders always differ, likely session seed."""
    def round_map(shuffles: List[Dict[str, Any]]) -> Dict[Any, tuple]:
        m: Dict[Any, tuple] = {}
        for s in shuffles:
            m[s.get("round")] = tuple(s["stock"])
        return m

    ma, mb = round_map(shuffles_a), round_map(shuffles_b)
    common = set(ma.keys()) & set(mb.keys())
    if not common:
        return False, "no overlapping round indices between sessions"

    same = [r for r in common if ma[r] == mb[r]]
    if same:
        return True, f"identical shuffle at round(s) {same} across sessions — investigate fixed seed/table"
    return False, "all overlapping rounds differ across sessions (session entropy likely)"


def attempt_seed_recovery(shuffles: List[Dict[str, Any]], seed_max: int = 500_000) -> Dict[str, Any]:
    results = []
    for s in shuffles:
        stock = s["stock"]
        if sorted(stock) != list(range(1, 12)):
            results.append({
                "round": s.get("round"),
                "stock": stock,
                "recovered_seed": None,
                "note": "not a full 1–11 deck snapshot",
            })
            continue
        seed = brute_force_seed_from_shuffle(stock, seed_min=0, seed_max=seed_max)
        results.append({
            "round": s.get("round"),
            "stock": stock,
            "recovered_seed": seed,
            "note": "match" if seed is not None else f"no seed in [0, {seed_max})",
        })
    recovered = [r for r in results if r["recovered_seed"] is not None]
    return {
        "attempted": len(results),
        "recovered": len(recovered),
        "details": results,
    }


def predict_next_round_from_seed(seed: int, round_count: int = 2) -> Optional[List[List[int]]]:
    """If one seed + sequential shuffles, simulate multi-round deck orders."""
    rng = UnityRandom(seed)
    base = list(range(1, 12))
    orders = []
    for _ in range(round_count):
        orders.append(fisher_yates_shuffle(rng, base))
    return orders


def decide_verdict(
    events: List[Event],
    shuffles: List[Dict[str, Any]],
    recovery: Optional[Dict[str, Any]],
    multi_session: Optional[Tuple[bool, str]],
) -> Tuple[Verdict, List[str]]:
    reasons: List[str] = []

    init_seeds = extract_init_seeds(events)
    if init_seeds:
        unique_seeds = set(init_seeds)
        reasons.append(f"captured {len(init_seeds)} InitState call(s), {len(unique_seeds)} unique seed(s)")
        if len(unique_seeds) == 1 and len(shuffles) >= 2:
            return "SESSION_FIXED", reasons + ["single InitState per session — PC seed capture could predict deck"]

    round_det, round_msg = test_round_index_determinism(shuffles)
    reasons.append(round_msg)

    if recovery and recovery["recovered"] > 0:
        reasons.append(f"Unity Fisher-Yates seed recovered for {recovery['recovered']}/{recovery['attempted']} full decks")
        if round_det and recovery["recovered"] == recovery["attempted"]:
            return "DEDUCIBLE", reasons + [
                "shuffle matches Unity InitState(seed)+FY — test if seed is observable in-game"
            ]

    if multi_session:
        cross, cross_msg = multi_session
        reasons.append(cross_msg)
        if cross:
            return "DEDUCIBLE", reasons + ["cross-session repeat — may be fixed table not RNG"]

    if round_det and not (recovery and recovery["recovered"]):
        return "OPAQUE", reasons + [
            "round-stable but seed not recovered — likely opaque RNG or non-Unity shuffle"
        ]

    if len(shuffles) < 2:
        return "OPAQUE", reasons + ["need more captures (2+ shuffles, 2+ sessions recommended)"]

    return "OPAQUE", reasons + [
        "default: no deducible pattern — keep public solver probabilistic"
    ]


def analyze(paths: Sequence[Path], recover_seed: bool = False, seed_max: int = 500_000) -> Dict[str, Any]:
    events = load_events(paths)
    shuffles = dedupe_shuffles(extract_shuffles(events))

    recovery = None
    if recover_seed and shuffles:
        recovery = attempt_seed_recovery(shuffles, seed_max=seed_max)

    multi_session = None
    if len(paths) >= 2:
        ev_a = extract_shuffles(load_events([paths[0]]))
        ev_b = extract_shuffles(load_events([paths[1]]))
        multi_session = test_cross_session(ev_a, ev_b)

    verdict, reasons = decide_verdict(events, shuffles, recovery, multi_session)

    return {
        "verdict": verdict,
        "reasons": reasons,
        "files": [str(p) for p in paths],
        "event_count": len(events),
        "shuffle_count": len(shuffles),
        "init_state_calls": len(extract_init_seeds(events)),
        "shuffles": shuffles,
        "seed_recovery": recovery,
        "public_release_recommendation": _release_note(verdict),
    }


def _release_note(verdict: Verdict) -> str:
    if verdict == "DEDUCIBLE":
        return "Revisit public perfect prediction ONLY if seed/table is observable without PC hooks."
    if verdict == "SESSION_FIXED":
        return "Do not ship seed-based prediction publicly; PC-only research path."
    return "Keep public build as rules-accurate simulator (current README stance)."


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze RE7:21 RNG trace logs")
    parser.add_argument("logs", nargs="+", type=Path, help="JSONL capture file(s)")
    parser.add_argument("--recover-seed", action="store_true", help="Brute-force Unity seed for full decks")
    parser.add_argument("--seed-max", type=int, default=500_000, help="Upper bound for seed search")
    parser.add_argument("--json", action="store_true", help="Print full JSON report")
    args = parser.parse_args()

    report = analyze(args.logs, recover_seed=args.recover_seed, seed_max=args.seed_max)

    if args.json:
        print(json.dumps(report, indent=2))
        return

    print("=" * 60)
    print("RE7:21 RNG ANALYSIS (Phase H)")
    print("=" * 60)
    print(f"Verdict: {report['verdict']}")
    print(f"Events: {report['event_count']}  Shuffles: {report['shuffle_count']}  InitState hooks: {report['init_state_calls']}")
    print()
    print("Reasoning:")
    for r in report["reasons"]:
        print(f"  • {r}")
    print()
    print(f"Public release: {report['public_release_recommendation']}")
    if report.get("seed_recovery"):
        rec = report["seed_recovery"]
        print()
        print(f"Seed recovery: {rec['recovered']}/{rec['attempted']} full decks")
        for d in rec["details"]:
            if d["recovered_seed"] is not None:
                print(f"  round {d['round']}: seed={d['recovered_seed']} stock={d['stock']}")


if __name__ == "__main__":
    main()
