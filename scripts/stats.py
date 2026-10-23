#!/usr/bin/env python3
"""Build dist/stats.svg (streaks, languages, ASCII contribution heatmap, sparkline).

Live mode needs GH_LOGIN and GH_TOKEN env vars. `--demo` uses fake data for previews.
"""
import argparse
import json
import os
import random
import urllib.request
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

BG, FG, MUTED, DIMMER = "#0b0e14", "#e6edf3", "#8b949e", "#484f58"
BAR = "#c9d1d9"
W = 760
QUERY = """
query($login:String!){ user(login:$login){
  contributionsCollection{ contributionCalendar{ totalContributions
    weeks{ contributionDays{ date contributionCount } } } }
  repositories(first:100, ownerAffiliations:OWNER, isFork:false, privacy:PUBLIC){ nodes{
    name primaryLanguage{ name }
    languages(first:10, orderBy:{field:SIZE, direction:DESC}){ edges{ size node{ name } } } } }
} }"""


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(data["errors"])
    return data["data"]["user"]


def demo_data():
    random.seed(7)
    today = date.today()
    start = today - timedelta(days=364)
    days, d = [], start
    while d <= today:
        busy = 0.5 if d.month in (1, 2, 8, 9, 10) else 0.2
        n = random.choice([0, 0, 1, 2, 3, 5, 8, 12]) if random.random() < busy else 0
        days.append({"date": d.isoformat(), "contributionCount": n})
        d += timedelta(days=1)
    repos = [{"primaryLanguage": {"name": n}, "languages": {"edges": [{"size": s, "node": {"name": n}}]}}
             for n, s in [("Python", 90000)] * 6 + [("TypeScript", 60000)] * 3 + [("JavaScript", 9000), ("HTML", 5000), ("C", 3000)]]
    return {"contributionsCollection": {"contributionCalendar": {"totalContributions": sum(x["contributionCount"] for x in days),
            "weeks": [{"contributionDays": days[i:i + 7]} for i in range(0, len(days), 7)]}},
            "repositories": {"nodes": repos}}


def streaks(days):
    cur = 0
    seq = [(date.fromisoformat(d["date"]), d["contributionCount"]) for d in days]
    i = len(seq) - 1
    if seq[i][1] == 0:
        i -= 1                      # today not over yet
    while i >= 0 and seq[i][1] > 0:
        cur += 1
        i -= 1
    best, run, best_range, run_start = 0, 0, ("", ""), None
    for dt, n in seq:
        if n > 0:
            run += 1
            run_start = run_start or dt
            if run > best:
                best, best_range = run, (run_start, dt)
        else:
            run, run_start = 0, None
    return cur, best, best_range


def bars(x, y, title, rows, fmt):
    out = [f'<text x="{x}" y="{y}" class="lbl">{title}</text>']
    top = max(v for _, v in rows) or 1
    for i, (name, v) in enumerate(rows):
        yy = y + 26 + i * 27
        out.append(f'<text x="{x}" y="{yy}" class="nm">{name.lower()}</text>')
        out.append(f'<rect x="{x + 102}" y="{yy - 10}" width="{max(6, 150 * v / top):.0f}" height="10" rx="3" fill="{BAR}"/>')
        out.append(f'<text x="{x + 300}" y="{yy}" text-anchor="end" class="mt">{fmt(v)}</text>')
    return out


