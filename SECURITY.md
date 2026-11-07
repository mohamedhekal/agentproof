# Security policy

## Supported versions

| version | supported |
|---|---|
| 0.1.x | yes (best effort) |

AgentProof is a young, maintainer-run project. There is no security SLA; reports are handled on a best-effort basis.

## Reporting a vulnerability

Please **do not open a public issue** with exploit details.

1. Preferred: use GitHub's **private vulnerability reporting** ("Security" tab > "Report a vulnerability") on [this repository](https://github.com/mohamedhekal/agentproof/security). *Status at the time of writing: this feature is not yet enabled on the repository. Enabling it is a listed action in [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md).*
2. Or email the maintainer at **mohamed.k.hekal@gmail.com** (subject: "AgentProof security"). Please do not include exploit details in a public issue.
3. If neither works: open a public issue that says only "I have a security report" **with no technical details**, and the maintainer will arrange a private channel.

Please include the version or commit, what you did, what you expected, and what happened.

## Threat model and things to know

AgentProof runs agents and tools you provide, against a simulated world. Where it touches things outside that:

- **`--agents module:Class` imports and runs arbitrary Python.** That is how bring-your-own-agent works. Only evaluate agent code you trust, in an environment you trust.
- **Recordings can contain sensitive data.** Traces (`--traces`), cassettes (`AGENTPROOF_CASSETTE`) and reports store prompts, tickets, tool arguments and model responses. If you point the harness at real tickets or real systems, those recordings may contain personal data, payment details or secrets. Run `agentproof redact` before sharing or committing a recording. It is pattern-based and best effort (it will miss unusual formats).
- **API keys** are read from the environment (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`). Never pass a key on a command line you keep in shell history, never commit one, and revoke any key that has been pasted into a chat, ticket or log. Keys are not written to cassettes, traces or reports by AgentProof.
- **Replay and cassette files are data, not code**: they are parsed as JSON, never executed. A cassette from an untrusted source can still contain misleading content, so review it before trusting results.
- **Network:** the only outbound calls are to the model provider you select (or a base URL you set). The default CI workflow makes none.

## Safeguards in this repository

- `scripts/check_secrets.py` (run in CI and available as a pre-commit check) fails on API keys, tokens, private-key blocks, personal email addresses, phone/card numbers in recorded data, and files that should never be public (`.env`, key files, `private/`, `enterprise/`, raw `traces/`).
- `.gitignore` excludes environment files, keys, private directories and raw traces.
- The CI workflow has `permissions: contents: read`, uses no secrets, and pins third-party actions to commit SHAs. Dependabot proposes updates.
- GitHub secret scanning and push protection are enabled on the repository.

## Known gaps (stated honestly)

- Commits and the `v0.1.0` tag are not cryptographically signed; there is no branch protection yet; Dependabot *security updates* are not enabled; no SBOM is published. See [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md).
- The live demo (`docs/demo/`) runs entirely in the visitor's browser with a strict Content-Security-Policy and executes no user-supplied code, but it loads the pinned Pyodide 0.26.4 runtime from `cdn.jsdelivr.net` without a Subresource Integrity hash yet.
- Redaction is heuristic. Treat a redacted file as "reviewed by a tool", not "certified clean".
- No third-party security audit has been performed.
