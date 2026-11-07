# Open-core architecture

How AgentProof stays a genuinely useful open-source framework while leaving room for separate, private commercial products. **This is an architecture proposal and a set of rules; nothing described as "private" or "future" exists in this repository, and no commercial code is, or will be, published here.**

## 1. Principles

1. **One direction of dependency: private -> public, never the reverse.** Private products import the public core. The public core never imports, references, feature-flags or mentions private code.
2. **Published MIT code stays MIT.** Code already released is not moved into a private repository and re-labelled proprietary. New private code is *new* code.
3. **Extend, don't fork.** Commercial features attach through documented extension points, not by patching the core.
4. **The core is useful on its own.** Nothing that is in the public repository today is removed to push users toward a paid tier.
5. **A clean license boundary.** Every file belongs to exactly one side, and each side has its own license, repository, CI and secrets.

## 2. What belongs where

### Public core (this repository, MIT)

| area | modules | notes |
|---|---|---|
| Shop-Sim world | `world.py` | |
| Chaos engine and recorder | `toolbox.py` | fault model, traces, `ReplayToolBox` |
| Scenarios and safety grading | `scenarios.py`, `runner.py` | invariants, pass / safe fail / unsafe, pass^k |
| Replay and cassettes | `runner.replay`, `llm.RecordingClient`, `llm.ReplayClient` | |
| Basic LLM adapters | `llm.py` | Anthropic, OpenAI-compatible, ablations |
| CLI and CI integration | `cli.py`, `scripts/`, workflow | `agentproof gate` |
| Company Brain (existing, basic) | `brain/` | |
| Calibrated autonomy (existing) | `trust.py` | |
| Redaction and hygiene | `redact.py`, `scripts/check_secrets.py` | safety tooling stays public |
| Community docs, wiki, examples | `docs/`, `examples/` | |

### Future private components (separate repositories, not in this repository)

Enterprise SaaS backend; advanced evaluation engine; hosted testing infrastructure; enterprise dashboard; organizations and workspaces; SSO, RBAC and enterprise audit trails; commercial policy engine; billing and subscriptions; proprietary monitoring and analytics; private enterprise integrations.

**Test for "does this belong in the private repo?"**: it is *new* work, it is not in any public release, and it depends on the core rather than the other way round. If any of these is false, it stays public or needs a deliberate decision.

## 3. Extension points that exist today (the contract private code may rely on)

| extension point | where | tier |
|---|---|---|
| Bring-your-own agent: any object with `name` and `run(ticket, tools)`, loaded as `module:Class` | `runner.load_agent` | **stable** |
| Tool surface: `lookup_order`, `get_customer`, `get_tracking`, `issue_refund`, `reship`, `send_message`, `escalate` | `toolbox._ToolSurface` | **stable** (names and argument names) |
| Model provider protocol: `complete(system, messages, tools) -> {content, stop_reason}` | `llm.py` | **stable** |
| Scenarios: `Scenario(name, description, build, grade)` and the `SCENARIOS` list | `scenarios.py` | provisional |
| Run results: `Suite.metrics()` JSON, `RunResult` fields | `runner.py` | **stable** shape, new keys may be added |
| Trace format: JSONL, one header line then one event per tool call | `runner.save_trace` | provisional |
| Cassette format: JSONL `{key, response}` keyed by `request_key(system, messages, tools)` | `llm.py` | provisional |
| Brain extractor: `extract(text, clients) -> Parsed | None` | `brain/extract.py` | provisional |
| Autonomy: `CalibratedRouter.decide`, `.feedback` | `trust.py` | provisional |
| CLI contract: `agentproof gate` exit codes (0 pass, 1 regression), `baseline.json` | `cli.py` | **stable** |

**Tiers.** *stable*: breaking changes only in a major version, with a deprecation period in the preceding minor. *provisional*: may change in a minor version while the project is `0.x`, always noted in the changelog. Anything not listed (leading-underscore names, internal helpers, file layout) is **private API**, whatever its visibility in Python.

### Recommended before private code depends on it (not yet implemented)

These are proposals; none is built, and they should be separate, reviewed pull requests:

- an explicit `agentproof.api` module re-exporting exactly the stable names above;
- a `schema_version` field in `metrics()`, trace and cassette outputs;
- a Python entry-point group (for example `agentproof.agents`, `agentproof.scenarios`, `agentproof.providers`) so a private package can register components without being imported by the core;
- a short `CHANGELOG.md` and a `py.typed` marker once type hints are complete.

## 4. How a private service consumes the core

```
                 public (MIT)                              private (proprietary)
  +--------------------------------------+      +-----------------------------------------+
  |  agentproof (PyPI / git tag)         |<-----|  agentproof-cloud   (API, queue, workers)|
  |  - world, toolbox, scenarios, runner |      |  agentproof-enterprise (SSO, RBAC, audit)|
  |  - llm adapters, brain, trust        |<-----|  agentproof-dashboard  (web UI)          |
  |  - CLI + gate + redact               |      |  agentproof-policy     (policy engine)   |
  +--------------------------------------+      |  agentproof-billing    (subscriptions)   |
        ^  no imports in this direction          +-----------------------------------------+
```

- Private packages declare `agentproof>=X.Y,<X.(Y+1)` while the core is `0.x` (minor versions may break provisional APIs), then `>=1,<2` after 1.0.
- A private service runs evaluations by importing the public runner (or invoking the CLI) in a worker, stores `metrics()` / trace / cassette outputs in its own database, and adds identity, tenancy, billing and UI around them. **All of that is server-side code the customer never receives.**
- Private features register through the (proposed) entry points or by wrapping public classes (composition). They do not monkey-patch the core.
- Contract tests: each private repository runs the public core's own test suite against the exact core version it pins, plus its own integration tests, so a core release that breaks a stable interface is caught before shipping.

