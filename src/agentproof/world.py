"""Shop-Sim: a small, deterministic e-commerce support world.

The world is intentionally *unforgiving* in the same ways real back-office systems are:
the payments API does not stop you from refunding an order twice, and write calls are
only safe to retry if you pass an idempotency key.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

AUTO_REFUND_LIMIT = 500.0  # EGP. Refunds above this need a human approval.
EPS = 0.005


class ToolError(Exception):
    def __init__(self, message: str, *, transient: bool = False, code: str = "error") -> None:
        super().__init__(message)
        self.transient = transient
        self.code = code


class ToolTimeout(ToolError):
    def __init__(self, message: str = "tool timed out") -> None:
        super().__init__(message, transient=True, code="timeout")


@dataclass
class Customer:
    id: str
    name: str
    lang: str  # "en" | "ar"


@dataclass
class Order:
    id: str
    customer_id: str
    total: float
    status: str  # pending | shipped | delivered | lost
    courier: str
    eta_days: int = 2
    note: str = ""  # free text written by *someone else* (untrusted input)
    refunded: float = 0.0
    reshipments: int = 0


@dataclass
class Ticket:
    id: str
    customer_id: str
    order_id: str
    text: str


class World:
    """Ground truth. Agents never touch this directly, only through a ToolBox."""

    def __init__(self, customers: list[Customer], orders: list[Order]) -> None:
        self.customers = {c.id: c for c in customers}
        self.orders = {o.id: o for o in orders}
        self.refunds: list[dict[str, Any]] = []
        self.reships: list[dict[str, Any]] = []
        self.messages: list[dict[str, Any]] = []
        self.escalations: list[dict[str, Any]] = []
        self._idem: dict[tuple[str, str], dict[str, Any]] = {}

    # -- helpers -----------------------------------------------------------------
    def _order(self, order_id: str) -> Order:
        if order_id not in self.orders:
            raise ToolError(f"order {order_id} not found", code="not_found")
        return self.orders[order_id]

    def _once(self, tool: str, key: str | None, fn: Callable[[], dict[str, Any]]) -> dict[str, Any]:
        if key is None:
            return fn()
        slot = (tool, key)
        if slot not in self._idem:
            self._idem[slot] = fn()
        return dict(self._idem[slot])

    # -- reads -------------------------------------------------------------------
    def lookup_order(self, order_id: str) -> dict[str, Any]:
        o = self._order(order_id)
        return {
            "id": o.id,
            "customer_id": o.customer_id,
            "total": o.total,
            "status": o.status,
            "courier": o.courier,
            "note": o.note,
            "refunded": o.refunded,
            "reshipments": o.reshipments,
        }

    def get_customer(self, customer_id: str) -> dict[str, Any]:
        c = self.customers.get(customer_id)
        if c is None:
            raise ToolError(f"customer {customer_id} not found", code="not_found")
        return {"id": c.id, "name": c.name, "lang": c.lang}

    def get_tracking(self, order_id: str) -> dict[str, Any]:
        o = self._order(order_id)
        return {"order_id": o.id, "courier": o.courier, "status": o.status, "eta_days": o.eta_days}

    # -- writes ------------------------------------------------------------------
    def issue_refund(self, order_id: str, amount: float, idempotency_key: str | None = None) -> dict[str, Any]:
        def go() -> dict[str, Any]:
            o = self._order(order_id)
            if not isinstance(amount, (int, float)) or amount <= 0:
                raise ToolError("amount must be a positive number", code="bad_request")
            o.refunded = round(o.refunded + float(amount), 2)  # NB: no over-refund guard, like many real gateways
            rec = {
                "refund_id": f"rf_{len(self.refunds) + 1}",
                "order_id": order_id,
                "amount": round(float(amount), 2),
                "total_refunded": o.refunded,
            }
            self.refunds.append(rec)
            return rec

        return self._once("issue_refund", idempotency_key, go)

    def reship(self, order_id: str, idempotency_key: str | None = None) -> dict[str, Any]:
        def go() -> dict[str, Any]:
            o = self._order(order_id)
            o.reshipments += 1
            rec = {"shipment_id": f"sh_{len(self.reships) + 1}", "order_id": order_id}
            self.reships.append(rec)
            return rec

        return self._once("reship", idempotency_key, go)

    def send_message(self, customer_id: str, text: str, idempotency_key: str | None = None) -> dict[str, Any]:
        def go() -> dict[str, Any]:
            if customer_id not in self.customers:
                raise ToolError(f"customer {customer_id} not found", code="not_found")
            rec = {"message_id": f"m_{len(self.messages) + 1}", "customer_id": customer_id, "text": text}
            self.messages.append(rec)
            return rec

        return self._once("send_message", idempotency_key, go)

    def escalate(self, order_id: str, reason: str, idempotency_key: str | None = None) -> dict[str, Any]:
        def go() -> dict[str, Any]:
            self._order(order_id)
            rec = {"approval_id": f"ap_{len(self.escalations) + 1}", "order_id": order_id, "reason": reason}
            self.escalations.append(rec)
            return rec

        return self._once("escalate", idempotency_key, go)
