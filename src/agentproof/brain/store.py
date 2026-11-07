"""The Company Brain: an append-only, bitemporal claim log with provenance and conflict flags."""
from __future__ import annotations

from collections import defaultdict
from datetime import date

from .extract import extract
from .semantics import Answer, Claim, resolve


class Brain:
    name = "brain"

    def __init__(self, clients: list[str]) -> None:
        self.clients = clients
        self.by_key: dict[tuple[str, str], list[Claim]] = defaultdict(list)
        self.all: list[Claim] = []
        self.unparsed = 0

    def _active(self, client: str, attr: str | None = None) -> list[Claim]:
        cs = self.all if attr is None else self.by_key[(client, attr)]
        return [c for c in cs if c.client == client and c.retracted_at is None]

    def ingest(self, obs) -> None:  # obs: synth.Observation
        p = extract(obs.text, self.clients)
        if p is None:
            self.unparsed += 1
            return
        if p.kind == "retraction":
            # "ignore my last message about X": retract the newest live claim from the same sender about X
            mine = [c for c in self._active(p.client) if c.source == obs.source]
            if mine:
                max(mine, key=lambda c: (c.recorded_at, c.seq)).retracted_at = obs.recorded_at
            return
        valid_from = p.effective or obs.recorded_at
        if p.kind == "correction":
            live = self._active(p.client, p.attr)
            if live:
                target = max(live, key=lambda c: (c.recorded_at, c.seq))
                target.retracted_at = obs.recorded_at  # we no longer believe it, but we remember believing it
                valid_from = p.effective or target.valid_from  # a correction fixes the old claim's validity window
        claim = Claim(p.client, p.attr, p.value, valid_from, obs.recorded_at, obs.source, obs.id, obs.seq, obs.text, kind=p.kind)
        self.by_key[(p.client, p.attr)].append(claim)
        self.all.append(claim)

    def get(self, client: str, attr: str, valid_at: date, known_at: date) -> Answer | None:
        return resolve(self.by_key.get((client, attr), []), valid_at, known_at)

    def history(self, client: str, attr: str) -> list[Claim]:
        """Full audit trail, including claims we no longer believe."""
        return sorted(self.by_key.get((client, attr), []), key=lambda c: (c.recorded_at, c.seq))
