"""Redaction of secrets and personal data from traces, cassettes and reports.

Evaluation recordings can end up containing things nobody meant to record: an API key echoed in an
error message, a customer's email or phone number in a ticket, a payment card number. Run
`agentproof redact` on a recording before you share, commit or attach it.

This is a best-effort safety net based on patterns (it will miss secrets in unusual formats and may
over-redact a long number). It is not a substitute for not recording sensitive data in the first place.
"""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

# Emails that are safe to keep (bot / no-reply addresses used for attribution).
SAFE_EMAIL_PARTS = ("noreply@anthropic.com", "@users.noreply.github.com")

_SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("private_key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("api_key", re.compile(r"\bsk-(?:ant-)?[A-Za-z0-9_\-]{16,}")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9\-]{10,}")),
    ("bearer_token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._\-]{16,}")),
]
_EMAIL = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
_CARD = re.compile(r"(?<![\w.])(?:\d[ \-]?){12,18}\d(?!\w)")
# Phone shapes: international (+..), a bare 10-15 digit run, or digit groups split by single spaces/dashes.
# Deliberately not "any long run of digits and punctuation": prices like "ORD-76541 (414.94 EGP)" must survive.
_PHONE = re.compile(
    r"(?<![\w.\-])(?:\+\d[\d ()\-]{8,16}\d|\d{10,15}|\d{3,4}[ \-]\d{3}[ \-]\d{3,4})(?![\w.]|[ \-]\d)"
)
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _luhn(digits: str) -> bool:
    total, alt = 0, False
    for ch in reversed(digits):
        d = int(ch)
        if alt:
            d *= 2
            if d > 9:
                d -= 9
        total += d
        alt = not alt
    return total % 10 == 0


def _is_card(raw: str) -> bool:
    digits = re.sub(r"\D", "", raw)
    return 13 <= len(digits) <= 19 and _luhn(digits)


def _is_phone(raw: str) -> bool:
    if _DATE.fullmatch(raw.strip()):
        return False
    digits = re.sub(r"\D", "", raw)
    return 10 <= len(digits) <= 15


def _safe_email(addr: str) -> bool:
    return any(part in addr.lower() for part in SAFE_EMAIL_PARTS)


def find(text: str, *, pii: bool = True) -> list[tuple[str, str]]:
    """Return [(kind, matched text)] for everything that looks sensitive. `pii=False` checks secrets only."""
    hits: list[tuple[str, str]] = []
    for kind, pat in _SECRET_PATTERNS:
        hits += [(kind, m.group(0)) for m in pat.finditer(text)]
    if pii:
        hits += [("email", m.group(0)) for m in _EMAIL.finditer(text) if not _safe_email(m.group(0))]
        hits += [("card", m.group(0)) for m in _CARD.finditer(text) if _is_card(m.group(0))]
        card_spans = [m.span() for m in _CARD.finditer(text) if _is_card(m.group(0))]
        for m in _PHONE.finditer(text):
            if _is_phone(m.group(0)) and not any(s <= m.start() < e for s, e in card_spans):
                hits.append(("phone", m.group(0)))
    return hits


def redact_text(text: str, counts: Counter | None = None) -> str:
    counts = counts if counts is not None else Counter()

    def sub(kind: str):
        def repl(m: re.Match[str]) -> str:
            counts[kind] += 1
            return f"[REDACTED:{kind}]"

        return repl

    for kind, pat in _SECRET_PATTERNS:
        text = pat.sub(sub(kind), text)
    text = _EMAIL.sub(lambda m: m.group(0) if _safe_email(m.group(0)) else (counts.update(["email"]) or "[REDACTED:email]"), text)
    text = _CARD.sub(lambda m: (counts.update(["card"]) or "[REDACTED:card]") if _is_card(m.group(0)) else m.group(0), text)
    text = _PHONE.sub(lambda m: (counts.update(["phone"]) or "[REDACTED:phone]") if _is_phone(m.group(0)) else m.group(0), text)
    return text


def redact_json(obj: Any, counts: Counter | None = None) -> Any:
    """Redact every string value (dict keys are kept as they are)."""
    counts = counts if counts is not None else Counter()
    if isinstance(obj, str):
        return redact_text(obj, counts)
    if isinstance(obj, list):
        return [redact_json(x, counts) for x in obj]
    if isinstance(obj, dict):
        return {k: redact_json(v, counts) for k, v in obj.items()}
    return obj


def redact_file(src: Path, dst: Path | None = None) -> Counter:
    """Redact a .jsonl / .json / text file. Returns what was removed; writes nothing if `dst` is None."""
    counts: Counter = Counter()
    raw = src.read_text(encoding="utf-8")
    if src.suffix == ".jsonl":
        out_lines = []
        for line in raw.splitlines():
            if not line.strip():
                out_lines.append(line)
                continue
            try:
                out_lines.append(json.dumps(redact_json(json.loads(line), counts), ensure_ascii=False))
            except ValueError:
                out_lines.append(redact_text(line, counts))
        out = "\n".join(out_lines) + ("\n" if raw.endswith("\n") else "")
    elif src.suffix == ".json":
        try:
            out = json.dumps(redact_json(json.loads(raw), counts), ensure_ascii=False, indent=2) + "\n"
        except ValueError:
            out = redact_text(raw, counts)
    else:
        out = redact_text(raw, counts)
    if dst is not None:
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(out, encoding="utf-8")
    return counts
