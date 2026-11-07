"""Bring your own agent.

Any class with a `name` and a `run(ticket, tools)` method can be evaluated. `tools` is the same
surface your production agent would call (lookup_order, issue_refund, ...). Wrap your LLM loop
inside `run` and AgentProof will sabotage its tool calls, grade the final world state, record
traces, and gate your CI on the result.

This example is an *ablation*: the hardened agent with its retries switched off. Run it with

    PYTHONPATH=src:. python -m agentproof compare --agents naive hardened examples.byo_agent:NoRetryAgent

to see which defence is actually carrying the weight.
"""
from agentproof.agents import HardenedAgent


class NoRetryAgent(HardenedAgent):
    name = "hardened-no-retry"
    ATTEMPTS = 1  # idempotency + validation + fail-safe stay on; retries off
