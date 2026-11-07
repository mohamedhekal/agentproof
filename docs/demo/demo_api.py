"""Glue between the browser demo and the real AgentProof package (runs inside Pyodide).

Every function returns a JSON string. Nothing here is special-cased for the demo: it calls the same
`run_suite`, `replay`, `evaluate` and `simulate` functions the CLI uses.
"""
from __future__ import annotations

import json
from pathlib import Path

from agentproof.agents import HardenedAgent
from agentproof.brain.evaluate import evaluate
from agentproof.runner import replay, run_suite, save_trace
from agentproof.trust import simulate

ROOT = Path("/home/pyodide")


class NoRetryAgent(HardenedAgent):
    """The hardened agent with retries switched off (the ablation from the README)."""

    name = "hardened-no-retry"
    ATTEMPTS = 1


AGENTS = {"naive": "naive", "hardened": "hardened", "hardened-no-retry": "demo_api:NoRetryAgent"}
_LAST: dict[tuple[str, str, int], tuple] = {}


def run_compare(chaos: float, runs: int, seed: int, labels_json: str) -> str:
    labels = json.loads(labels_json)
    _LAST.clear()
    agents, failures = {}, []
    for label in labels:
        suite = run_suite(AGENTS[label], int(runs), float(chaos), int(seed))
        agents[label] = suite.metrics()
        for r in suite.results:
            _LAST[(label, r.scenario, r.seed)] = (r, AGENTS[label], float(chaos))
            if r.status != "pass":
                failures.append({"agent": label, "scenario": r.scenario, "seed": r.seed, "status": r.status, "reasons": r.unsafe or r.unmet})
    failures.sort(key=lambda f: ({"unsafe": 0, "safe_fail": 1}[f["status"]], f["agent"], f["scenario"], f["seed"]))
    return json.dumps({"chaos": chaos, "runs": runs, "seed": seed, "agents": agents, "failures": failures})


def get_trace(label: str, scenario: str, seed: int) -> str:
    r, _spec, chaos = _LAST[(label, scenario, int(seed))]
    return json.dumps({
        "agent": label, "scenario": scenario, "seed": r.seed, "chaos": chaos, "status": r.status,
        "ticket": r.ticket["text"], "unsafe": r.unsafe, "unmet": r.unmet, "error": r.error, "events": r.events,
    })


def replay_trace(label: str, scenario: str, seed: int, as_label: str) -> str:
    r, spec, chaos = _LAST[(label, scenario, int(seed))]
    path = ROOT / "replay_demo.jsonl"
    save_trace(r, spec, chaos, path)
    out = replay(path, AGENTS[as_label])
    out.pop("header", None)
    out["replayed_with"] = as_label
    return json.dumps(out)


def claude_replay() -> str:
    suite = run_suite(f"replay:{ROOT}/cassettes/claude.jsonl", 5, 0.3, 0)
    m = suite.metrics()
    m["model_responses_replayed"] = sum(1 for _ in open(ROOT / "cassettes" / "claude.jsonl"))
    return json.dumps(m)


def run_brain(seeds: int) -> str:
    import statistics as st

    rows = []
    for unseen in (0.0, 0.15):
        rs = [evaluate(s, unseen=unseen) for s in range(7, 7 + int(seeds))]
        for name in rs[0]["systems"]:
            rows.append({
                "unseen": unseen, "system": name,
                "all": st.mean(r["systems"][name]["all"] for r in rs),
                "tricky": st.mean(r["systems"][name]["tricky"] for r in rs),
                "provenance": st.mean(r["systems"][name]["provenance"] for r in rs),
            })
    return json.dumps({"seeds": int(seeds), "rows": rows})


def run_autonomy() -> str:
    return json.dumps(simulate())
