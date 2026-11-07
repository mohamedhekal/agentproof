"""Run agents against scenarios under chaos and compute reliability metrics."""
from __future__ import annotations

import importlib
import json
import random
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .agents import HardenedAgent, NaiveAgent
from .scenarios import SCENARIOS, Scenario
from .toolbox import ReplayDivergence, ReplayToolBox, ToolBox
from .world import Ticket

REGISTRY = {"naive": NaiveAgent, "hardened": HardenedAgent}


def load_agent(spec: str) -> type:
    """'naive' | 'hardened' | 'package.module:ClassName' (bring your own agent)."""
    if spec in REGISTRY:
        return REGISTRY[spec]
    if ":" not in spec:
        raise SystemExit(f"unknown agent '{spec}'. Use naive, hardened or module:Class")
    mod, cls = spec.split(":", 1)
    return getattr(importlib.import_module(mod), cls)


@dataclass
class RunResult:
    scenario: str
    seed: int
    status: str  # pass | safe_fail | unsafe
    unmet: list[str]
    unsafe: list[str]
    calls: int
    faults: int
    error: str | None
    ticket: dict[str, Any]
    events: list[dict[str, Any]] = field(repr=False, default_factory=list)


def run_one(agent_cls: type, sc: Scenario, seed: int, chaos: float) -> RunResult:
    world, ticket = sc.build(random.Random(f"{sc.name}|{seed}|world"))
    box = ToolBox(world, random.Random(f"{sc.name}|{seed}|chaos"), chaos)
    error = None
    try:
        agent_cls().run(ticket, box)
    except Exception as e:  # noqa: BLE001 - an agent crash is a result, not our crash
        error = f"{type(e).__name__}: {e}"
    unmet, unsafe = sc.grade(world, ticket)
    if error:
        unmet = [*unmet, f"crash:{error.split(':')[0]}"]
    status = "unsafe" if unsafe else ("pass" if not unmet else "safe_fail")
    return RunResult(sc.name, seed, status, unmet, unsafe, box.calls, box.faults, error, asdict(ticket), box.events)


@dataclass
class Suite:
    agent: str
    chaos: float
    runs: int
    results: list[RunResult]

    def metrics(self) -> dict[str, Any]:
        n = len(self.results)
        by_sc: dict[str, Counter] = {}
        reasons: Counter = Counter()
        for r in self.results:
            by_sc.setdefault(r.scenario, Counter())[r.status] += 1
            for u in r.unsafe:
                reasons[f"UNSAFE {u}"] += 1
            for u in r.unmet:
                reasons[u.split("=")[0].split(" ")[0]] += 1
        per = {
            s: {"pass": c["pass"], "safe_fail": c["safe_fail"], "unsafe": c["unsafe"], "runs": sum(c.values())}
            for s, c in by_sc.items()
        }
        all_pass = sum(1 for v in per.values() if v["pass"] == v["runs"])
        flaky = sorted(s for s, v in per.items() if 0 < v["pass"] < v["runs"])
        count = lambda st: sum(1 for r in self.results if r.status == st)  # noqa: E731
        return {
            "agent": self.agent,
            "chaos": self.chaos,
            "runs_per_scenario": self.runs,
            "total_runs": n,
            "pass_rate": round(count("pass") / n, 4),
            "safe_fail_rate": round(count("safe_fail") / n, 4),
            "unsafe_rate": round(count("unsafe") / n, 4),
            "reliability": round(all_pass / len(per), 4),  # scenarios where ALL runs passed (pass^k)
            "flaky_scenarios": flaky,
            "avg_tool_calls": round(sum(r.calls for r in self.results) / n, 2),
            "faults_injected": sum(r.faults for r in self.results),
            "failure_reasons": dict(reasons.most_common()),
            "per_scenario": per,
        }


def run_suite(agent_spec: str, runs: int = 20, chaos: float = 0.3, seed: int = 0, scenarios: list[Scenario] | None = None) -> Suite:
    cls = load_agent(agent_spec)
    results = [run_one(cls, sc, seed + i, chaos) for sc in (scenarios or SCENARIOS) for i in range(runs)]
    return Suite(getattr(cls, "name", agent_spec), chaos, runs, results)


# ------------------------------------------------------------------ traces & replay
def save_trace(r: RunResult, agent_spec: str, chaos: float, path: Path) -> None:
    header = {
        "scenario": r.scenario, "seed": r.seed, "agent": agent_spec, "chaos": chaos, "status": r.status,
        "unmet": r.unmet, "unsafe": r.unsafe, "error": r.error, "ticket": r.ticket,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        f.write(json.dumps({"header": header}, ensure_ascii=False) + "\n")
        for ev in r.events:
            f.write(json.dumps(ev, ensure_ascii=False) + "\n")


def load_trace(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    lines = [json.loads(x) for x in path.read_text().splitlines() if x.strip()]
    return lines[0]["header"], lines[1:]


def replay(path: Path, agent_spec: str | None = None) -> dict[str, Any]:
    """Re-run an agent against a recorded cassette: no world, no randomness, no network."""
    header, events = load_trace(path)
    cls = load_agent(agent_spec or header["agent"])
    box = ReplayToolBox(events)
    outcome, detail = "identical", ""
    try:
        cls().run(Ticket(**header["ticket"]), box)
        if not box.fully_consumed:
            outcome, detail = "diverged", f"agent stopped after {box.pos} of {len(events)} recorded calls"
    except ReplayDivergence as e:
        outcome, detail = "diverged", str(e)
    except Exception as e:  # noqa: BLE001
        outcome, detail = ("identical" if box.fully_consumed else "diverged"), f"agent raised {type(e).__name__}: {e}"
    return {"outcome": outcome, "detail": detail, "calls_matched": box.pos, "calls_recorded": len(events), "header": header}
