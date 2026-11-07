# Contributing to AgentProof

Thanks for helping. Small, focused pull requests with tests are the easiest to merge. Please also read the [Code of Conduct](CODE_OF_CONDUCT.md).

## Set up

```bash
git clone https://github.com/mohamedhekal/agentproof && cd agentproof
pip install -e .[dev]          # Python 3.10+; no runtime dependencies
pytest -q                      # about 60 tests, under 15 seconds
agentproof gate                # the reliability gate (must still pass)
python scripts/check_secrets.py   # no secrets / personal data / private files
```

If a global pytest plugin on your machine breaks collection, run `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q`.

## The live demo

`docs/demo/` runs the real package in the browser (Pyodide). If you change anything under `src/agentproof/`, run `python scripts/build_demo.py` and commit the regenerated `docs/demo/bundle.json`; a test fails if it is stale. The page must keep saying it is only a demo that explains the idea.

## What a good pull request does

- Keeps the tests and the reliability gate green. **Do not change recorded results, cassettes or `baseline.json` to make a test pass.** If behaviour legitimately changes, say why in the pull request and regenerate with the documented command so a reviewer can see the diff.
- Adds or updates tests for new behaviour. New scenarios need a grader that checks the final world state, not the agent's words.
- Keeps claims honest: if you add a number to the docs, add the command that reproduces it and its limits.
- Contains **no secrets, no real customer data, no real payment data, no private infrastructure details**. Use synthetic data. Run `agentproof redact --check` on any recording you add.
- Documentation is bilingual where practical (English plus an Arabic counterpart under `docs/ar/`). A pull request that is English-only is still welcome; mention it and the maintainer will arrange the Arabic text.

## Licensing and attribution

- By submitting a contribution you agree it is licensed under the repository's **MIT License** (inbound = outbound, which is also GitHub's default for public repositories). **You keep the copyright in your contribution.** No copyright assignment is required.
- You are credited in the git history and, with your permission, in [AUTHORS.md](AUTHORS.md).
- Do not submit code you did not write unless its license is MIT-compatible, and say where it came from so attribution and the license notice can be preserved.
- **AI-assisted contributions are welcome. Please say so in the pull request** (which tool, and that you reviewed the result). You remain responsible for what you submit.

## About a DCO or CLA (information only; neither is required today)

Some projects add a **Developer Certificate of Origin** (contributors add `Signed-off-by:` to each commit, certifying they have the right to submit it) or a **Contributor License Agreement**. The trade-offs, so the choice is made deliberately:

| | what it does | implications |
|---|---|---|
| DCO | a lightweight per-commit certification of origin | low friction, no copyright transfer; improves provenance; does **not** let the maintainer relicense contributions beyond the license they were given |
| CLA (license grant) | a signed grant of broader rights to the maintainer | lets a maintainer later relicense or dual-license, which matters for open-core; adds friction and can discourage contributors; needs legal drafting |
| CLA (copyright assignment) | transfers ownership | the heaviest option; contributors lose rights; most communities resist it |

**Today the project requires none of these.** If the maintainer later wants commercial flexibility over community contributions, a DCO is the gentler step and a CLA needs legal advice and a public announcement *before* it applies; it would not apply retroactively to contributions already accepted under MIT. Nothing here imposes any of this.

## Reporting problems

- Bugs and ideas: open an issue.
- Security: see [SECURITY.md](SECURITY.md) (do not open a public issue with exploit details).
