"""The baseline: plain retrieval-augmented memory.

Every message is a chunk. A question retrieves the top-k chunks by TF-IDF, and a *reader* pulls the
value out of the best chunk that is actually about that client and attribute. The reader is the same
extractor the Brain uses, so the comparison isolates the memory architecture, not parsing skill.

* `rag_top1`    - answer from the highest-scoring matching chunk
* `rag_recency` - among the top-k matching chunks, answer from the newest (the standard fix)

Both get a metadata filter: for "as of D" questions only chunks recorded on or before D are searched.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from datetime import date

from .extract import extract
from .semantics import Answer

ATTR_WORDS = {
    "contact": "contact person point of contact الشخص المسؤول",
    "courier": "ships via courier deliveries يشحن مع",
    "terms": "payment terms net agreed شروط الدفع صافي",
    "city": "delivery address shipping moved الشحن عنوان",
}
TOK = re.compile(r"[\w]+", re.U)


def _tokens(s: str) -> list[str]:
    return [t.lower() for t in TOK.findall(s)]


class RagMemory:
    def __init__(self, clients: list[str], mode: str = "recency", k: int = 8) -> None:
        self.clients, self.mode, self.k = clients, mode, k
        self.name = f"rag_{'recency' if mode == 'recency' else 'top1'}"
        self.docs: list = []
        self.tf: list[Counter] = []
        self.df: Counter = Counter()

    def ingest(self, obs) -> None:
        toks = Counter(_tokens(obs.text))
        self.docs.append(obs)
        self.tf.append(toks)
        for t in toks:
            self.df[t] += 1

    def _score(self, q: list[str], i: int) -> float:
        n = len(self.docs)
        return sum(self.tf[i][t] * math.log(1 + n / (1 + self.df[t])) for t in q if t in self.tf[i])

    def get(self, client: str, attr: str, valid_at: date, known_at: date) -> Answer | None:
        cutoff = known_at if known_at < valid_at else valid_at
        q = _tokens(client) + _tokens(ATTR_WORDS[attr])
        ranked = sorted(
            (i for i, d in enumerate(self.docs) if d.recorded_at <= cutoff),
            key=lambda i: -self._score(q, i),
        )[: self.k]
        hits = []
        for i in ranked:
            p = extract(self.docs[i].text, self.clients)
            if p and p.client == client and p.attr == attr and p.kind in ("claim", "correction"):
                hits.append(self.docs[i])
        if not hits:
            return None
        pick = hits[0] if self.mode == "top1" else max(hits, key=lambda d: (d.recorded_at, d.seq))
        p = extract(pick.text, self.clients)
        return Answer(p.value, pick.id, pick.source, False)
