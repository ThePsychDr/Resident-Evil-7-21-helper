"""
Unity legacy Random (XorShift128+) — used by RE Engine / Unity 5.x–2017 titles.

Reference: UnityEngine.Random decompilation (Mono/IL2CPP). Calibrate against
re7_21_rng_trace.jsonl captures if recovery fails on real data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass
class RandomState:
    x: int
    y: int
    z: int
    w: int

    def as_tuple(self) -> Tuple[int, int, int, int]:
        return (self.x & 0xFFFFFFFF, self.y & 0xFFFFFFFF, self.z & 0xFFFFFFFF, self.w & 0xFFFFFFFF)


class UnityRandom:
    """Minimal port of Unity's static Random for seed search."""

    def __init__(self, seed: Optional[int] = None):
        self.x = 0
        self.y = 0
        self.z = 0
        self.w = 0
        if seed is not None:
            self.init_state(seed)

    def init_state(self, seed: int) -> None:
        seed = int(seed) & 0xFFFFFFFF
        self.x = seed
        self.y = (seed * 279470273) & 0xFFFFFFFF
        self.z = (seed * 279470273 + 1) & 0xFFFFFFFF
        self.w = (seed * 279470273 + 2) & 0xFFFFFFFF

    def set_state(self, state: RandomState) -> None:
        self.x, self.y, self.z, self.w = state.as_tuple()

    def get_state(self) -> RandomState:
        return RandomState(self.x, self.y, self.z, self.w)

    def _next_uint(self) -> int:
        t = (self.x ^ ((self.x << 11) & 0xFFFFFFFF)) & 0xFFFFFFFF
        self.x = self.y
        self.y = self.z
        self.z = self.w
        self.w = (self.w ^ (self.w >> 19) ^ (t ^ (t >> 8))) & 0xFFFFFFFF
        return self.w

    def value(self) -> float:
        """Unity Random.value — [0, 1)."""
        return (self._next_uint() & 0x7FFFFFFF) / 2147483648.0

    def range_int(self, min_inclusive: int, max_exclusive: int) -> int:
        """Unity Random.Range(int min, int max) — max is exclusive."""
        if min_inclusive >= max_exclusive:
            return min_inclusive
        span = max_exclusive - min_inclusive
        return min_inclusive + int(self.value() * span)


def fisher_yates_shuffle(rng: UnityRandom, deck: List[int]) -> List[int]:
    """Typical deck shuffle using Unity integer Range."""
    arr = list(deck)
    for i in range(len(arr) - 1, 0, -1):
        j = rng.range_int(0, i + 1)
        arr[i], arr[j] = arr[j], arr[i]
    return arr


def brute_force_seed_from_shuffle(
    observed_order: List[int],
    base_deck: Optional[List[int]] = None,
    seed_min: int = 0,
    seed_max: int = 1_000_000,
) -> Optional[int]:
    """
    Try InitState(seed) + Fisher-Yates for a full 1–11 deck.
    Returns matching seed or None.
    """
    if base_deck is None:
        base_deck = list(range(1, 12))
    if sorted(observed_order) != sorted(base_deck):
        return None

    for seed in range(seed_min, seed_max):
        rng = UnityRandom(seed)
        if fisher_yates_shuffle(rng, base_deck) == observed_order:
            return seed
    return None


def step_rng_after_shuffle(seed: int, base_deck: Optional[List[int]] = None) -> RandomState:
    """Return RNG state after one full deck shuffle from seed."""
    if base_deck is None:
        base_deck = list(range(1, 12))
    rng = UnityRandom(seed)
    fisher_yates_shuffle(rng, base_deck)
    return rng.get_state()
