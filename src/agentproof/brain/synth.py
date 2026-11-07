"""Synthetic, messy, multi-month operational history (all invented, none real).

Generates a stream of short messages (WhatsApp / email / CRM / sales / finance) about client accounts:
plain updates, retroactive changes ("effective <earlier date>"), corrections, retractions
("ignore my last message"), same-day conflicts between sources, typos in client names, English and
Egyptian Arabic, plus chatter that mentions clients but states no fact. The generator also keeps the
ground-truth claim log, so every question has a known right answer.
"""
from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from .semantics import Answer, Claim, authority, resolve

ATTRS = ("contact", "courier", "terms", "city")
POOLS = {
    "contact": ["Ahmed Samir", "Mona Adel", "Karim Fathy", "Hala Nabil", "Omar Khaled", "Salma Reda", "Tarek Wagdy", "Dina Magdy", "Yassin Hamed", "Nour Essam"],
    "courier": ["SwiftEx", "NileGo", "Falcon", "Delta Post", "RapidBox"],
    "terms": ["15", "30", "45", "60"],
    "city": ["Cairo", "Giza", "Alexandria", "Mansoura", "Tanta", "Assiut", "Luxor", "Aswan"],
}
SOURCES = ["whatsapp", "email", "sales", "crm", "finance"]
FIRST = ["Nile", "Delta", "Pyramid", "Sphinx", "Karnak", "Giza", "Cairo", "Luxor", "Aswan", "Siwa", "Memphis", "Thebes"]
SECOND = ["Textiles", "Foods", "Tech", "Logistics", "Pharma", "Furniture", "Plastics", "Retail"]

TEMPLATES = {
    # index 0-1 English, 2 Egyptian Arabic, 3 = held-out phrasing the extractor has never seen
    "contact": ["{c}: new point of contact is {v}.", "{c} - contact person changed to {v}", "بالنسبة لـ {c} الشخص المسؤول بقى {v}", "{c}: please direct everything to {v} from now on"],
    "courier": ["{c} now ships via {v}.", "Switch {c} to {v} for deliveries", "{c} بقى يشحن مع {v}", "{c} deliveries are handled by {v} these days"],
    "terms": ["{c} payment terms are net {v}.", "Agreed net {v} with {c}", "شروط الدفع مع {c} صافي {v} يوم", "{c} settles invoices within {v} days now"],
    "city": ["{c} moved delivery to {v}.", "{c}'s shipping address is now in {v}", "{c} غيّر عنوان الشحن إلى {v}", "{c}: send parcels to {v} instead"],
}
RETRACT = ["Please ignore my last message about {c}.", "Ignore the previous note about {c}, sorry", "تجاهل رسالتي الأخيرة عن {c}"]
CHATTER = [
    "{c}: thanks, will review the invoice tomorrow.",
    "Call {c} back about the delivery schedule.",
    "{c} asked whether we could ship via {x}, we said we'd think about it.",
    "Reminder: {c} wants to discuss payment terms next week.",
    "{c} is considering moving their delivery address, nothing decided yet.",
    "فكّر {c} يغيّر شروط الدفع بس لسه مفيش قرار",
]


@dataclass
class Observation:
    id: str
    source: str
    recorded_at: date
    text: str
    seq: int


@dataclass
class Question:
    kind: str  # current | valid_at | belief_at
    client: str
    attr: str
    valid_at: date
    known_at: date
    truth: Answer
    tricky: bool  # this (client, attr) history contains a retro/correction/retraction/conflict


@dataclass
class Dataset:
    clients: list[str]
    observations: list[Observation]
    claims: list[Claim]
    questions: list[Question]
    start: date
    end: date


def _garble(rng: random.Random, text: str, client: str, noise: float) -> str:
    if rng.random() >= noise:
        return text
    kind = rng.choice(["lower", "typo", "space"])
    if kind == "lower":
        return text.lower()
    if kind == "space":
        i = text.find(" ")
        return text[:i] + "  " + text[i + 1:] if i > 0 else text
    i = text.find(client)
    if i < 0 or len(client) < 5:
        return text
    j = i + rng.randint(1, len(client) - 3)
    c = text[j:j + 2]
    return text[:j] + c[::-1] + text[j + 2:]


