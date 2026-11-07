"""Calibrated autonomy: decide *when a human must be pulled in*, and learn to ask less over time.

A static rule ("ask if amount > X") cannot tell a safe action class from a fraud-prone one at the
same amount. `CalibratedRouter` keeps a rolling window of human verdicts per action class and only
acts on its own when the Wilson lower confidence bound of the approval rate clears a target. Auto
actions are audited at a small rate, so if a class starts going bad (drift) it falls back to asking.
"""
from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass


def wilson_lcb(k: int, n: int, z: float = 1.64) -> float:
    if n == 0:
        return 0.0
    p, z2 = k / n, z * z
    return (p + z2 / (2 * n) - z * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))) / (1 + z2 / n)


class CalibratedRouter:
    def __init__(self, target: float = 0.95, window: int = 120, min_samples: int = 30,
                 audit_rate: float = 0.15, hard_cap: float | None = 500.0, seed: int = 0) -> None:
        self.target, self.window, self.min_samples = target, window, min_samples
        self.audit_rate, self.hard_cap = audit_rate, hard_cap
        self.history: dict[str, deque[int]] = {}
        self.rng = random.Random(seed)

    def decide(self, action_class: str, amount: float = 0.0) -> str:
        if self.hard_cap is not None and amount > self.hard_cap:
            return "ask"
        h = self.history.get(action_class)
        if h is None or len(h) < self.min_samples:
            return "ask"
        return "auto" if wilson_lcb(sum(h), len(h)) >= self.target else "ask"

    def feedback(self, action_class: str, approved: bool) -> None:
        self.history.setdefault(action_class, deque(maxlen=self.window)).append(1 if approved else 0)

    def should_audit(self) -> bool:
        return self.rng.random() < self.audit_rate


# ------------------------------------------------------------------ simulation
@dataclass(frozen=True)
class ActionClass:
    name: str
    weight: float
    amount: tuple[float, float]
    p_approve: float  # probability a human would approve this action as proposed


CLASSES = (
    ActionClass("refund_damaged_small", 0.40, (50, 450), 0.995),
    ActionClass("reship_lost", 0.15, (100, 400), 0.98),
    ActionClass("refund_not_received", 0.20, (50, 450), 0.55),  # fraud-prone, same amounts as the safe ones
    ActionClass("refund_wrong_item", 0.10, (50, 450), 0.93),
    ActionClass("refund_damaged_large", 0.15, (500, 2500), 0.93),
)
DRIFT_CLASS, DRIFT_P = "refund_damaged_small", 0.80  # a fraud wave hits halfway through


def _stream(n: int, seed: int) -> list[tuple[str, float, float]]:
    rng = random.Random(seed)
    weights = [c.weight for c in CLASSES]
    out = []
    for _ in range(n):
        c = rng.choices(CLASSES, weights)[0]
        out.append((c.name, rng.uniform(*c.amount), rng.random()))
    return out


def simulate(n: int = 4000, seed: int = 7, windows: int = 8) -> dict:
    actions = _stream(n, seed)
    p_base = {c.name: c.p_approve for c in CLASSES}

    def human_approves(i: int, klass: str, u: float) -> bool:
        p = DRIFT_P if (klass == DRIFT_CLASS and i >= n // 2) else p_base[klass]
        return u < p

    def run(policy: str) -> dict:
        router = CalibratedRouter(seed=seed)
        per_win = n // windows
        asks = [0] * windows
        bad = [0] * windows
        for i, (klass, amount, u) in enumerate(actions):
            w = min(i // per_win, windows - 1)
            ok = human_approves(i, klass, u)
            if policy == "always_ask":
                decision = "ask"
            elif policy == "static_threshold":
                decision = "ask" if amount > 500 else "auto"
            else:
                decision = router.decide(klass, amount)
            if decision == "ask":
                asks[w] += 1
                if policy == "calibrated":
                    router.feedback(klass, ok)
            else:
                if not ok:
                    bad[w] += 1  # a bad action went out without a human looking
                if policy == "calibrated" and router.should_audit():
                    router.feedback(klass, ok)
        return {
            "ask_rate": round(sum(asks) / n, 4),
            "bad_auto_rate": round(sum(bad) / n, 4),
            "ask_by_window": [round(a / per_win, 3) for a in asks],
            "bad_by_window": [round(b / per_win, 3) for b in bad],
        }

    return {"n": n, "seed": seed, "policies": {p: run(p) for p in ("always_ask", "static_threshold", "calibrated")}}
