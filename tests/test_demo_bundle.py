"""The browser demo must never drift from the package it explains, and must always say it is only a demo."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "docs" / "demo"


def test_demo_bundle_is_in_sync_with_the_source():
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_demo.py"), "--check"], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + "\nFix: python scripts/build_demo.py"


def test_demo_bundle_contains_the_real_package_and_the_claude_cassette():
    files = json.loads((DEMO / "bundle.json").read_text(encoding="utf-8"))["files"]
    for must in ("py/agentproof/runner.py", "py/agentproof/toolbox.py", "py/agentproof/brain/store.py", "py/demo_api.py", "cassettes/claude.jsonl"):
        assert must in files, must


def test_demo_page_states_that_it_is_only_a_demo_in_both_languages():
    html, js = (DEMO / "index.html").read_text(encoding="utf-8"), (DEMO / "app.js").read_text(encoding="utf-8")
    assert 'role="note"' in html and 'data-i18n="bannerTitle"' in html
    assert "A demo to explain the idea." in js and "ديمو لتوضيح الفكرة." in js
    assert "not a benchmark of any AI model" in js


def test_demo_page_is_locked_down_and_loads_nothing_unexpected():
    html = (DEMO / "index.html").read_text(encoding="utf-8")
    assert "Content-Security-Policy" in html and "default-src 'none'" in html
    assert "<script>" not in html  # no inline scripts: the CSP forbids them
    assert 'style="' not in html
    hosts = {h.split("/")[0].rstrip(";") for h in __import__("re").findall(r"https://([^\"' )]+)", html)}
    assert hosts <= {"cdn.jsdelivr.net", "github.com", "raw.githubusercontent.com"}, hosts
    assert "v0.26.4" in html  # the runtime version is pinned


def test_pages_plumbing_exists():
    assert (ROOT / "docs" / ".nojekyll").exists() and (ROOT / "docs" / "index.html").exists()
