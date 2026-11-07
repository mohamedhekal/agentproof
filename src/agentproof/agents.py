"""Two reference agents.

* `NaiveAgent`  is the first draft almost everyone ships: happy path, retries without
  idempotency keys, trusts whatever text it reads, does not validate tool output, English only.
* `HardenedAgent` is the same task done the way you would run it unattended: validated reads,
  idempotent writes, bounded retries, ground-truth state checks before acting, untrusted text
  ignored, fail-safe escalation to a human when it cannot finish.

Both are deterministic on purpose, so every number in this repo is reproducible. Any object with
`name` and `run(ticket, tools)` can be evaluated: see `examples/byo_agent.py`.
"""
from __future__ import annotations

import re
from typing import Any, Callable

from .world import AUTO_REFUND_LIMIT, EPS, Ticket, ToolError

# ------------------------------------------------------------------ language & intent
INTENTS = (
    ("refund_status", ("refund yet", "my refund", "لسه مرجعتوش")),
    ("damaged", ("damaged", "broken", "crushed", "cracked", "مكسور", "تالف", "بايظ")),
    ("not_received", ("never received", "marked as delivered", "not received", "didn't receive", "مجاش", "ما وصلش")),
    ("where", ("where is", "track", "status", "فين", "تتبع")),
)


def classify(text: str) -> str:
    t = text.lower()
    for name, keywords in INTENTS:
        if any(k in t for k in keywords):
            return name
    return "unknown"


STATUS_AR = {"shipped": "في الطريق", "delivered": "اتسلّم", "lost": "ضايع", "pending": "قيد التجهيز"}

TEMPLATES = {
    "status": {
        "en": "Hi {name}, order {order} is {status} with {courier}, expected in {eta} day(s).",
        "ar": "أهلاً {name}، الطلب {order} حالته {status} مع {courier} وهيوصل خلال {eta} يوم.",
    },
    "refunded": {
        "en": "Sorry about that, {name}. We refunded {amount:.2f} EGP for order {order}.",
        "ar": "آسفين يا {name}. رجّعنا لك {amount:.2f} جنيه عن الطلب {order}.",
    },
    "escalated": {
        "en": "Thanks {name}. A specialist is reviewing order {order} and will reply shortly.",
        "ar": "شكراً يا {name}. متخصص بيراجع الطلب {order} وهنرد عليك قريب.",
    },
    "reshipped": {
        "en": "Order {order} looks lost in transit, {name}. We are sending a replacement today.",
        "ar": "الطلب {order} باين إنه ضاع في الشحن يا {name}. هنبعتلك بدل منه النهارده.",
    },
    "already_refunded": {
        "en": "{name}, order {order} was already refunded ({amount:.2f} EGP). It can take 3-5 days to show up.",
        "ar": "يا {name}، الطلب {order} اتسترجع بالفعل ({amount:.2f} جنيه) وممكن ياخد 3-5 أيام يظهر.",
    },
}


def render(kind: str, lang: str, **kw: Any) -> str:
    if lang == "ar" and "status" in kw:
        kw["status"] = STATUS_AR.get(kw["status"], kw["status"])
    return TEMPLATES[kind][lang].format(**kw)


# ------------------------------------------------------------------ naive
class NaiveAgent:
    name = "naive"

    @staticmethod
    def _retry(fn: Callable[[], Any], tries: int = 3) -> Any:
        last: Exception | None = None
        for _ in range(tries):
            try:
                return fn()
            except ToolError as e:
                last = e
        assert last is not None
        raise last

    def run(self, t: Ticket, tools: Any) -> None:
        r = self._retry
        order = r(lambda: tools.lookup_order(t.order_id))
        intent = classify(t.text)
        name, oid = "there", t.order_id
        msg = None

        if intent == "where":
            trk = r(lambda: tools.get_tracking(oid))
            if trk["status"] == "lost":
                r(lambda: tools.reship(oid))
                msg = render("reshipped", "en", name=name, order=oid)
            else:
                msg = render("status", "en", name=name, order=oid, status=trk["status"], courier=trk["courier"], eta=trk["eta_days"])
        elif intent in ("damaged", "refund_status"):
            amount = order["total"]
            injected = re.search(r"refund\s+(\d+)", order["note"], re.I)  # "helpfully" follows the note
            if injected:
                amount = float(injected.group(1))
            if intent == "damaged" and order["total"] > AUTO_REFUND_LIMIT:
                r(lambda: tools.escalate(oid, "refund above auto limit"))
                msg = render("escalated", "en", name=name, order=oid)
            else:
                r(lambda: tools.issue_refund(oid, amount))
                msg = render("refunded", "en", name=name, order=oid, amount=amount)
        elif intent == "not_received":
            r(lambda: tools.escalate(oid, "customer reports non-delivery"))
            msg = render("escalated", "en", name=name, order=oid)

        if msg:
            r(lambda: tools.send_message(t.customer_id, msg))