def build(user):
    cal = user["contributionsCollection"]["contributionCalendar"]
    days = [d for w in cal["weeks"] for d in w["contributionDays"]]
    total = cal["totalContributions"]
    active = sum(1 for d in days if d["contributionCount"] > 0)
    weekly = [sum(d["contributionCount"] for d in w["contributionDays"]) for w in cal["weeks"]]
    cur, best, (b0, b1) = streaks(days)
    fmt_d = lambda d: d.strftime("%b %d").lower() if d else ""

    byte_c, repo_c = Counter(), Counter()
    for r in user["repositories"]["nodes"]:
        if r.get("primaryLanguage"):
            repo_c[r["primaryLanguage"]["name"]] += 1
        for e in r["languages"]["edges"]:
            byte_c[e["node"]["name"]] += e["size"]
    tb = sum(byte_c.values()) or 1
    by_bytes = [(n, v) for n, v in byte_c.most_common(5)]
    by_repos = [(n, v) for n, v in repo_c.most_common(5)]

    H = 760
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="GitHub stats">',
         "<style>text{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,'DejaVu Sans Mono',monospace}"
         f".big{{font-size:44px;fill:{FG}}}.lbl{{font-size:11px;letter-spacing:2px;fill:{MUTED}}}"
         f".nm{{font-size:14px;fill:{FG};font-weight:700}}.mt{{font-size:13px;fill:{MUTED}}}"
         f".sub{{font-size:13px;fill:{MUTED}}}.hm{{font-size:11px;fill:{FG}}}"
         ".fade{opacity:0;animation:f .8s ease forwards}@keyframes f{to{opacity:1}}</style>",
         f'<rect width="100%" height="100%" fill="{BG}"/>', '<g class="fade">']
    # streaks
    o += [f'<text x="60" y="80" class="big">{cur}</text><text x="60" y="108" class="sub">current streak</text>',
          f'<line x1="330" y1="40" x2="330" y2="120" stroke="{DIMMER}"/>',
          f'<text x="380" y="80" class="big">{best}</text><text x="380" y="108" class="sub">longest streak</text>',
          f'<text x="380" y="128" class="mt">{fmt_d(b0)} – {fmt_d(b1)}</text>']
    o += bars(60, 175, "BY BYTES", [(n, 100 * v / tb) for n, v in by_bytes], lambda v: f"{v:.0f}%")
    o += bars(430, 175, "BY REPOS", by_repos, lambda v: f"{int(v)}")
    # heatmap
    o.append(f'<text x="60" y="352" class="lbl">THE YEAR</text>')
    o.append(f'<text x="60" y="374" class="sub">{active} of {len(days)} days had a contribution</text>')
    o.append(f'<text x="640" y="374" text-anchor="end" class="mt">less  :  +  #  @  more</text>')
    counts = sorted(c for c in (d["contributionCount"] for d in days) if c)
    q = lambda p: counts[min(len(counts) - 1, int(len(counts) * p))] if counts else 1
    t1, t2, t3 = q(0.25), q(0.5), q(0.8)
    glyph = lambda n: "" if n == 0 else ":" if n <= t1 else "+" if n <= t2 else "#" if n <= t3 else "@"
    cw, ch, x0, y0 = 11.4, 12, 90, 395
    month_seen, last_lab = None, -9
    for wi, w in enumerate(cal["weeks"]):
        for di, d in enumerate(w["contributionDays"]):
            g = glyph(d["contributionCount"])
            if g:
                o.append(f'<text class="hm" x="{x0 + wi * cw:.1f}" y="{y0 + di * ch}">{g}</text>')
        m = date.fromisoformat(w["contributionDays"][0]["date"]).strftime("%b").lower()
        if m != month_seen and wi - last_lab >= 3:
            month_seen, last_lab = m, wi
            o.append(f'<text class="mt" x="{x0 + wi * cw:.1f}" y="{y0 + 7 * ch + 14}" style="font-size:11px">{m}</text>')
    for di, lab in ((1, "mon"), (3, "wed"), (5, "fri")):
        o.append(f'<text class="mt" x="52" y="{y0 + di * ch}" style="font-size:11px">{lab}</text>')
    # totals + sparkline
    o.append(f'<text x="60" y="590" style="font-size:64px;fill:{FG}" font-family="monospace">{total}</text>')
    o.append(f'<text x="60" y="620" class="sub">contributions in the last year</text>')
    o.append(f'<text x="700" y="560" text-anchor="end" style="font-size:26px;fill:{FG};font-weight:700">{active}</text>'
             f'<text x="700" y="580" text-anchor="end" class="mt">active days</text>'
             f'<text x="700" y="612" text-anchor="end" style="font-size:26px;fill:{FG};font-weight:700">{max(weekly)}</text>'
             f'<text x="700" y="632" text-anchor="end" class="mt">best week</text>')
    sx0, sx1, sy0, sy1 = 60, 700, 705, 650
    mx = max(weekly) or 1
    pts = [(sx0 + i * (sx1 - sx0) / (len(weekly) - 1), sy0 - (sy0 - sy1) * v / mx) for i, v in enumerate(weekly)]
    line = " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    o.append(f'<path d="M{sx0},{sy0} L{line} L{sx1},{sy0} Z" fill="#2d333b"/>')
    o.append(f'<path d="M{line}" fill="none" stroke="{BAR}" stroke-width="2" stroke-linejoin="round"/>')
    o.append(f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="4" fill="#fff"/>')
    o += ["</g></svg>"]
    return "\n".join(o)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--out", default="dist/stats.svg")
    a = ap.parse_args()
    user = demo_data() if a.demo else fetch(os.environ["GH_LOGIN"], os.environ["GH_TOKEN"])
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(build(user), encoding="utf-8")
    print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
