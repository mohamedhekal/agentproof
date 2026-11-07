"""Redaction and repository-hygiene guards. Secret-looking fixtures are built at runtime so this file
never contains a literal token (which would trip GitHub push protection and our own scanner)."""
import json
import subprocess
import sys
from pathlib import Path

from agentproof import cli
from agentproof.redact import find, redact_file, redact_json, redact_text

KEY = "sk-" + "ant-" + "Ab12Cd34" * 4
OPENAI_KEY = "sk-" + "proj_" + "Zy98Xw76" * 3
AWS = "AKIA" + "ABCDEFGHIJKLMNOP"
CARD = "4111 1111 1111 1111"  # a well-known test number (passes the Luhn check)
EMAIL = "customer" + "@" + "example.org"
ROOT = Path(__file__).resolve().parent.parent


def test_secrets_are_redacted_everywhere_in_text():
    text = f"key={KEY} other={OPENAI_KEY} aws={AWS} Authorization: Bearer abcdef1234567890abcdef"
    out = redact_text(text)
    assert KEY not in out and OPENAI_KEY not in out and AWS not in out and "abcdef1234567890" not in out
    assert out.count("[REDACTED:") >= 4


def test_pii_is_redacted_but_synthetic_ids_and_dates_survive():
    out = redact_text(f"mail {EMAIL} phone +20 100 123 4567 card {CARD} order ORD-48213 on 2026-01-26 ticket T-10553")
    assert EMAIL not in out and "123 4567" not in out and "4111" not in out
    assert "ORD-48213" in out and "2026-01-26" in out and "T-10553" in out


def test_no_reply_attribution_addresses_are_kept():
    assert "noreply@anthropic.com" in redact_text("Co-Authored-By: Claude <noreply@anthropic.com>")


def test_non_card_digit_runs_are_not_treated_as_cards():
    hits = [k for k, _ in find("1234 5678 9012 3456")]  # fails Luhn
    assert "card" not in hits


def test_redact_json_covers_nested_values_not_keys():
    obj = {"a": [{"text": f"x {KEY}"}], "n": 5, "k": EMAIL}
    out = redact_json(obj)
    assert KEY not in json.dumps(out) and EMAIL not in json.dumps(out) and out["n"] == 5 and "a" in out


def test_redact_file_roundtrip_jsonl(tmp_path):
    src = tmp_path / "trace.jsonl"
    src.write_text(json.dumps({"i": 1, "result": {"text": f"token {KEY}"}}) + "\n" + json.dumps({"i": 2, "note": EMAIL}) + "\n")
    dst = tmp_path / "out" / "trace.jsonl"
    counts = redact_file(src, dst)
    assert counts["api_key"] == 1 and counts["email"] == 1
    assert KEY not in dst.read_text() and EMAIL not in dst.read_text()
    assert len(dst.read_text().splitlines()) == 2


def test_cli_check_mode_exit_codes(tmp_path):
    dirty, clean = tmp_path / "d.jsonl", tmp_path / "c.jsonl"
    dirty.write_text(json.dumps({"t": KEY}) + "\n")
    clean.write_text(json.dumps({"t": "all good"}) + "\n")
    assert cli.main(["redact", "--check", str(dirty)]) == 1
    assert cli.main(["redact", "--check", str(clean)]) == 0
    assert KEY in dirty.read_text()  # --check writes nothing


def test_committed_recordings_contain_no_secrets_or_personal_data():
    """Every cassette, report and sample trace in the repository must already be clean."""
    files = [str(p) for d in ("cassettes", "reports", "docs/sample") for p in (ROOT / d).rglob("*") if p.is_file()]
    assert files
    assert cli.main(["redact", "--check", *files]) == 0


def test_repo_hygiene_script_passes_on_the_working_tree():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_secrets.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_hygiene_script_catches_a_planted_secret(tmp_path):
    bad = tmp_path / "leak.txt"
    bad.write_text(f"token = {KEY}\n")
    # run on an absolute path inside tmp: the script resolves relative to the repo, so use a repo-relative path
    planted = ROOT / "zz_planted_secret.txt"
    planted.write_text(f"token = {KEY}\n")
    try:
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_secrets.py"), "zz_planted_secret.txt"], capture_output=True, text=True)
    finally:
        planted.unlink()
    assert r.returncode == 1 and "api_key" in r.stdout and KEY not in r.stdout


def test_maintainer_contact_email_is_allowed_only_in_governance_files():
    contact = "mohamed.k.hekal" + "@" + "gmail.com"
    ok = ROOT / "SECURITY.md"
    assert contact in ok.read_text(), "the contact address should be published in SECURITY.md"
    planted = ROOT / "zz_planted_contact.txt"
    planted.write_text(f"mail me at {contact}\n")
    try:
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "check_secrets.py"), "zz_planted_contact.txt"], capture_output=True, text=True)
    finally:
        planted.unlink()
    assert r.returncode == 1 and "email" in r.stdout


def test_no_phone_number_is_published_in_the_repository():
    import re
    from agentproof.redact import find

    for p in subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=ROOT, capture_output=True, text=True).stdout.split():
        f = ROOT / p
        if f.suffix in {".png", ".pdf"} or not f.is_file() or p.startswith(("cassettes/", "reports/", "docs/provenance/")):
            continue
        if p in {"scripts/check_secrets.py", "src/agentproof/redact.py", "tests/test_hygiene.py"}:
            continue
        for line in f.read_text(encoding="utf-8", errors="ignore").splitlines():
            assert not [h for k, h in find(line) if k == "phone" and re.search(r"\+?20\s?1\d", h)], f"phone number in {p}"
