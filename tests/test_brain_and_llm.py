import json
import random
import statistics as st
from datetime import date

import pytest

from agentproof.brain.evaluate import evaluate
from agentproof.brain.extract import extract, link_client
from agentproof.brain.semantics import Claim, resolve
from agentproof.brain.store import Brain
from agentproof.brain.synth import Observation, generate
from agentproof.llm import (
    AnthropicClient, CassetteMiss, OpenAIClient, ReplayClient, RecordingClient, ScriptedModel, TOOL_SCHEMAS, request_key,
)
from agentproof.runner import run_suite

CLIENTS = ["Nile Textiles", "Delta Foods"]
D = date


# ---------------------------------------------------------------- extraction
@pytest.mark.parametrize("text,attr,value", [
    ("Nile Textiles: new point of contact is Mona Adel.", "contact", "Mona Adel"),
    ("Switch Delta Foods to Falcon for deliveries", "courier", "Falcon"),
    ("شروط الدفع مع Nile Textiles صافي 45 يوم", "terms", "45"),
    ("Delta Foods moved delivery to Tanta.", "city", "Tanta"),
])
def test_extracts_english_and_arabic_claims(text, attr, value):
    p = extract(text, CLIENTS)
    assert (p.attr, p.value) == (attr, value)


def test_extracts_effective_date_correction_and_retraction():
    p = extract("Correction: Nile Textiles now ships via NileGo (effective 2026-03-01)", CLIENTS)
    assert p.kind == "correction" and p.effective == D(2026, 3, 1) and p.value == "NileGo"
    assert extract("تجاهل رسالتي الأخيرة عن Delta Foods", CLIENTS).kind == "retraction"


def test_chatter_is_not_mistaken_for_a_fact():
    assert extract("Nile Textiles asked whether we could ship via Falcon, we said we'd think about it.", CLIENTS) is None


def test_fuzzy_client_linking_survives_a_typo():
    assert link_client("Nlie Textiles now ships via Falcon", CLIENTS) == "Nile Textiles"
    assert link_client("Acme Corp now ships via Falcon", CLIENTS) is None


# ---------------------------------------------------------------- bitemporal semantics
def claim(v, vf, rec, src="crm", seq=0, retracted=None, oid="O"):
    return Claim("C", "terms", v, vf, rec, src, oid, seq, retracted_at=retracted)


def test_valid_time_and_system_time_are_independent():
    cs = [claim("30", D(2026, 1, 1), D(2026, 1, 1), seq=0), claim("45", D(2026, 2, 1), D(2026, 3, 10), seq=1)]  # learned late
    assert resolve(cs, D(2026, 2, 15), D(2026, 3, 1)).value == "30"  # what we believed on Mar 1
    assert resolve(cs, D(2026, 2, 15), D(2026, 4, 1)).value == "45"  # what we know now about Feb 15


def test_retracted_claims_are_forgotten_only_after_the_retraction():
    cs = [claim("30", D(2026, 1, 1), D(2026, 1, 1), seq=0), claim("99", D(2026, 2, 1), D(2026, 2, 1), seq=1, retracted=D(2026, 2, 5))]
    assert resolve(cs, D(2026, 2, 3), D(2026, 2, 3)).value == "99"
    assert resolve(cs, D(2026, 2, 3), D(2026, 2, 6)).value == "30"


def test_conflict_is_flagged_and_higher_authority_wins():
    cs = [claim("30", D(2026, 1, 1), D(2026, 1, 1), "whatsapp", 0, oid="A"), claim("45", D(2026, 1, 1), D(2026, 1, 1), "finance", 1, oid="B")]
    a = resolve(cs, D(2026, 2, 1), D(2026, 2, 1))
    assert (a.value, a.obs_id, a.conflicted) == ("45", "B", True)


def test_brain_applies_correction_retraction_and_keeps_provenance():
    b = Brain(CLIENTS)
    feed = [
        ("crm", D(2026, 1, 1), "Nile Textiles payment terms are net 30."),
        ("sales", D(2026, 1, 10), "Nile Textiles payment terms are net 60."),
        ("sales", D(2026, 1, 12), "Please ignore my last message about Nile Textiles."),
        ("email", D(2026, 1, 20), "Correction: Nile Textiles payment terms are net 45."),
    ]
    for i, (s, d, t) in enumerate(feed):
        b.ingest(Observation(f"O{i}", s, d, t, i))
    assert b.get("Nile Textiles", "terms", D(2026, 1, 11), D(2026, 1, 11)).value == "60"  # believed that day
    assert b.get("Nile Textiles", "terms", D(2026, 1, 15), D(2026, 1, 15)).value == "30"  # retracted by then
    ans = b.get("Nile Textiles", "terms", D(2026, 2, 1), D(2026, 2, 1))
    assert (ans.value, ans.obs_id) == ("45", "O3")
    assert len(b.history("Nile Textiles", "terms")) == 3  # nothing is deleted


# ---------------------------------------------------------------- benchmark claims
def test_dataset_is_reproducible_and_messy():
    a, b = generate(3), generate(3)
    assert [o.text for o in a.observations] == [o.text for o in b.observations]
    assert any("effective" in o.text or "اعتبارًا" in o.text for o in a.observations)
    assert any(o.text.startswith(("Correction", "تصحيح")) for o in a.observations)


