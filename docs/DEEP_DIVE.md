# Deep-dive worksheet: "an agent system I shipped: what broke, what I measured"

A **worksheet, not a story**. Facts and numbers must come from the production system; nothing here is invented. Fill every blank with something you can show (a log line, a dashboard, a commit, a query). If you cannot show it, cut it. A long technical deep dive rewards the person who can say "here is the query" and punishes the one who says "roughly".

Keep your filled-in copy **outside** any public repository: it will contain real incident details.

## 1. The system in 90 seconds
- What the agent does, for whom, with what authority (what it can *do*, not what it can *say*):
- Volume (tickets / calls / orders per day) and the share handled without a human:
- Model(s), fallbacks, and what happens when the model is down:
- Tools it can call, and which of them move money or change customer-visible state:
- Where a human is pulled in today, and who decided that line:

## 2. Failure #1 / #2 / #3 (one page each, same shape)

| field | your answer |
|---|---|
| What broke (one sentence, user-visible symptom) | |
| How you found out (alert, complaint, audit, by luck) | |
| How long it ran before you noticed | |
| Blast radius (customers / orders / money) | |
| Root cause (the mechanism, not "the model hallucinated") | |
| What you measured to confirm it (query, metric, sample size) | |
| The fix | |
| How you know the fix worked (before/after number) | |
| The regression test / eval that now guards it | |
| What you would do differently | |

Map each failure to a class. AgentProof has a scenario for each, which gives you a second, reproducible demo:

| class | example symptom | AgentProof scenario |
|---|---|---|
| non-idempotent retry | customer confirmed or refunded twice after a timeout or duplicate webhook | `damaged_small_refund`, `already_refunded` under chaos |
| trusting untrusted text | an instruction inside a customer message or order note was obeyed | `prompt_injection_in_order_note` |
| acting without authority | agent did something that needed a human | `damaged_high_value`, `delivered_but_not_received` |
| silent bad tool output | malformed or empty API reply treated as success | read fault `malformed` |
| stale or contradictory memory | agent acted on an address or price that was superseded or disputed | `agentproof brain` |
| dependency outage | model or gateway down, agent froze or guessed | fail-safe escalation trace |

## 3. Finding your candidates
Go through your own commit history, incident notes and support escalations for: fallbacks you added when a model or provider was down, parsing or pricing mistakes an agent made, token or cost reductions, places where internal notes could reach the wrong audience, and every rule of the form "this needs a human to approve". Each rule like that is a human-in-the-loop decision: write down the incident that made you draw the line. Those are your best material for "approvals that pull a human in at exactly the right moment".

## 4. Evals: what you actually trusted
- The metric you used to decide ship / don't ship:
- How the eval set was built (real tickets? sampled how? labelled by whom?):
- A time the eval said "fine" and production disagreed, and why:
- A time the eval blocked a change that felt fine:
- What AgentProof adds (chaos + a separate safety axis + replay + a CI gate), in your words, with the 160-run table from the README as the artifact:

## 5. Questions to rehearse
1. "Walk me through the worst incident." Start with the user-visible symptom, end with the guard that now prevents it.
2. "How do you know the agent is as reliable on run 50 as on run 1?" (pass^k, seeded chaos, idempotency; not accuracy on a clean set.)
3. "What would you not let the agent do, and why?" (Name the line and the incident behind it.)
4. "What breaks first at 10x?" (Cost, rate limits, human-queue depth, memory contradictions.)
5. "What did you measure that surprised you?"

## 6. Checklist before the call
- [ ] Three failures, each with symptom, mechanism, number, fix, guard
- [ ] Every number traceable to a query or log you can open
- [ ] A demo that cannot fail offline: `agentproof compare`, then `agentproof show docs/sample/failsafe-trace.jsonl`, then `agentproof replay` it
- [ ] An honest sentence about what the reference agents are (scripted) and what you have and have not measured on a real model
