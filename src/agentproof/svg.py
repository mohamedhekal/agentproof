"""Dependency-free SVG chart: reliability and safety as chaos increases."""
from __future__ import annotations

from html import escape

W, H, L, R, T, B = 760, 400, 64, 24, 64, 56
COLORS = {"naive": "#d9534f", "hardened": "#1f9d6b"}


def reliability_chart(sweep: dict[str, list[tuple[float, float, float]]], title: str) -> str:
    """sweep[agent] = [(chaos, pass_rate, unsafe_rate), ...]"""
    xs = [c for c, *_ in next(iter(sweep.values()))]
    x0, x1 = min(xs), max(xs)
    px = lambda x: L + (x - x0) / ((x1 - x0) or 1) * (W - L - R)  # noqa: E731
    py = lambda y: T + (1 - y) * (H - T - B)  # noqa: E731
    o = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="{escape(title)}">',
        f'<rect width="{W}" height="{H}" rx="14" fill="#ffffff" stroke="#e3e6ea"/>',
        f'<text x="{L}" y="30" font-family="Helvetica,Arial,sans-serif" font-size="17" font-weight="700" fill="#14181f">{escape(title)}</text>',
        f'<text x="{L}" y="48" font-family="Helvetica,Arial,sans-serif" font-size="12" fill="#5b6572">solid = tickets fully resolved   dashed = unsafe actions (double refunds, policy breaks)</text>',
    ]
    for g in (0, .25, .5, .75, 1):
        y = py(g)
        o.append(f'<line x1="{L}" y1="{y}" x2="{W - R}" y2="{y}" stroke="#eef0f3"/>')
        o.append(f'<text x="{L - 10}" y="{y + 4}" text-anchor="end" font-family="Helvetica,Arial,sans-serif" font-size="11" fill="#5b6572">{int(g * 100)}%</text>')
    for x in xs:
        o.append(f'<text x="{px(x)}" y="{H - B + 20}" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" font-size="11" fill="#5b6572">{x:.2f}</text>')
    o.append(f'<text x="{(L + W - R) / 2}" y="{H - 14}" text-anchor="middle" font-family="Helvetica,Arial,sans-serif" font-size="12" fill="#14181f">chaos level (probability that any tool call is sabotaged)</text>')
    for i, (agent, pts) in enumerate(sweep.items()):
        col = COLORS.get(agent, "#3b6fd9")
        solid = " ".join(f"{px(c):.1f},{py(p):.1f}" for c, p, _ in pts)
        dash = " ".join(f"{px(c):.1f},{py(u):.1f}" for c, _, u in pts)
        o.append(f'<polyline points="{solid}" fill="none" stroke="{col}" stroke-width="3" stroke-linejoin="round"/>')
        o.append(f'<polyline points="{dash}" fill="none" stroke="{col}" stroke-width="2" stroke-dasharray="6 5" opacity=".8"/>')
        for c, p, _ in pts:
            o.append(f'<circle cx="{px(c):.1f}" cy="{py(p):.1f}" r="4" fill="{col}"/>')
        lx = W - R - 150
        o.append(f'<rect x="{lx}" y="{T + 8 + i * 22}" width="12" height="12" rx="3" fill="{col}"/>')
        o.append(f'<text x="{lx + 20}" y="{T + 19 + i * 22}" font-family="Helvetica,Arial,sans-serif" font-size="12" fill="#14181f">{escape(agent)}</text>')
    o.append("</svg>")
    return "\n".join(o)
