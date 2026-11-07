"""Rule-based claim extractor (English + Egyptian Arabic) with fuzzy client linking.

Deliberately pluggable: the Brain only needs `extract(text, clients) -> Parsed | None`. A production
system would put an LLM here; keeping it rule-based makes the benchmark deterministic and free.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher

EFFECTIVE = re.compile(r"\s*(?:\(\s*)?(?:effective|اعتبارًا من|اعتبارا من)\s+(\d{4}-\d{2}-\d{2})\s*\)?", re.I)
CORRECTION = re.compile(r"^\s*(?:correction|تصحيح)\s*[:\-]\s*", re.I)
RETRACTION = re.compile(r"(?:ignore (?:my|the) (?:last|earlier|previous) (?:message|note)|تجاهل رسالتي)", re.I)

PATTERNS: list[tuple[str, re.Pattern]] = [
    ("contact", re.compile(r"new point of contact is (?P<v>.+)$", re.I)),
    ("contact", re.compile(r"contact person changed to (?P<v>.+)$", re.I)),
    ("contact", re.compile(r"الشخص المسؤول بقى (?P<v>.+)$")),
    ("courier", re.compile(r"now ships via (?P<v>.+)$", re.I)),
    ("courier", re.compile(r"switch .+? to (?P<v>.+?) for deliveries$", re.I)),
    ("courier", re.compile(r"بقى يشحن مع (?P<v>.+)$")),
    ("terms", re.compile(r"payment terms are net (?P<v>\d+)$", re.I)),
    ("terms", re.compile(r"agreed net (?P<v>\d+) with", re.I)),
    ("terms", re.compile(r"صافي (?P<v>\d+) يوم")),
    ("city", re.compile(r"moved delivery to (?P<v>.+)$", re.I)),
    ("city", re.compile(r"shipping address is now in (?P<v>.+)$", re.I)),
    ("city", re.compile(r"عنوان الشحن إلى (?P<v>.+)$")),
]


@dataclass
class Parsed:
    kind: str  # claim | correction | retraction
    client: str
    attr: str | None = None
    value: str | None = None
    effective: date | None = None


def link_client(text: str, clients: list[str]) -> str | None:
    """Exact (case-insensitive) match first, then fuzzy match on same-length word windows."""
    t = " ".join(text.lower().split())
    for c in sorted(clients, key=len, reverse=True):
        if c.lower() in t:
            return c
    words = re.findall(r"[\w'’]+", t)
    best, best_r = None, 0.0
    for c in clients:
        k = len(c.split())
        for i in range(len(words) - k + 1):
            r = SequenceMatcher(None, " ".join(words[i:i + k]), c.lower()).ratio()
            if r > best_r:
                best, best_r = c, r
    return best if best_r >= 0.88 else None


def extract(text: str, clients: list[str]) -> Parsed | None:
    client = link_client(text, clients)
    if client is None:
        return None
    if RETRACTION.search(text):
        return Parsed("retraction", client)
    kind = "claim"
    body = text
    if CORRECTION.search(body):
        kind, body = "correction", CORRECTION.sub("", body, count=1)
    eff = None
    m = EFFECTIVE.search(body)
    if m:
        y, mo, d = map(int, m.group(1).split("-"))
        eff = date(y, mo, d)
        body = EFFECTIVE.sub("", body, count=1)
    body = " ".join(body.split()).strip(" .!")
    for attr, pat in PATTERNS:
        mm = pat.search(body)
        if mm:
            return Parsed(kind, client, attr, mm.group("v").strip(" .!"), eff)
    return None
