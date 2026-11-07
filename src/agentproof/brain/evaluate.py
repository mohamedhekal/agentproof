"""Brain vs RAG benchmark on the synthetic operational history."""
from __future__ import annotations

from collections import defaultdict
from typing import Any

from .rag import RagMemory
from .semantics import norm
from .store import Brain
from .synth import generate


def evaluate(seed: int = 7, n_clients: int = 25, days: int = 180, n_events: int = 420, noise: float = 0.08, unseen: float = 0.0) -> dict[str, Any]:
    ds = generate(seed, n_clients, days, n_events, noise, unseen)
    systems = [Brain(ds.clients), RagMemory(ds.clients, "top1"), RagMemory(ds.clients, "recency")]
    for s in systems:
        for o in ds.observations:
            s.ingest(o)

    out: dict[str, Any] = {
        "seed": seed,
        "unseen_phrasing": unseen,
        "observations": len(ds.observations),
        "questions": len(ds.questions),
        "tricky_questions": sum(q.tricky for q in ds.questions),
        "systems": {},
    }
    for s in systems:
        acc: dict[str, list[int]] = defaultdict(list)
        prov: list[int] = []
        tp = fp = fn = 0
        for q in ds.questions:
            a = s.get(q.client, q.attr, q.valid_at, q.known_at)
            ok = int(a is not None and norm(a.value) == norm(q.truth.value))
            acc[q.kind].append(ok)
            acc["all"].append(ok)
            acc["tricky" if q.tricky else "plain"].append(ok)
            if q.kind == "current":
                prov.append(int(a is not None and a.obs_id == q.truth.obs_id))
                pred = bool(a and a.conflicted)
                tp += pred and q.truth.conflicted
                fp += pred and not q.truth.conflicted
                fn += (not pred) and q.truth.conflicted
        rate = lambda xs: round(sum(xs) / len(xs), 4) if xs else None  # noqa: E731
        out["systems"][s.name] = {
            **{k: rate(v) for k, v in acc.items()},
            "provenance": rate(prov),
            "conflict_recall": round(tp / (tp + fn), 4) if (tp + fn) else None,
            "conflict_precision": round(tp / (tp + fp), 4) if (tp + fp) else None,
        }
    out["conflicted_current"] = sum(1 for q in ds.questions if q.kind == "current" and q.truth.conflicted)
    out["brain_unparsed_messages"] = systems[0].unparsed
    return out
