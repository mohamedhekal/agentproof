"""The tool surface an agent sees, plus fault injection and trace recording.

`ToolBox` sits between the agent and the `World`. It can inject the failures that make
production agents fall over (timeouts that *did* apply, duplicated deliveries, malformed
payloads, lost acks) and records every call so a run can be replayed offline.
"""
from __future__ import annotations

import random
from typing import Any

from .world import ToolError, ToolTimeout, World

READ_TOOLS = {"lookup_order", "get_customer", "get_tracking"}

READ_FAULTS = (("transient", 0.40), ("timeout", 0.30), ("malformed", 0.30))
WRITE_FAULTS = (
    ("transient", 0.25),  # 503, nothing happened
    ("timeout_lost", 0.15),  # timeout, nothing happened
    ("timeout_applied", 0.25),  # timeout, but the write DID happen  (the dangerous one)
    ("ack_lost", 0.20),  # write happened, response came back empty
    ("duplicate", 0.15),  # at-least-once delivery: the write is applied twice
)


class BudgetExceeded(Exception):
    """The agent burned its tool-call budget (runaway loop guard)."""


class ReplayDivergence(Exception):
    """During replay the agent asked for something the recording does not contain."""


class _ToolSurface:
    """The methods agents call. Subclasses implement `_invoke`."""

    def _invoke(self, name: str, **kw: Any) -> Any:  # pragma: no cover - interface
        raise NotImplementedError

    def lookup_order(self, order_id: str) -> Any:
        return self._invoke("lookup_order", order_id=order_id)

    def get_customer(self, customer_id: str) -> Any:
        return self._invoke("get_customer", customer_id=customer_id)

    def get_tracking(self, order_id: str) -> Any:
        return self._invoke("get_tracking", order_id=order_id)

    def issue_refund(self, order_id: str, amount: float, idempotency_key: str | None = None) -> Any:
        return self._invoke("issue_refund", order_id=order_id, amount=amount, idempotency_key=idempotency_key)

    def reship(self, order_id: str, idempotency_key: str | None = None) -> Any:
        return self._invoke("reship", order_id=order_id, idempotency_key=idempotency_key)

    def send_message(self, customer_id: str, text: str, idempotency_key: str | None = None) -> Any:
        return self._invoke("send_message", customer_id=customer_id, text=text, idempotency_key=idempotency_key)

    def escalate(self, order_id: str, reason: str, idempotency_key: str | None = None) -> Any:
        return self._invoke("escalate", order_id=order_id, reason=reason, idempotency_key=idempotency_key)


def _weighted(rng: random.Random, table: tuple[tuple[str, float], ...]) -> str:
    r = rng.random()
    acc = 0.0
    for name, w in table:
        acc += w
        if r < acc:
            return name
    return table[-1][0]


def _corrupt(rng: random.Random, value: Any) -> Any:
    """Return a plausible-but-wrong payload."""
    kind = rng.choice(["none", "empty", "drop_key", "stringify"])
    if kind == "none" or not isinstance(value, dict) or not value:
        return None
    if kind == "empty":
        return {}
    if kind == "drop_key":
        out = dict(value)
        out.pop(rng.choice(sorted(out)))
        return out
    return {k: (str(v) if isinstance(v, (int, float)) else v) for k, v in value.items()}


class ToolBox(_ToolSurface):
    def __init__(self, world: World, rng: random.Random, chaos: float = 0.0, budget: int = 30) -> None:
        self.world = world
        self.rng = rng
        self.chaos = chaos
        self.budget = budget
        self.calls = 0
        self.faults = 0
        self.events: list[dict[str, Any]] = []

    def _invoke(self, name: str, **kw: Any) -> Any:
        self.calls += 1
        if self.calls > self.budget:
            raise BudgetExceeded(f"tool-call budget of {self.budget} exceeded")
        fault = None
        if self.chaos > 0 and self.rng.random() < self.chaos:
            fault = _weighted(self.rng, READ_FAULTS if name in READ_TOOLS else WRITE_FAULTS)
            self.faults += 1
        event: dict[str, Any] = {"i": self.calls, "tool": name, "args": kw, "fault": fault}
        try:
            result = self._dispatch(name, kw, fault)
        except ToolError as e:
            event["error"] = {
                "type": type(e).__name__,
                "message": str(e),
                "transient": e.transient,
                "code": e.code,
            }
            self.events.append(event)
            raise
        event["result"] = result
        self.events.append(event)
        return result

    def _dispatch(self, name: str, kw: dict[str, Any], fault: str | None) -> Any:
        fn = getattr(self.world, name)
        if fault is None:
            return fn(**kw)
        if fault == "transient":
            raise ToolError("503 service unavailable", transient=True, code="unavailable")
        if fault in ("timeout", "timeout_lost"):
            raise ToolTimeout()
        if fault == "timeout_applied":
            fn(**kw)
            raise ToolTimeout()
        if fault == "ack_lost":
            fn(**kw)
            return None
        if fault == "duplicate":
            fn(**kw)
            return fn(**kw)
        if fault == "malformed":
            return _corrupt(self.rng, fn(**kw))
        raise AssertionError(f"unknown fault {fault}")


class ReplayToolBox(_ToolSurface):
    """Serves a recorded run back to an agent: no world, no randomness, no network."""

    def __init__(self, events: list[dict[str, Any]]) -> None:
        self.events = events
        self.pos = 0

    def _invoke(self, name: str, **kw: Any) -> Any:
        if self.pos >= len(self.events):
            raise ReplayDivergence(f"agent made extra call #{self.pos + 1}: {name}({kw})")
        ev = self.events[self.pos]
        if ev["tool"] != name or ev["args"] != kw:
            raise ReplayDivergence(
                f"call #{self.pos + 1} diverged: recorded {ev['tool']}({ev['args']}) but agent called {name}({kw})"
            )
        self.pos += 1
        if "error" in ev:
            e = ev["error"]
            if e["type"] == "ToolTimeout":
                raise ToolTimeout(e["message"])
            raise ToolError(e["message"], transient=e["transient"], code=e["code"])
        return ev["result"]

    @property
    def fully_consumed(self) -> bool:
        return self.pos == len(self.events)
