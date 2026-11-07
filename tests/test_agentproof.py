import random

import pytest

from agentproof import cli
from agentproof.runner import replay, run_one, run_suite, save_trace
from agentproof.scenarios import SCENARIOS, by_name
from agentproof.toolbox import ReplayDivergence, ReplayToolBox, ToolBox
from agentproof.trust import CalibratedRouter, simulate, wilson_lcb
from agentproof.world import ToolTimeout


def fresh(name="damaged_small_refund", seed=1):
    return by_name(name).build(random.Random(seed))


# ---------------------------------------------------------------- world & faults
def test_idempotency_key_makes_writes_safe_to_retry():
    w, t = fresh()
    a = w.issue_refund(t.order_id, 10.0, idempotency_key="k")
    b = w.issue_refund(t.order_id, 10.0, idempotency_key="k")
    assert a == b and len(w.refunds) == 1


def test_gateway_does_not_guard_double_refunds_without_key():
    w, t = fresh()
    w.issue_refund(t.order_id, 10.0)
    w.issue_refund(t.order_id, 10.0)
    assert len(w.refunds) == 2


def test_timeout_applied_really_applies_the_write():
    w, t = fresh()
    box = ToolBox(w, random.Random(0))
    with pytest.raises(ToolTimeout):
        box._dispatch("issue_refund", {"order_id": t.order_id, "amount": 5.0, "idempotency_key": None}, "timeout_applied")
    assert len(w.refunds) == 1


def test_duplicate_fault_applies_twice_without_key_once_with_key():
    w, t = fresh()
    box = ToolBox(w, random.Random(0))
    box._dispatch("issue_refund", {"order_id": t.order_id, "amount": 5.0, "idempotency_key": None}, "duplicate")
    assert len(w.refunds) == 2
    w2, t2 = fresh()
    box2 = ToolBox(w2, random.Random(0))
    box2._dispatch("issue_refund", {"order_id": t2.order_id, "amount": 5.0, "idempotency_key": "k"}, "duplicate")
    assert len(w2.refunds) == 1


# ---------------------------------------------------------------- determinism & headline claims
def test_runs_are_reproducible():
    a = run_suite("naive", runs=5, chaos=0.3, seed=3).metrics()
    b = run_suite("naive", runs=5, chaos=0.3, seed=3).metrics()
    assert a == b


@pytest.mark.parametrize("chaos", [0.0, 0.3, 0.5])
def test_hardened_never_does_anything_unsafe(chaos):
    m = run_suite("hardened", runs=15, chaos=chaos).metrics()
    assert m["unsafe_rate"] == 0.0


def test_hardened_is_perfect_without_chaos():
    assert run_suite("hardened", runs=10, chaos=0.0).metrics()["pass_rate"] == 1.0


def test_naive_is_caught_doing_unsafe_things():
    m = run_suite("naive", runs=10, chaos=0.3).metrics()
    assert m["unsafe_rate"] > 0.1
    assert any(k.startswith("UNSAFE") for k in m["failure_reasons"])


def test_prompt_injection_is_caught_for_naive_and_resisted_by_hardened():
    sc = by_name("prompt_injection_in_order_note")
    assert run_one(__import__("agentproof.agents", fromlist=["x"]).NaiveAgent, sc, 0, 0.0).status == "unsafe"
    assert run_one(__import__("agentproof.agents", fromlist=["x"]).HardenedAgent, sc, 0, 0.0).status == "pass"


def test_every_scenario_is_passable_in_a_clean_world():
    m = run_suite("hardened", runs=3, chaos=0.0).metrics()
    assert set(m["per_scenario"]) == {s.name for s in SCENARIOS}
    assert all(v["pass"] == v["runs"] for v in m["per_scenario"].values())


# ---------------------------------------------------------------- replay
def test_replay_is_identical_for_same_agent_and_diverges_for_a_different_one(tmp_path):
    suite = run_suite("hardened", runs=10, chaos=0.5)
    bad = next(r for r in suite.results if r.status != "pass")
    p = tmp_path / "t.jsonl"
    save_trace(bad, "hardened", 0.5, p)
    assert replay(p)["outcome"] == "identical"
    assert replay(p, "naive")["outcome"] == "diverged"


def test_replay_toolbox_detects_argument_divergence():
    box = ReplayToolBox([{"i": 1, "tool": "lookup_order", "args": {"order_id": "A"}, "fault": None, "result": {}}])
    with pytest.raises(ReplayDivergence):
        box.lookup_order("B")


# ---------------------------------------------------------------- gate
def test_gate_passes_for_hardened_and_fails_for_naive(tmp_path, capsys):
    base = str(tmp_path / "b.json")
    assert cli.main(["gate", "--update", "--baseline", base, "--runs", "10"]) == 0
    assert cli.main(["gate", "--baseline", base, "--runs", "10"]) == 0
    assert cli.main(["gate", "--agent", "naive", "--baseline", base, "--runs", "10"]) == 1
    assert "GATE FAILED" in capsys.readouterr().out


# ---------------------------------------------------------------- calibrated autonomy
def test_router_asks_when_cold_goes_auto_when_proven_and_reverts_on_drift():
    r = CalibratedRouter(seed=1)
    assert r.decide("x", 10) == "ask"
    for _ in range(100):
        r.feedback("x", True)
    assert r.decide("x", 10) == "auto"
    assert r.decide("x", 10_000) == "ask"  # hard cap always asks
    for _ in range(40):
        r.feedback("x", False)  # audits start failing
    assert r.decide("x", 10) == "ask"


def test_wilson_bound_is_conservative():
    assert wilson_lcb(0, 0) == 0.0
    assert wilson_lcb(10, 10) < 1.0
    assert wilson_lcb(100, 100) > wilson_lcb(10, 10)


def test_calibrated_beats_static_on_safety_and_always_ask_on_effort():
    p = simulate()["policies"]
    assert p["calibrated"]["bad_auto_rate"] < p["static_threshold"]["bad_auto_rate"] / 5
    assert p["calibrated"]["ask_rate"] < p["always_ask"]["ask_rate"]
