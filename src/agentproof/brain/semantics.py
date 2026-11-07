"""Bitemporal claim semantics shared by the generator's ground truth and the Brain.

A *claim* says "client C has value V for attribute A", with two time axes:

* valid time    - when the fact is true in the world (`valid_from`)
* system time   - when we learned it (`recorded_at`), and when we stopped believing it (`retracted_at`)

Resolution at (valid_at, known_at): consider claims we knew about and still believed at `known_at`,
whose `valid_from <= valid_at`; the newest `valid_from` wins; ties are broken by source authority,
then by recency. If several distinct values share the winning `valid_from`, the answer is flagged
`conflicted`. Every answer carries the claim it came from (provenance).

What the benchmark tests is NOT this function (both sides share it) but whether a system can
rebuild the right claim log from messy messages: corrections, retroactive dates, retractions,
conflicting sources, typos, Arabic.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date

BASE_AUTHORITY = {"whatsapp": 1, "email": 2, "sales": 2, "crm": 3, "finance": 3}


def authority(attr: str, source: str) -> int:
    if attr == "terms" and source == "finance":
        return 4  # finance is the source of truth for payment terms
    return BASE_AUTHORITY.get(source, 1)


@dataclass
class Claim:
    client: str
    attr: str
    value: str
    valid_from: date
    recorded_at: date
    source: str
    obs_id: str
    seq: int
    quote: str = ""
    retracted_at: date | None = None
    kind: str = "update"


@dataclass(frozen=True)
class Answer:
    value: str
    obs_id: str
    source: str
    conflicted: bool = False


def norm(v: str) -> str:
    return " ".join(v.lower().split())


def resolve(claims: list[Claim], valid_at: date, known_at: date) -> Answer | None:
    """`claims` must already be restricted to one (client, attr)."""
    live = [
        c for c in claims
        if c.recorded_at <= known_at and (c.retracted_at is None or c.retracted_at > known_at) and c.valid_from <= valid_at
    ]
    if not live:
        return None
    top_vf = max(c.valid_from for c in live)
    top = [c for c in live if c.valid_from == top_vf]
    win = max(top, key=lambda c: (authority(c.attr, c.source), c.recorded_at, c.seq))
    return Answer(win.value, win.obs_id, win.source, len({norm(c.value) for c in top}) > 1)