def test_brain_beats_rag_by_a_wide_margin_and_flags_conflicts():
    rs = [evaluate(s) for s in range(7, 12)]
    mean = lambda sysname, k: st.mean(r["systems"][sysname][k] for r in rs)  # noqa: E731
    assert mean("brain", "all") > 0.97
    assert mean("brain", "all") > mean("rag_recency", "all") + 0.15 > mean("rag_top1", "all")
    assert mean("brain", "provenance") > 0.95 and mean("rag_recency", "conflict_recall") == 0.0


def test_brain_degrades_honestly_on_phrasing_it_has_never_seen():
    clean = evaluate(7, unseen=0.0)["systems"]["brain"]["all"]
    messy = evaluate(7, unseen=0.3)["systems"]["brain"]["all"]
    assert messy < clean - 0.1


# ---------------------------------------------------------------- LLM adapter
def test_scripted_model_through_the_llm_loop_matches_the_hardened_agent():
    m = run_suite("scripted", runs=10, chaos=0.3).metrics()
    assert m["unsafe_rate"] == 0.0 and m["pass_rate"] > 0.95


def test_harness_catches_a_sloppy_model_through_the_llm_path():
    m = run_suite("scripted-sloppy", runs=10, chaos=0.3).metrics()
    assert m["unsafe_rate"] > 0.1


def test_cassette_replay_reproduces_a_recorded_run_exactly(tmp_path, monkeypatch):
    cas = tmp_path / "c.jsonl"
    monkeypatch.setenv("AGENTPROOF_CASSETTE", str(cas))
    live = run_suite("scripted", runs=4, chaos=0.3).metrics()
    monkeypatch.delenv("AGENTPROOF_CASSETTE")
    replayed = run_suite(f"replay:{cas}", runs=4, chaos=0.3).metrics()
    for k in ("pass_rate", "safe_fail_rate", "unsafe_rate", "reliability", "per_scenario"):
        assert live[k] == replayed[k]


def test_cassette_miss_is_loud_not_silent(tmp_path):
    p = tmp_path / "empty.jsonl"
    p.write_text("")
    with pytest.raises(CassetteMiss):
        ReplayClient(p).complete("s", [{"role": "user", "content": "x"}], TOOL_SCHEMAS)


def test_request_key_is_stable_and_sensitive():
    a = request_key("s", [{"role": "user", "content": "x"}], TOOL_SCHEMAS)
    assert a == request_key("s", [{"role": "user", "content": "x"}], TOOL_SCHEMAS)
    assert a != request_key("s", [{"role": "user", "content": "y"}], TOOL_SCHEMAS)


def test_recording_client_writes_each_request_once(tmp_path):
    class Fake:
        calls = 0

        def complete(self, s, m, t):
            Fake.calls += 1
            return {"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn"}

    rec = RecordingClient(Fake(), tmp_path / "r.jsonl")
    for _ in range(3):
        rec.complete("s", [{"role": "user", "content": "x"}], [])
    assert Fake.calls == 3 and len((tmp_path / "r.jsonl").read_text().splitlines()) == 1


def test_anthropic_client_request_shape():
    seen = {}

    def post(url, headers, body):
        seen.update(url=url, headers=headers, body=body)
        return {"content": [{"type": "text", "text": "hi"}], "stop_reason": "end_turn"}

    out = AnthropicClient("claude-x", api_key="k", post=post).complete("sys", [{"role": "user", "content": "x"}], TOOL_SCHEMAS)
    assert seen["url"].endswith("/v1/messages") and seen["headers"]["x-api-key"] == "k"
    assert "temperature" not in seen["body"] and seen["body"]["tools"] == TOOL_SCHEMAS and out["stop_reason"] == "end_turn"


def test_openai_translation_round_trip():
    msgs = [
        {"role": "user", "content": "ticket"},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "t1", "name": "lookup_order", "input": {"order_id": "A"}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "{}"}]},
    ]
    out, fns = OpenAIClient.to_openai("sys", msgs, TOOL_SCHEMAS)
    assert out[0]["role"] == "system" and out[2]["tool_calls"][0]["function"]["name"] == "lookup_order"
    assert out[3] == {"role": "tool", "tool_call_id": "t1", "content": "{}"} and fns[0]["type"] == "function"
    resp = {"choices": [{"message": {"content": None, "tool_calls": [{"id": "c1", "function": {"name": "reship", "arguments": json.dumps({"order_id": "A"})}}]}}]}
    back = OpenAIClient.from_openai(resp)
    assert back["stop_reason"] == "tool_use" and back["content"][0]["input"] == {"order_id": "A"}


def test_scripted_model_never_touches_the_network():
    r = ScriptedModel().complete("s", [{"role": "user", "content": "Ticket T-1\ncustomer_id: C1\norder_id: O1\nmessage: where is my order"}], TOOL_SCHEMAS)
    assert r["content"][0]["name"] == "lookup_order"
    random.seed(0)


def test_committed_claude_cassette_replays_offline():
    m = run_suite("replay:cassettes/claude.jsonl", runs=5, chaos=0.3).metrics()
    assert m["total_runs"] == 40 and m["unsafe_rate"] == 0.0 and m["pass_rate"] == 1.0