## 5. Proposed private repository structure

| repository (private) | owns | depends on |
|---|---|---|
| `agentproof-cloud` | API, job queue, evaluation workers, storage, tenancy model | `agentproof` |
| `agentproof-enterprise` | SSO / SAML / OIDC, RBAC, audit-trail export, retention | `agentproof-cloud` |
| `agentproof-dashboard` | web application (history, comparisons, gates, annotation) | `agentproof-cloud` API only |
| `agentproof-policy` | commercial policy engine (rules beyond the open autonomy router) | `agentproof` |
| `agentproof-billing` | plans, metering, invoicing integration | `agentproof-cloud` |
| `agentproof-integrations` | private customer-specific connectors | `agentproof` |
| `agentproof-infra` | infrastructure as code, deployment, secrets references (never values) | none |

Ownership: a GitHub **organization** (not a personal account) should own these, so that rights, access and history survive changes in personnel. Repository permissions: least privilege per team; `CODEOWNERS` on every repository; branch protection, required reviews and required status checks on `main`; no personal access tokens with org-wide scope; deploy through short-lived OIDC credentials, not stored keys.

## 6. Build, release and CI/CD separation

| | public repository | private repositories |
|---|---|---|
| CI | GitHub-hosted runners, `permissions: contents: read`, no secrets, no API keys (model runs replay from cassettes) | separate workflows, own secrets, environment protection rules, self-hosted runners if needed |
| Secrets | none | stored in the organization's secret manager; never in the public repository or its forks' workflows |
| Releases | semantic versions, tags, SHA-256 manifest, PyPI/Zenodo when approved | internal versioning; images or wheels in a **private** registry |
| Dependency on the other side | none | pins a released public version; never a floating branch in production |
| Visibility of build logs | public | private |

Do **not** share a workflow file, reusable workflow or secret between the two sides. A public pull request must never be able to trigger a job that holds private secrets (beware `pull_request_target` and `workflow_run`).

## 7. Commercial licensing requirements

- The private repositories need their **own license** (proprietary / commercial terms) chosen with legal advice. Keep license headers out of public files and keep the MIT notice on anything derived from the core.
- If a private product **bundles** public MIT code (for example by vendoring it), the MIT copyright notice and license text must ship with it. MIT permits this; removing the notice does not.
- Contributions to the public core are MIT. If broader rights over contributions are wanted later, see the DCO / CLA discussion in [CONTRIBUTING.md](../CONTRIBUTING.md); it must be announced and cannot apply retroactively.
- The name and logo are governed separately ([TRADEMARKS.md](../TRADEMARKS.md)); decide who owns the mark before a product ships under it.
- Customer terms (ToS, DPA, privacy policy, SLA) are separate legal documents.

## 8. A SaaS does not require shipping proprietary source

A hosted service runs private code on infrastructure you control and exposes an API and a UI; customers receive responses, not source. The public core's MIT license has no copyleft, so a service that uses it need not publish its own code. **Situations where proprietary code could be disclosed, and what to do:**

| situation | risk | mitigation |
|---|---|---|
| On-premises or "private cloud" delivery (container images, installers, wheels) | the customer now holds the artifact; Python is trivially readable or decompilable | ship compiled/obfuscated artifacts only if you accept that is *deterrence*, keep the valuable logic server-side, rely on contract terms, offer SaaS-only for crown-jewel components |
| Publishing a private package by mistake (wrong index, public registry, public repo) | immediate disclosure; secret scanners and mirrors copy within minutes | private registries only; CI blocks publishing from private repositories to public indexes; require 2-person approval for releases; `check_secrets.py` forbids `private/`, `enterprise/` and similar paths in the public repo |
| Source distributions and source maps (`sdist`, JS source maps, debug symbols, `.pyc` with source paths) | includes more than the wheel/bundle | review package contents (`unzip -l`, `tar tf`) before every release; build with explicit include lists |
| Public docs, wiki, issues, deck or error messages naming private modules, schemas or roadmaps | discloses design | keep private design in private docs; review public text; the public deck is already a record of what was disclosed |
| Test fixtures, traces and cassettes recorded from customers | customer data and prompts exposed | record only synthetic data publicly; run `agentproof redact`; keep real recordings in private storage |
| A private service that is AGPL/GPL-linked | copyleft obligations | the public core is MIT (no copyleft); avoid adding copyleft dependencies to the commercial side without advice |
| Logs and telemetry from hosted runs sent to third parties | data and code leakage | log redaction, a data-processing review, region controls |
| Client-side/JS dashboard bundles | business logic visible in the browser | keep policy and metering logic on the server |

## 9. Compatibility contract (summary)

- Public core follows [Semantic Versioning](https://semver.org). While `0.x`, minor releases may change *provisional* interfaces and every change is listed in the release notes; *stable* interfaces change only in majors, after a deprecation notice in the previous minor.
- Output formats gain fields but do not repurpose existing ones. Consumers must ignore unknown fields.
- Private repositories pin an exact or narrow range of the core and upgrade deliberately; the core's maintainers announce interface changes in release notes before they ship.

## 10. Decisions that need the maintainer (and, where noted, a lawyer)

1. Confirm the public/private boundary in section 2 (it follows your instruction; the Brain and autonomy modules are listed as public because they already are).
2. Decide whether to create the GitHub organization now (recommended before any private code exists).
3. Decide on DCO vs CLA (a lawyer for anything beyond DCO).
4. Commission trademark clearance and a licensing review before the first commercial release.
5. Approve (or reword) the intent statements in [COMMERCIAL.md](../COMMERCIAL.md), which commit the maintainer publicly.
