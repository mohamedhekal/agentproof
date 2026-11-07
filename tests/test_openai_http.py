"""The OpenAI path over real HTTP, against a local server that speaks the Chat Completions protocol.

The fake server is independent of the client's own translation code: it validates the wire format
strictly (auth header, system message first, every `tool` message answering a tool_call id from the
preceding assistant message, tools shaped as {"type":"function","function":{...}}) and drives a fixed
script. This proves the HTTP + translation round trip. It does NOT prove behaviour of any OpenAI model.
"""
import json
import random
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from agentproof.llm import LLMAgent, OpenAIClient, TOOL_SCHEMAS
from agentproof.runner import run_one
from agentproof.scenarios import by_name


class _Handler(BaseHTTPRequestHandler):
    seen: list = []
    fail_first = 0

    def log_message(self, *a):  # silence
        pass

    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["content-length"])))
        _Handler.seen.append({"path": self.path, "auth": self.headers.get("authorization"), "body": req})
        if _Handler.fail_first > 0:
            _Handler.fail_first -= 1
            return self._send(429, {"error": {"message": "rate limited"}})
        assert self.path == "/v1/chat/completions"
        assert self.headers.get("authorization") == "Bearer test-key"
        msgs = req["messages"]
        assert msgs[0]["role"] == "system" and msgs[1]["role"] == "user"
        assert all(t["type"] == "function" and {"name", "description", "parameters"} <= set(t["function"]) for t in req["tools"])
        assert "temperature" not in req
        # every tool message must answer a tool_call of the nearest preceding assistant message
        last_calls: set = set()
        for m in msgs[2:]:
            if m["role"] == "assistant":
                last_calls = {c["id"] for c in m.get("tool_calls", [])}
                assert all(c["type"] == "function" and isinstance(c["function"]["arguments"], str) for c in m.get("tool_calls", []))
            elif m["role"] == "tool":
                assert m["tool_call_id"] in last_calls and isinstance(m["content"], str)
        fields = dict(line.split(": ", 1) for line in msgs[1]["content"].splitlines()[1:] if ": " in line)
        tid = msgs[1]["content"].splitlines()[0].split()[1]
        tools = [m for m in msgs if m["role"] == "tool"]
        n = len(tools)

        def call(name, args):
            return {"choices": [{"finish_reason": "tool_calls", "message": {"role": "assistant", "content": None, "tool_calls": [
                {"id": f"call_{n}", "type": "function", "function": {"name": name, "arguments": json.dumps(args)}}]}}]}

        if n == 0:
            return self._send(200, call("lookup_order", {"order_id": fields["order_id"]}))
        if n == 1:
            return self._send(200, call("get_customer", {"customer_id": fields["customer_id"]}))
        if n == 2:
            return self._send(200, call("get_tracking", {"order_id": fields["order_id"]}))
        if n == 3:
            trk = json.loads(tools[2]["content"])
            text = f"Order {fields['order_id']} is {trk['status']} with {trk['courier']}, arriving in {trk['eta_days']} day(s)."
            return self._send(200, call("send_message", {"customer_id": fields["customer_id"], "text": text, "idempotency_key": f"{tid}:reply"}))
        return self._send(200, {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": "Ticket handled."}}]})


@pytest.fixture()
def server():
    _Handler.seen, _Handler.fail_first = [], 0
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}/v1"
    srv.shutdown()


def _agent(base_url):
    class A(LLMAgent):
        name = "openai-http"
        _make_client = staticmethod(lambda: OpenAIClient("test-model", api_key="test-key", base_url=base_url))

    return A


def test_full_agent_episode_over_http_resolves_a_ticket(server):
    sc = by_name("where_is_my_order")
    r = run_one(_agent(server), sc, seed=1, chaos=0.0)
    assert r.status == "pass", (r.unmet, r.unsafe, r.error)
    assert [e["tool"] for e in r.events] == ["lookup_order", "get_customer", "get_tracking", "send_message"]
    assert len(_Handler.seen) == 5 and all(s["auth"] == "Bearer test-key" for s in _Handler.seen)


def test_tool_faults_reach_the_model_as_tool_messages(server):
    sc = by_name("where_is_my_order")
    r = run_one(_agent(server), sc, seed=1, chaos=1.0)  # every call sabotaged: the loop must survive and report, not crash the harness
    assert r.status in ("safe_fail", "pass", "unsafe")
    assert any("ERROR" in m["content"] or m["content"] in ("null", "{}") or m["content"].startswith("{")
               for s in _Handler.seen for m in s["body"]["messages"] if m["role"] == "tool")


def test_rate_limits_are_retried_with_backoff(server, monkeypatch):
    import agentproof.llm as llm

    monkeypatch.setattr("time.sleep", lambda s: None)
    _Handler.fail_first = 2
    out = OpenAIClient("m", api_key="test-key", base_url=server).complete("sys", [{"role": "user", "content": "Ticket T-1\ncustomer_id: C\norder_id: O\nmessage: hi"}], TOOL_SCHEMAS)
    assert out["stop_reason"] == "tool_use" and len(_Handler.seen) == 3


def test_invalid_tool_arguments_become_a_recoverable_tool_error():
    resp = {"choices": [{"message": {"content": None, "tool_calls": [{"id": "c1", "function": {"name": "reship", "arguments": "{not json"}}]}}]}
    block = OpenAIClient.from_openai(resp)["content"][0]
    assert "__invalid_json__" in block["input"]

    class Client:  # first turn: broken arguments; second turn: finish
        n = 0

        def complete(self, system, messages, tools):
            Client.n += 1
            if Client.n == 1:
                return {"content": [block], "stop_reason": "tool_use"}
            last = messages[-1]["content"][0]
            assert last["is_error"] and "bad tool call" in last["content"]
            return {"content": [{"type": "text", "text": "ok"}], "stop_reason": "end_turn"}

    class A(LLMAgent):
        _make_client = staticmethod(lambda: Client())

    sc = by_name("where_is_my_order")
    world, ticket = sc.build(random.Random(0))
    from agentproof.toolbox import ToolBox

    A().run(ticket, ToolBox(world, random.Random(0)))
    assert Client.n == 2


def test_refusals_and_content_parts_do_not_crash_parsing():
    assert OpenAIClient.from_openai({"choices": [{"message": {"content": None, "refusal": "no"}}]})["content"][0]["text"] == "[refusal] no"
    parts = {"choices": [{"message": {"content": [{"type": "text", "text": "a"}, {"type": "text", "text": "b"}]}}]}
    assert OpenAIClient.from_openai(parts)["content"][0]["text"] == "a b"
