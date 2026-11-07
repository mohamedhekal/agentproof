"""agentproof CLI."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .runner import load_trace, replay, run_suite, save_trace
from .svg import reliability_chart
from .trust import simulate

SPARK = "▁▂▃▄▅▆▇█"


def pct(x: float) -> str:
    return f"{x * 100:5.1f}%"


def spark(vals: list[float], top: float = 1.0) -> str:
    return "".join(SPARK[min(7, int(v / top * 7.999))] for v in vals)


def table(rows: list[list[str]], head: list[str]) -> str:
    cols = list(zip(head, *rows))
    widths = [max(len(str(c)) for c in col) for col in cols]
    fmt = lambda r: "  ".join(str(c).ljust(w) for c, w in zip(r, widths))  # noqa: E731
    return "\n".join([fmt(head), "  ".join("-" * w for w in widths), *map(fmt, rows)])


def summary_row(m: dict) -> list[str]:
    return [m["agent"], pct(m["pass_rate"]), pct(m["safe_fail_rate"]), pct(m["unsafe_rate"]), pct(m["reliability"]), str(m["avg_tool_calls"])]


SUMMARY_HEAD = ["agent", "resolved", "handed-to-human", "UNSAFE", "reliability(pass^k)", "avg calls"]


def md_report(ms: list[dict]) -> str:
    c, k = ms[0]["chaos"], ms[0]["runs_per_scenario"]
    out = [f"# AgentProof report\n\nchaos={c} - {k} seeded runs per scenario - {ms[0]['total_runs']} runs per agent\n"]
    out += ["| agent | resolved | handed to human | **unsafe** | reliability (pass^k) | avg tool calls |", "|---|---|---|---|---|---|"]
    for m in ms:
        out.append(f"| {m['agent']} | {pct(m['pass_rate'])} | {pct(m['safe_fail_rate'])} | **{pct(m['unsafe_rate'])}** | {pct(m['reliability'])} | {m['avg_tool_calls']} |")
    for m in ms:
        out += [f"\n## {m['agent']}: per scenario\n", "| scenario | pass | safe_fail | unsafe |", "|---|---|---|---|"]
        for s, v in m["per_scenario"].items():
            out.append(f"| {s} | {v['pass']}/{v['runs']} | {v['safe_fail']} | {v['unsafe']} |")
        if m["failure_reasons"]:
            out += ["", "Top failure reasons: " + ", ".join(f"`{k}` x{v}" for k, v in list(m["failure_reasons"].items())[:6])]
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------ commands
def cmd_compare(a: argparse.Namespace) -> int:
    from .scenarios import by_name

    only = [by_name(n) for n in a.scenarios] if a.scenarios else None
    ms = []
    for spec in a.agents:
        suite = run_suite(spec, a.runs, a.chaos, a.seed, only)
        ms.append(suite.metrics())
        if a.traces:
            for r in suite.results:
                if r.status != "pass":
                    save_trace(r, spec, a.chaos, Path(a.traces) / spec.replace(":", "_") / f"{r.scenario}-{r.seed}.jsonl")
    print(f"\nchaos={a.chaos}  runs/scenario={a.runs}  seed={a.seed}\n")
    print(table([summary_row(m) for m in ms], SUMMARY_HEAD))
    for m in ms:
        if m["failure_reasons"]:
            print(f"\n{m['agent']} top failure reasons:")
            for k, v in list(m["failure_reasons"].items())[:6]:
                print(f"  {v:4d}  {k}")
    if a.out:
        out = Path(a.out)
        out.mkdir(parents=True, exist_ok=True)
        (out / "latest.json").write_text(json.dumps(ms, indent=2, ensure_ascii=False))
        (out / "latest.md").write_text(md_report(ms))
        print(f"\nwrote {out}/latest.md and latest.json")
    return 0


def cmd_gate(a: argparse.Namespace) -> int:
    m = run_suite(a.agent, a.runs, a.chaos, a.seed).metrics()
    path = Path(a.baseline)
    if a.update:
        path.write_text(json.dumps({k: m[k] for k in ("chaos", "runs_per_scenario", "pass_rate", "unsafe_rate", "reliability", "per_scenario")}, indent=2))
        print(f"baseline written to {path}: pass={pct(m['pass_rate'])} unsafe={pct(m['unsafe_rate'])}")
        return 0
    base = json.loads(path.read_text())
    problems = []
    if m["unsafe_rate"] > base["unsafe_rate"]:
        problems.append(f"unsafe rate rose {pct(base['unsafe_rate'])} -> {pct(m['unsafe_rate'])}")
    if m["pass_rate"] < base["pass_rate"] - a.tolerance:
        problems.append(f"resolution rate fell {pct(base['pass_rate'])} -> {pct(m['pass_rate'])} (tolerance {a.tolerance})")
    for s, v in m["per_scenario"].items():
        b = base["per_scenario"].get(s)
        if b and v["pass"] / v["runs"] < b["pass"] / b["runs"] - max(a.tolerance, 0.10):
            problems.append(f"scenario '{s}' regressed: {b['pass']}/{b['runs']} -> {v['pass']}/{v['runs']}")
    if problems:
        print("GATE FAILED: " + a.agent)
        for p in problems:
            print("  -", p)
        return 1
    print(f"GATE PASSED: {a.agent}  pass={pct(m['pass_rate'])} unsafe={pct(m['unsafe_rate'])}  (baseline pass={pct(base['pass_rate'])})")
    return 0


def cmd_sweep(a: argparse.Namespace) -> int:
    levels = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]
    data = {}
    for spec in a.agents:
        pts = []
        for c in levels:
            m = run_suite(spec, a.runs, c, a.seed).metrics()
            pts.append((c, m["pass_rate"], m["unsafe_rate"]))
        data[spec.split(":")[-1].lower()] = pts
    print(table([[k] + [f"{p[1] * 100:.0f}%/{p[2] * 100:.0f}%" for p in v] for k, v in data.items()], ["agent (resolved/unsafe)"] + [f"c={c}" for c in levels]))
    if a.svg:
        Path(a.svg).parent.mkdir(parents=True, exist_ok=True)
        Path(a.svg).write_text(reliability_chart(data, "Reliability under chaos: same tasks, same faults"))
        print(f"\nwrote {a.svg}")
    return 0


def cmd_replay(a: argparse.Namespace) -> int:
    r = replay(Path(a.trace), a.agent)
    h = r["header"]
    print(f"{h['scenario']} seed={h['seed']} recorded status={h['status']} agent={h['agent']}")
    print(f"replay: {r['outcome'].upper()}  ({r['calls_matched']}/{r['calls_recorded']} calls matched)  {r['detail']}")
    return 0 if r["outcome"] == "identical" else 2


def cmd_show(a: argparse.Namespace) -> int:
    h, events = load_trace(Path(a.trace))
    print(f"{h['scenario']} seed={h['seed']} agent={h['agent']} chaos={h['chaos']} -> {h['status'].upper()}")
    print(f"ticket: {h['ticket']['text']}")
    for ev in events:
        fault = f"  <-- FAULT: {ev['fault']}" if ev["fault"] else ""
        args = ", ".join(f"{k}={v!r}" for k, v in ev["args"].items() if v is not None)
        res = f"ERROR {ev['error']['type']}: {ev['error']['message']}" if "error" in ev else repr(ev["result"])[:70]
        print(f"  {ev['i']:2d}. {ev['tool']}({args[:60]}) -> {res}{fault}")
    for k in ("unsafe", "unmet"):
        if h[k]:
            print(f"{k}: {h[k]}")
    return 0


def cmd_autonomy(a: argparse.Namespace) -> int:
    res = simulate(a.n, a.seed)
    print(f"{res['n']} proposed actions, 5 action classes, fraud wave hits 'refund_damaged_small' at the halfway mark\n")
    rows = []
    for p, v in res["policies"].items():
        rows.append([p, pct(v["ask_rate"]), pct(v["bad_auto_rate"]), spark(v["ask_by_window"]), spark(v["bad_by_window"], top=0.25)])
    print(table(rows, ["policy", "human asked", "bad actions sent w/o a human", "asks over time", "bad over time"]))
    return 0


def cmd_brain(a: argparse.Namespace) -> int:
    import statistics as st

    from .brain.evaluate import evaluate
    from .brain.store import Brain
    from .brain.synth import generate

    if a.explain:
        ds = generate(a.seed)
        client, attr = a.explain
        b = Brain(ds.clients)
        for o in ds.observations:
            b.ingest(o)
        print(f"audit trail: {client} / {attr}  (every claim we ever heard, newest last)\n")
        for c in b.history(client, attr):
            state = f"RETRACTED {c.retracted_at}" if c.retracted_at else "believed"
            print(f"  {c.obs_id} [{c.source:8s}] heard {c.recorded_at}  true from {c.valid_from}  {c.kind:10s} value={c.value!r:16} {state}")
            print(f"           \"{c.quote}\"")
        ans = b.get(client, attr, ds.end, ds.end)
        if ans:
            print(f"\ncurrent answer: {ans.value!r}  (from {ans.obs_id}, {ans.source}){'  CONFLICTED' if ans.conflicted else ''}")
        return 0
    rows = []
    for u in a.unseen:
        rs = [evaluate(s, unseen=u) for s in range(a.seed, a.seed + a.seeds)]
        for name in rs[0]["systems"]:
            m = lambda k: st.mean(r["systems"][name][k] for r in rs)  # noqa: E731
            rows.append([f"{u:.0%}", name, pct(m("all")), pct(m("tricky")), pct(m("valid_at")), pct(m("belief_at")), pct(m("provenance"))])
    print(f"{rs[0]['observations']} messages, {rs[0]['questions']} questions per seed, mean of {a.seeds} seeds\n")
    print(table(rows, ["unseen phrasing", "system", "all", "tricky", "valid-at", "belief-at", "provenance"]))
    cr = [r["systems"]["brain"]["conflict_recall"] for r in rs if r["systems"]["brain"]["conflict_recall"] is not None]
    print(f"\nbrain conflict recall (last setting): {pct(st.mean(cr)) if cr else 'n/a'}; RAG never flags conflicts (0%)")
    return 0


def cmd_redact(a: argparse.Namespace) -> int:
    from collections import Counter

    from .redact import redact_file

    total: Counter = Counter()
    for p in a.paths:
        src = Path(p)
        if a.check:
            counts = redact_file(src, None)
        elif a.in_place:
            counts = redact_file(src, src)
        else:
            counts = redact_file(src, Path(a.out_dir) / src.name)
        total += counts
        print(f"{p}: " + (", ".join(f"{k} x{v}" for k, v in sorted(counts.items())) or "nothing found"))
    if a.check:
        return 1 if total else 0
    where = "in place" if a.in_place else f"to {a.out_dir}/"
    print(f"\nredacted {sum(total.values())} item(s) {where}. Pattern-based: review the output before sharing.")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="agentproof", description="Prove your agent survives production, not just the demo.")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    def common(sp: argparse.ArgumentParser, chaos: float = 0.3, runs: int = 20) -> None:
        sp.add_argument("--runs", type=int, default=runs, help="seeded runs per scenario")
        sp.add_argument("--chaos", type=float, default=chaos, help="probability a tool call is sabotaged")
        sp.add_argument("--seed", type=int, default=0)

    sp = sub.add_parser("compare", help="run agents head to head under chaos")
    sp.add_argument("--agents", nargs="+", default=["naive", "hardened"], help="naive | hardened | module:Class")
    sp.add_argument("--out", help="write latest.md / latest.json here")
    sp.add_argument("--traces", help="save a replayable trace of every non-passing run here")
    sp.add_argument("--scenarios", nargs="+", help="only these scenarios (default: all 8)")
    common(sp)
    sp.set_defaults(fn=cmd_compare)

    sp = sub.add_parser("gate", help="CI gate: fail if reliability or safety regressed vs a baseline")
    sp.add_argument("--agent", default="hardened")
    sp.add_argument("--baseline", default="baseline.json")
    sp.add_argument("--update", action="store_true", help="write the baseline instead of checking it")
    sp.add_argument("--tolerance", type=float, default=0.02)
    common(sp)
    sp.set_defaults(fn=cmd_gate)

    sp = sub.add_parser("sweep", help="reliability vs chaos curve (+ optional SVG)")
    sp.add_argument("--agents", nargs="+", default=["naive", "hardened"])
    sp.add_argument("--svg")
    common(sp, runs=20)
    sp.set_defaults(fn=cmd_sweep)

    sp = sub.add_parser("replay", help="re-run an agent against a recorded trace (no world, no randomness)")
    sp.add_argument("trace")
    sp.add_argument("--agent", help="override the recorded agent (e.g. test a fix against a recorded failure)")
    sp.set_defaults(fn=cmd_replay)

    sp = sub.add_parser("show", help="print a recorded trace as a timeline")
    sp.add_argument("trace")
    sp.set_defaults(fn=cmd_show)

    sp = sub.add_parser("autonomy", help="simulate calibrated human-in-the-loop routing")
    sp.add_argument("--n", type=int, default=4000)
    sp.add_argument("--seed", type=int, default=7)
    sp.set_defaults(fn=cmd_autonomy)

    sp = sub.add_parser("brain", help="Company Brain (bitemporal memory) vs RAG on synthetic operational history")
    sp.add_argument("--seeds", type=int, default=10)
    sp.add_argument("--seed", type=int, default=7)
    sp.add_argument("--unseen", type=float, nargs="+", default=[0.0, 0.15, 0.3], help="share of messages using phrasing the extractor never saw")
    sp.add_argument("--explain", nargs=2, metavar=("CLIENT", "ATTR"), help="print the audit trail for one client attribute")
    sp.set_defaults(fn=cmd_brain)

    sp = sub.add_parser("redact", help="remove secrets and personal data (keys, emails, phones, cards) from traces and cassettes")
    sp.add_argument("paths", nargs="+")
    sp.add_argument("--out-dir", default="redacted", help="write redacted copies here (default: redacted/)")
    sp.add_argument("--in-place", action="store_true", help="overwrite the files")
    sp.add_argument("--check", action="store_true", help="write nothing; exit 1 if anything would be redacted")
    sp.set_defaults(fn=cmd_redact)

    args = p.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
