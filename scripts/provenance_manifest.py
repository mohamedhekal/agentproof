#!/usr/bin/env python3
"""Reproducible provenance manifest for a git revision (default: the v0.1.0 release tag).

    python scripts/provenance_manifest.py --rev v0.1.0 --write     # (re)generate docs/provenance/
    python scripts/provenance_manifest.py --rev v0.1.0 --check     # verify the committed manifest still matches git

It records, for one revision: the commit chain (hash, author date, author, subject) and the SHA-256 of every
tracked file *as stored in that revision* (read with `git show`, so the result does not depend on your working
tree). The same command on the same revision always gives byte-identical output (no timestamps are generated).

What it is: a verifiable inventory of what was published at a given commit.
What it is NOT: a registration of ownership, a notarised timestamp or a signature. See docs/IP_PROVENANCE.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "provenance"


def git(*args: str, binary: bool = False):
    r = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True)
    return r.stdout if binary else r.stdout.decode("utf-8")


def build(rev: str) -> tuple[dict, str]:
    commit = git("rev-parse", f"{rev}^{{commit}}").strip()
    commits = []
    for line in git("log", "--reverse", "--format=%H%x1f%aI%x1f%an%x1f%s", commit).splitlines():
        h, date, author, subject = line.split("\x1f")
        commits.append({"commit": h, "author_date": date, "author": author, "subject": subject})
    files = {}
    for path in git("ls-tree", "-r", "--name-only", commit).splitlines():
        if path.startswith("docs/provenance/"):
            continue  # the manifest does not hash itself
        files[path] = hashlib.sha256(git("show", f"{commit}:{path}", binary=True)).hexdigest()
    manifest = {
        "about": "Inventory of files at one git revision. Not a registration of ownership, a notarised timestamp or a signature.",
        "repository": "https://github.com/mohamedhekal/agentproof",
        "revision": rev,
        "commit": commit,
        "tag_type": git("cat-file", "-t", rev).strip() if rev != commit else "commit",
        "commit_count": len(commits),
        "commits": commits,
        "file_count": len(files),
        "sha256": dict(sorted(files.items())),
    }
    sums = "".join(f"{digest}  {path}\n" for path, digest in sorted(files.items()))
    return manifest, sums


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rev", default="v0.1.0")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    a = ap.parse_args()
    manifest, sums = build(a.rev)
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    if a.write:
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "MANIFEST.json").write_text(text, encoding="utf-8")
        (OUT / "SHA256SUMS").write_text(sums, encoding="utf-8")
        print(f"wrote {OUT.relative_to(ROOT)}/MANIFEST.json and SHA256SUMS ({manifest['file_count']} files, {manifest['commit_count']} commits, {manifest['commit'][:12]})")
        return 0
    ok = (OUT / "MANIFEST.json").read_text(encoding="utf-8") == text and (OUT / "SHA256SUMS").read_text(encoding="utf-8") == sums
    print("provenance manifest matches git" if ok else "provenance manifest does NOT match git: regenerate with --write and review the diff")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
