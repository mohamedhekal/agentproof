# IP provenance

A factual record of where AgentProof came from and what was published when, built only from real git data. It is meant to make the project's history **verifiable**, not to assert legal rights. See the end for what it does not prove.

## Timeline (all times from git and the GitHub API)

| event | when | evidence |
|---|---|---|
| first commit `f90b73c` | 2026-11-07 02:16:51 +02:00 (00:16:51 UTC) | `git log` |
| public repository created | 2026-11-07 00:18:22 UTC | GitHub API `created_at` |
| 8th commit `57a3fc9` (release commit) | 2026-11-07 03:43:02 +02:00 (01:43:02 UTC) | `git log` |
| release `v0.1.0` published | 2026-11-07 01:48:25 UTC | GitHub release `published_at`; tag `v0.1.0` points to `57a3fc9` (a lightweight, unsigned tag). The API's release `created_at` (01:43:02 UTC) is the tag commit's date, not the publication time. |

The commit chain at `v0.1.0`:

| # | commit | what it added |
|---|---|---|
| 1 | `f90b73c` | chaos harness, Shop-Sim, graders, replay, calibrated autonomy, CI gate |
| 2 | `84db941` | Company Brain, LLM adapter with cassettes, deep-dive worksheet |
| 3 | `5282323` | case study, `--scenarios` filter |
| 4 | `987af6b` | measured Claude run (40 runs) and its cassette |
| 5 | `705198e` | prompt ablation on Claude, cassettes, tests |
| 6 | `7d31942` | hardened OpenAI path, HTTP round-trip tests |
| 7 | `c22bf3b` | pitch deck in the READMEs, Arabic documentation |
| 8 | `57a3fc9` | pitch deck as a PDF |

The exact hashes, author dates and a SHA-256 for every file at that revision are in [provenance/MANIFEST.json](provenance/MANIFEST.json) and [provenance/SHA256SUMS](provenance/SHA256SUMS).

## Authorship and attribution

See [AUTHORS.md](../AUTHORS.md) and [COPYRIGHT.md](../COPYRIGHT.md). In short: a single human author (Mohamed Hekal), with AI assistance (Claude) recorded in every commit trailer; no third-party source code copied; all data synthetic. Open questions (legal name, deck/mark provenance, prior obligations, AI-assisted authorship) are listed in `COPYRIGHT.md` and not resolved here.

## What has been publicly disclosed

Everything in the repository at `v0.1.0`, under the MIT License, from 2026-11-07: the world and fault model, the chaos engine, state-based grading and its invariants, pass / safe-fail / unsafe and pass^k, replay and content-hashed cassettes, the Anthropic and OpenAI adapters, the prompt-ablation method and results, the bitemporal Company Brain and its benchmark, the calibrated autonomy router, the CI gate, the bilingual documentation, the 17-slide deck (including the proposed commercial model and go-to-market plan) and the wiki.

Consequences worth knowing (not legal advice):

- MIT permissions already granted cannot be withdrawn for copies already distributed.
- Public disclosure can affect whether a technical idea can still be patented in many jurisdictions (some have a short grace period, many do not). If patents matter to you, ask a patent attorney before relying on any exclusivity.
- Anything that should stay proprietary must **not** be added to this repository. See [OPEN_CORE_ARCHITECTURE.md](OPEN_CORE_ARCHITECTURE.md).

## Verifying the manifest yourself

```bash
git fetch --tags
python scripts/provenance_manifest.py --rev v0.1.0 --check
```

`--check` recomputes the inventory from git (independent of your working tree) and compares it to the committed files. A mismatch means the manifest or the history differs from what was recorded. The same command always yields byte-identical output, because no timestamps are generated.

## What this record does NOT do

- It is **not a registration** of copyright, trademark or any other right, and not a certificate of ownership.
- Git author dates are written by the committer's own machine and can be set to anything; they are evidence, not proof. The GitHub `created_at` and the release time are recorded by GitHub, which is stronger but still not a notarised timestamp.
- Commits and the tag are **unsigned**, so they do not cryptographically bind the author's identity. Signing is a listed action in [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md).
- No DOI, Zenodo record, Software Heritage archive entry, ORCID or publication exists yet for this project. This document does not claim otherwise. A DOI, if obtained, identifies an archived copy; it does not establish ownership.
- Third-party archives and services (GitHub, Zenodo, Software Heritage) can improve the evidence trail; none of them decides who owns the work.

## Related

[COPYRIGHT.md](../COPYRIGHT.md) | [AUTHORS.md](../AUTHORS.md) | [CITATION.cff](../CITATION.cff) | [TRADEMARKS.md](../TRADEMARKS.md) | [RELEASE_CHECKLIST.md](RELEASE_CHECKLIST.md)
