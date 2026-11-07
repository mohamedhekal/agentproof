#!/usr/bin/env python3
"""Repository hygiene check: secrets, personal data and private files must not be committed.

    python scripts/check_secrets.py            # scan every tracked file (what CI runs)
    python scripts/check_secrets.py PATH ...   # scan specific files (e.g. from a pre-commit hook)

Checks (a best-effort safety net, not a guarantee):
  1. file names that should never be public: .env files, private keys, credential files, and anything under
     private/, enterprise/, commercial/, secrets/ or a raw traces/ folder;
  2. API keys, tokens and private-key blocks inside any text file;
  3. email addresses (apart from known no-reply addresses) in any text file;
  4. phone numbers and payment-card numbers inside recorded data (cassettes, traces, reports, samples).

A line containing `agentproof:allow` is skipped (use it only for deliberate fixtures).
Exit status 1 if anything is found. It never prints a matched secret in full.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from agentproof.redact import find  # noqa: E402

FORBIDDEN_PATHS = [
    (re.compile(r"(^|/)\.env(\..+)?$"), "environment file"),
    (re.compile(r"\.(pem|key|p12|pfx|keystore|jks)$", re.I), "key / certificate file"),
    (re.compile(r"(^|/)id_(rsa|dsa|ecdsa|ed25519)(\.pub)?$"), "SSH key"),
    (re.compile(r"(^|/)credentials(\.json)?$", re.I), "credentials file"),
    (re.compile(r"^(private|enterprise|commercial|secrets)/", re.I), "private-source directory"),
    (re.compile(r"^traces[^/]*/"), "raw evaluation traces (redact first, then share a copy under docs/sample/)"),
    (re.compile(r"\.(har|sqlite|sqlite3|db)$", re.I), "capture / database file"),
]
DATA_DIRS = ("cassettes/", "reports/", "docs/sample/", "traces")
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".pdf", ".ico", ".zip", ".gz", ".whl"}
SKIP_FILES = {"scripts/check_secrets.py", "src/agentproof/redact.py", "tests/test_hygiene.py"}
# The maintainer's published contact address is allowed in these governance files only (nowhere else).
CONTACT_EMAIL = "mohamed.k.hekal@gmail.com"
CONTACT_FILES = {"SECURITY.md", "CODE_OF_CONDUCT.md", "COMMERCIAL.md", "CITATION.cff", "AUTHORS.md", "docs/RELEASE_CHECKLIST.md"}


def tracked_files() -> list[str]:
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    return [p for p in out.splitlines() if p]


def mask(s: str) -> str:
    return s[:4] + "..." + s[-2:] if len(s) > 8 else "***"


def main(argv: list[str]) -> int:
    files = argv or tracked_files()
    problems: list[str] = []
    for rel in files:
        rel = str(Path(rel))
        for pat, why in FORBIDDEN_PATHS:
            if pat.search(rel):
                problems.append(f"{rel}: forbidden path ({why})")
        path = ROOT / rel
        if rel in SKIP_FILES or path.suffix.lower() in BINARY_SUFFIXES or not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        in_data = rel.startswith(DATA_DIRS)
        for n, line in enumerate(text.splitlines(), 1):
            if "agentproof:allow" in line:
                continue
            for kind, hit in find(line, pii=True):
                if kind in ("card", "phone") and not in_data:
                    continue
                if kind == "email" and hit == CONTACT_EMAIL and rel in CONTACT_FILES:
                    continue
                problems.append(f"{rel}:{n}: {kind} ({mask(hit)})")
    if problems:
        print("hygiene check FAILED:")
        for p in problems:
            print("  -", p)
        return 1
    print(f"hygiene check passed ({len(files)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