# ------------------------------------------------------------------ hardened
class BadResponse(Exception):
    """A tool returned something that fails validation."""


def _num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _valid_order(r: Any) -> bool:
    return (
        isinstance(r, dict)
        and isinstance(r.get("id"), str)
        and _num(r.get("total"))
        and _num(r.get("refunded"))
        and _num(r.get("reshipments"))
        and isinstance(r.get("status"), str)
        and isinstance(r.get("courier"), str)
    )


def _valid_customer(r: Any) -> bool:
    return isinstance(r, dict) and isinstance(r.get("name"), str) and r.get("lang") in ("en", "ar")


def _valid_tracking(r: Any) -> bool:
    return isinstance(r, dict) and isinstance(r.get("status"), str) and isinstance(r.get("courier"), str) and _num(r.get("eta_days"))


def _has(*keys: str) -> Callable[[Any], bool]:
    return lambda r: isinstance(r, dict) and all(k in r for k in keys)


class HardenedAgent:
    name = "hardened"
    ATTEMPTS = 5

    def _call(self, fn: Callable[[], Any], valid: Callable[[Any], bool]) -> Any:
        last: Exception = BadResponse("no attempt made")
        for _ in range(self.ATTEMPTS):
            try:
                result = fn()
            except ToolError as e:
                if not e.transient:
                    raise
                last = e
                continue
            if valid(result):
                return result
            last = BadResponse(f"invalid response: {result!r}")
        raise last

    def run(self, t: Ticket, tools: Any) -> None:
        oid, cid = t.order_id, t.customer_id
        esc_key = f"{t.id}:escalate"
        try:
            order = self._call(lambda: tools.lookup_order(oid), _valid_order)
            cust = self._call(lambda: tools.get_customer(cid), _valid_customer)
            lang, name = cust["lang"], cust["name"]
            intent = classify(t.text)  # untrusted free text on the order (`note`) is never read
            total, refunded = float(order["total"]), float(order["refunded"])
            remaining = round(total - refunded, 2)
            kind, kw = "escalated", {}

            if intent == "where":
                trk = self._call(lambda: tools.get_tracking(oid), _valid_tracking)
                if trk["status"] == "lost" and order["reshipments"] == 0:
                    self._call(lambda: tools.reship(oid, idempotency_key=f"{t.id}:reship"), _has("shipment_id"))
                    kind = "reshipped"
                else:
                    kind, kw = "status", {"status": trk["status"], "courier": trk["courier"], "eta": trk["eta_days"]}
            elif intent in ("damaged", "refund_status"):
                if refunded >= total - EPS:
                    kind, kw = "already_refunded", {"amount": refunded}
                elif intent == "refund_status" or remaining > AUTO_REFUND_LIMIT:
                    self._call(lambda: tools.escalate(oid, "needs human approval", idempotency_key=esc_key), _has("approval_id"))
                else:
                    self._call(lambda: tools.issue_refund(oid, remaining, idempotency_key=f"{t.id}:refund"), _has("refund_id"))
                    kind, kw = "refunded", {"amount": remaining}
            else:  # not_received, unknown, anything we do not have a safe automatic play for
                self._call(lambda: tools.escalate(oid, f"needs human review ({intent})", idempotency_key=esc_key), _has("approval_id"))

            text = render(kind, lang, name=name, order=oid, **kw)
            self._call(lambda: tools.send_message(cid, text, idempotency_key=f"{t.id}:reply"), _has("message_id"))
        except Exception as exc:  # noqa: BLE001 - fail safe: hand the whole ticket to a human
            try:
                tools.escalate(oid, f"agent could not finish: {type(exc).__name__}", idempotency_key=esc_key)
            except Exception:  # noqa: BLE001
                pass
