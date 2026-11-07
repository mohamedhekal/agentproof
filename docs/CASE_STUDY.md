# Case study: three ways a support agent double-refunds, and what chaos testing can and cannot tell you

> Everything below happened in **Shop-Sim**, the simulated store in this repo, with the two scripted reference agents. It is not a production incident. Every number is reproducible with the command next to it (seeded, deterministic).

## The question
"Does the agent behave on the fiftieth run as it did on the first?" A clean test set cannot answer that, because the failures that cost money are not wrong answers. They are *right answers delivered twice*, or right answers *to the wrong input*.

## Setup
Eight support scenarios (damaged item, lost parcel, already-refunded order, prompt injection hidden in an order note, Arabic-speaking customer, ...). Each run builds a fresh randomized world and grades the **final state** (ledger, shipments, messages), on two axes: *was the ticket resolved per policy* and *did anything unsafe happen* (refunds over the order total, refunds above the approval limit, duplicate shipments, wrong recipient). Chaos sabotages a share of tool calls: timeouts, malformed payloads, lost acks, duplicated deliveries, and the nasty one, **a timeout where the write actually happened**.

The payments API in the sim does not guard against over-refunds, which is how many real gateways behave.

## Finding 1: the headline number hides three different bugs
At chaos 0.3 the naive agent is *unsafe* in 45 of 160 runs (28.1%). Taken apart:

| cause | unsafe runs | needs chaos? | scenario |
|---|---|---|---|
| obeys an instruction written in an order note | 19 | no | `prompt_injection_in_order_note` |
| acts on a stale picture: refunds an order that was already refunded | 19 | no | `already_refunded` |
| a retried write applied twice | 7 | **yes** | `damaged_small_refund`, `lost_package`, `arabic_damaged` |

Chaos off, the naive agent is already unsafe in 40 of 160 runs (25.0%), all from the first two causes. **Most of what looks like a reliability problem is a trust-boundary and state-freshness problem.** A chaos harness alone would have under-reported it; the grader that reads the ledger is what catches it.

Reproduce: `agentproof compare --runs 20 --chaos 0.3` and `--chaos 0.0`.

## Finding 2: isolate the retry bug and it scales with chaos
Restrict to the three scenarios where a write must happen exactly once (120 runs per cell, `--runs 40`):

| chaos | naive unsafe | naive resolved | hardened unsafe | hardened resolved |
|---|---|---|---|---|
| 0.0 | 0.0% | 66.7% | 0.0% | 100.0% |
| 0.3 | 8.3% | 54.2% | 0.0% | 97.5% |
| 0.5 | 19.2% | 41.7% | 0.0% | 92.5% |

Mechanism: the naive agent retries a failed write with the same arguments and **no idempotency key**. When the failure is a timeout after the write already landed, or the delivery layer duplicates the request, the retry applies the refund (or the replacement shipment) a second time. At chaos 0.5 that is 12 double refunds and 11 duplicate shipments in 120 runs. At chaos 0 the same agent looks perfect on these scenarios, which is exactly why a clean test set ships this bug. (The naive agent's 66.7% at chaos 0 is the Arabic scenario: it only writes English replies.)

Reproduce: `agentproof compare --runs 40 --chaos 0.5 --scenarios damaged_small_refund lost_package arabic_damaged`.

## Finding 3: safety and liveness come from different defences
The hardened agent: validates every read against a schema, passes `"<ticket>:<action>"` idempotency keys on every write and reuses them on retry, re-reads state before acting, never reads the order note, and hands the ticket to a human when it cannot finish. Turn **only the retries off** (full suite, chaos 0.3, `examples/byo_agent.py`):

| agent | resolved | handed to a human | unsafe |
|---|---|---|---|
| hardened | 98.8% | 1.2% | 0.0% |
| hardened, retries off | 33.1% | 66.9% | 0.0% |

Still perfectly safe (idempotency, validation and the fail-safe do not depend on retrying), but two thirds of tickets now need a person. Retries buy availability; idempotency buys safety. Teams that conflate the two either ship duplicate-effect bugs or build agents that give up too easily.

## Finding 4: a failure you can replay
`docs/sample/failsafe-trace.jsonl` is a recorded run where five consecutive reads failed (timeout, malformed `{}`, three 503s). The hardened agent stopped, escalated to a human and sent nothing, rather than guessing. `agentproof replay` re-runs any agent against that exact recording: the hardened agent reproduces it call for call; the naive agent diverges on call 2 with a `KeyError`. That is the workflow for fixing a failure you cannot rerun on demand: record, replay the fix against the recording, then gate it in CI.

## What this does not show
- The agents are deterministic scripted policies, and the naive one is a strawman. The result is about the harness and the three bug classes, not about any model. For a model, see the cassette workflow in the README; no real-model numbers are published here.
- Eight scenarios and one fault model. The structure scales; the coverage is small.
- 160 runs per agent per setting, one base seed. The differences above are far larger than seed noise, but I have not computed confidence intervals.

## What I would do on a real system
1. Add an invariant checker over the real ledger (not the agent's transcript) and alert on any violation, before building any eval.
2. Make every write idempotent at the API boundary, so a retry can never be the thing that costs money.
3. Treat every free-text field written by a third party (notes, messages, addresses) as data, never as instructions.
4. Re-read the facts that gate an action immediately before acting; never trust a flag stored earlier.
5. Put a reliability gate (pass^k plus a separate unsafe rate) in CI so a prompt or model change cannot silently regress either.