def generate(seed: int = 7, n_clients: int = 25, days: int = 180, n_events: int = 420, noise: float = 0.08, unseen: float = 0.0) -> Dataset:
    rng = random.Random(seed)
    names: list[str] = []
    while len(names) < n_clients:
        n = f"{rng.choice(FIRST)} {rng.choice(SECOND)}"
        if n not in names:
            names.append(n)
    start = date(2026, 1, 1)
    obs: list[Observation] = []
    truth: list[Claim] = []
    tags: dict[tuple[str, str], set[str]] = defaultdict(set)

    def day_of(d: int) -> date:
        return start + timedelta(days=d)

    def add_obs(d: int, source: str, text: str, client: str) -> Observation:
        o = Observation(f"O{len(obs) + 1:04d}", source, day_of(d), _garble(rng, text, client, noise), len(obs))
        obs.append(o)
        return o

    def add_claim(o: Observation, client: str, attr: str, value: str, valid_from: date, kind: str) -> Claim:
        c = Claim(client, attr, value, valid_from, o.recorded_at, o.source, o.id, o.seq, o.text, kind=kind)
        truth.append(c)
        return c

    def live(client: str, attr: str | None = None) -> list[Claim]:
        return [c for c in truth if c.client == client and (attr is None or c.attr == attr) and c.retracted_at is None]

    def newest(cs: list[Claim]) -> Claim:
        return max(cs, key=lambda c: (c.recorded_at, c.seq))

    def text_for(attr: str, client: str, value: str, lang: int, effective: date | None = None, correction: bool = False) -> str:
        t = TEMPLATES[attr][lang].format(c=client, v=value)
        if effective:
            t += f" اعتبارًا من {effective}" if lang == 2 else f" (effective {effective})"
        if correction:
            t = ("تصحيح: " if lang == 2 else "Correction: ") + t
        return t

    def fresh_value(client: str, attr: str) -> str:
        cur = newest(live(client, attr)).value
        return rng.choice([v for v in POOLS[attr] if v != cur])

    for c in names:  # onboarding
        for a in ATTRS:
            v = rng.choice(POOLS[a])
            o = add_obs(0, "crm", text_for(a, c, v, 0), c)
            add_claim(o, c, a, v, day_of(0), "update")

    kinds = ["update"] * 45 + ["retro"] * 12 + ["correction"] * 10 + ["conflict"] * 9 + ["retraction"] * 6 + ["noise"] * 18
    for d in sorted(rng.randint(1, days - 1) for _ in range(n_events)):
        kind = rng.choice(kinds)
        c, a = rng.choice(names), rng.choice(ATTRS)
        lang = 3 if rng.random() < unseen else rng.choice([0, 0, 1, 2])
        src = rng.choice(SOURCES)
        if kind == "retro":
            last = newest(live(c, a))
            gap = (day_of(d) - last.valid_from).days
            if gap < 3:
                kind = "update"
            else:
                eff = last.valid_from + timedelta(days=rng.randint(1, gap - 1))
                v = fresh_value(c, a)
                o = add_obs(d, src, text_for(a, c, v, lang, effective=eff), c)
                add_claim(o, c, a, v, eff, "retro")
                tags[(c, a)].add("retro")
                continue
        if kind == "correction":
            target = newest(live(c, a))
            v = fresh_value(c, a)
            target.retracted_at = day_of(d)
            o = add_obs(d, src, text_for(a, c, v, lang, correction=True), c)
            add_claim(o, c, a, v, target.valid_from, "correction")
            tags[(c, a)].add("correction")
            continue
        if kind == "conflict":
            hi_lo = rng.sample(SOURCES, 2)
            if authority(a, hi_lo[0]) == authority(a, hi_lo[1]):
                kind = "update"
            else:
                v1 = fresh_value(c, a)
                v2 = rng.choice([v for v in POOLS[a] if v != v1])
                for s, v in zip(hi_lo, (v1, v2)):
                    o = add_obs(d, s, text_for(a, c, v, lang), c)
                    add_claim(o, c, a, v, day_of(d), "conflict")
                tags[(c, a)].add("conflict")
                continue
        if kind == "retraction":
            done = False
            for _ in range(8):
                cand = rng.choice(live(c))
                if cand.recorded_at <= day_of(0):
                    continue
                mine = [x for x in live(c) if x.source == cand.source]
                same_attr = live(c, cand.attr)
                if newest(mine) is cand and newest(same_attr) is cand and len(same_attr) > 1:
                    o = add_obs(d, cand.source, RETRACT[lang if lang < 3 else 0].format(c=c), c)
                    cand.retracted_at = o.recorded_at
                    tags[(c, cand.attr)].add("retraction")
                    done = True
                    break
            if done:
                continue
            kind = "noise"
        if kind == "noise":
            add_obs(d, src, rng.choice(CHATTER).format(c=c, x=rng.choice(POOLS["courier"])), c)
            continue
        v = fresh_value(c, a)  # plain update
        o = add_obs(d, src, text_for(a, c, v, lang), c)
        add_claim(o, c, a, v, day_of(d), "update")

    end = day_of(days)
    qs: list[Question] = []
    for c in names:
        for a in ATTRS:
            cs = [x for x in truth if x.client == c and x.attr == a]
            tricky = bool(tags.get((c, a)))
            d1, d2 = day_of(rng.randint(10, days - 1)), day_of(rng.randint(10, days))
            for kind, va, ka in (("current", end, end), ("valid_at", d1, end), ("belief_at", d2, d2)):
                ans = resolve(cs, va, ka)
                if ans is not None:
                    qs.append(Question(kind, c, a, va, ka, ans, tricky))
    return Dataset(names, obs, truth, qs, start, end)

