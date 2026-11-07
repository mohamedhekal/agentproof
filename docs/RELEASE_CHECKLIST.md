# Release and research-preservation checklist

What the repository already supports, and the **human actions** still required. Nothing in the second part has been done: no DOI, archive entry, signature, package or registration exists yet, and none should be claimed until it does.

## What is ready in the repository

- Semantic version in `pyproject.toml` (`0.1.0`) and a `v0.1.0` tag and GitHub release.
- `CITATION.cff` (verified facts only; no DOI/ORCID) so GitHub shows "Cite this repository".
- `docs/provenance/MANIFEST.json` and `SHA256SUMS`: a reproducible inventory of every file at `v0.1.0` (`python scripts/provenance_manifest.py --rev v0.1.0 --check`).
- CI with least-privilege permissions, SHA-pinned actions, a secrets/PII/private-path check, tests, the reliability gate and an offline replay of the recorded Claude run.
- Dependabot configuration and `CODEOWNERS`.
- `SECURITY.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `COPYRIGHT.md`, `AUTHORS.md`, `TRADEMARKS.md`, `COMMERCIAL.md`, `docs/IP_PROVENANCE.md`, `docs/OPEN_CORE_ARCHITECTURE.md`.

## Semantic versioning rules for this project

- `MAJOR.MINOR.PATCH`. While `0.x`: minor = may change provisional interfaces (listed in `OPEN_CORE_ARCHITECTURE.md`), patch = fixes only.
- Never change recorded cassettes, reports or `baseline.json` to make a release pass. If a behaviour change legitimately moves a number, regenerate with the documented command and explain the diff in the release notes.

## Per-release steps (maintainer)

1. Update `version` in `pyproject.toml` and `CITATION.cff` (`version`, `date-released`, `commit`).
2. Run: `pytest -q`, `agentproof gate`, `agentproof compare --agents replay:cassettes/claude.jsonl --runs 5 --chaos 0.3`, `python scripts/check_secrets.py`. All must pass.
3. Regenerate and commit the provenance manifest for the release commit: `python scripts/provenance_manifest.py --rev <tag> --write` (create the tag first, then commit the manifest in the next commit and say so in the notes).
4. Create an **annotated, signed** tag: `git tag -s vX.Y.Z -m "AgentProof vX.Y.Z"` and push it.
5. Create the GitHub release from that tag. Attach `SHA256SUMS`, the built `sdist`/wheel (if you publish them) and the deck PDF.
6. Check that the release page renders and that attached checksums match `sha256sum -c SHA256SUMS`.

## Human actions still required (none done yet)

### Repository settings (GitHub UI)
- [ ] Enable **private vulnerability reporting** (Settings > Code security) so `SECURITY.md` works as written.
- [ ] Enable **branch protection** on `main` (require pull requests and the `ci` checks; no force pushes; restrict deletions).
- [ ] Enable **Dependabot security updates** (the config only covers version updates).
- [ ] Consider requiring signed commits on `main` once you have a signing key.
- [ ] The contact address in `SECURITY.md`, `CODE_OF_CONDUCT.md`, `COMMERCIAL.md`, `CITATION.cff` and `AUTHORS.md` is a personal Gmail address (mohamed.k.hekal@gmail.com). Consider a project alias (for example on a domain you own) before the project grows, and update those five files together. No phone number is published anywhere in this repository, on purpose.
- [ ] Add a `LICENSE` file to the **wiki** repository (the intent is MIT; the wiki currently has none).

### Live demo (GitHub Pages)
- [ ] Settings > Pages > Source: **Deploy from a branch**, branch `main`, folder `/docs`. The demo is then served at `https://mohamedhekal.github.io/agentproof/` (`docs/.nojekyll` stops Jekyll from processing the documentation).
- [ ] Open the page and click through the five sections once; confirm the banner "A demo to explain the idea" is visible.
- [ ] After any change under `src/agentproof/`, regenerate the demo bundle (`python scripts/build_demo.py`) and commit `docs/demo/bundle.json`; a test fails if it is stale.
- [ ] Optional hardening: the page loads the pinned Pyodide 0.26.4 runtime from cdn.jsdelivr.net without a Subresource Integrity hash. Add an `integrity` attribute (and `crossorigin`) once you have verified the hash of that file, or self-host the runtime.

### Identity and signing
- [ ] Configure commit/tag signing (GPG or SSH signing key uploaded to GitHub as a *signing key*); then `git tag -s`.
- [ ] Optionally use a GitHub `noreply` address for future commits.

### Zenodo (DOI)
- [ ] Sign in at zenodo.org with GitHub and switch the `mohamedhekal/agentproof` toggle on (Zenodo > GitHub).
- [ ] Zenodo archives **new releases** published after the toggle is on; the existing `v0.1.0` is not archived retroactively. Publish the next release (for example `v0.1.1`) to obtain the first record.
- [ ] Review the Zenodo metadata (title, authors as you want them cited, license MIT, description).
- [ ] After you receive a DOI, add it to `CITATION.cff` (`identifiers`) and the README. **Do not add a DOI that does not exist.**
- [ ] Optional: create an ORCID iD and add it to `CITATION.cff` (`orcid` on the author). Do not add one you do not have.

### Software Heritage
- [ ] Open archive.softwareheritage.org, use "Save code now" for `https://github.com/mohamedhekal/agentproof` (or enable the GitHub webhook), and wait for the visit to complete.
- [ ] Record the resulting SWHID in the release notes or `CITATION.cff` only after it exists.

### Package index (only if you decide to publish)
- [ ] Check name availability for `agentproof` on PyPI and for conflicts before claiming it.
- [ ] Use PyPI **Trusted Publishing** (OIDC) from a protected workflow; never a long-lived token in repository secrets.
- [ ] Inspect the built `sdist` and wheel contents before upload (the default `sdist` includes tests, cassettes and the deck images; exclude what you do not want shipped).

### Legal review (not something a repository can settle)
- [ ] Trademark clearance and advice (`TRADEMARKS.md`).
- [ ] Ownership questions: AI-assisted authorship, any prior employment/university/contract claims, deck and mark provenance (`COPYRIGHT.md`).
- [ ] Patent advice if exclusivity over any technique matters, given the public disclosure on 2026-11-07.
- [ ] DCO / CLA decision and the wording of the intent statements in `COMMERCIAL.md`.
- [ ] Customer-facing legal documents (terms, privacy policy, DPA) before any hosted product.

## Verification after each step

`git status` clean; CI green on the release commit; `scripts/provenance_manifest.py --check` passes for the release tag; the release page lists the expected assets; every external record (DOI, SWHID) is cited only after you can open it.
