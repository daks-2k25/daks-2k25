#!/usr/bin/env python3
"""Gera assets/ship-shooter.svg a partir do calendário REAL de contribuições do GitHub.

Uso (Actions):  GITHUB_TOKEN=... GITHUB_USER=daks-2k25 python scripts/generate_ship.py
Teste offline:  python scripts/generate_ship.py --sample
Só usa a biblioteca padrão do Python.
"""
import datetime as dt
import json
import os
import random
import sys
import urllib.request

USER = os.environ.get("GITHUB_USER", "daks-2k25")
OUT = os.environ.get("OUT", "assets/ship-shooter.svg")

CELL, GAP = 14, 4
PITCH = CELL + GAP
LEFT, TOP = 34, 22          # espaço para os rótulos (Mon/Wed/Fri e meses)
SHIP_AREA = 56
BG = "#0d1117"
LEVEL_COLORS = ["#1c0f12", "#5c161b", "#8b1a1f", "#c4252b", "#ff3b30"]
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2,
          "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
MAX_SHOTS = 36
SHOT_TIME = 0.7             # segundos por tiro


def fetch_weeks():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        sys.exit("Defina GITHUB_TOKEN (ou use --sample para testar).")
    query = """query($login:String!){user(login:$login){contributionsCollection{
      contributionCalendar{weeks{contributionDays{date contributionCount contributionLevel weekday}}}}}}"""
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": USER}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "ship-shooter"})
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.load(r)
    if "errors" in data:
        sys.exit(json.dumps(data["errors"]))
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [[(d["date"], d["contributionCount"], LEVELS[d["contributionLevel"]], d["weekday"])
             for d in w["contributionDays"]] for w in weeks]


def sample_weeks():
    random.seed(7)
    end = dt.date.today()
    start = end - dt.timedelta(days=364)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)  # domingo
    weeks, d = [], start
    while d <= end:
        wk = []
        for i in range(7):
            day = d + dt.timedelta(days=i)
            if day > end:
                break
            lvl = random.choice([0, 0, 0, 1, 1, 2, 3, 4]) if day.month in (7, 8, 9, 10) else random.choice([0, 0, 0, 0, 0, 1, 2])
            wk.append((day.isoformat(), lvl * 2, lvl, i))
        weeks.append(wk)
        d += dt.timedelta(days=7)
    return weeks


def build(weeks):
    n = len(weeks)
    width = LEFT + n * PITCH + 10
    grid_h = 7 * PITCH
    ship_y = TOP + grid_h + 40            # ponta da nave
    height = ship_y + 20
    cells, active = [], {}                # active: col -> linha mais baixa com commit
    for c, wk in enumerate(weeks):
        for date, count, lvl, wd in wk:
            x, y = LEFT + c * PITCH, TOP + wd * PITCH
            cells.append((c, wd, x, y, lvl, date, count))
            if lvl > 0:
                active[c] = max(active.get(c, -1), wd)

    cols = sorted(active)
    if len(cols) > MAX_SHOTS:               # distribui os tiros ao longo do ano
        step = len(cols) / MAX_SHOTS
        cols = [cols[int(i * step)] for i in range(MAX_SHOTS)]
    shots = len(cols)
    T = max(shots, 1) * SHOT_TIME + 1.0

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" '
           f'role="img" aria-label="Contribuições do GitHub de {USER}">',
           f'<rect width="{width}" height="{height}" rx="10" fill="{BG}"/>',
           '<style>text{font:10px "JetBrains Mono",ui-monospace,monospace;fill:#8b949e}</style>']

    # rótulos de mês
    last_m = None
    for c, wk in enumerate(weeks):
        d = dt.date.fromisoformat(wk[0][0])
        if d.month != last_m and (c == 0 or d.day <= 7):
            if c == 0 and d.day > 20:       # primeira semana já quase no mês seguinte
                last_m = d.month
                continue
            out.append(f'<text x="{LEFT + c * PITCH}" y="{TOP - 8}">{d.strftime("%b")}</text>')
            last_m = d.month
    for wd, label in ((1, "Mon"), (3, "Wed"), (5, "Fri")):
        out.append(f'<text x="2" y="{TOP + wd * PITCH + CELL - 3}">{label}</text>')

    # células (com tooltip nativo, igual ao GitHub)
    hit = {}
    for i, c in enumerate(cols):
        hit[(c, active[c])] = i
    for c, wd, x, y, lvl, date, count in cells:
        title = f'{count} contribuição(ões) em {date}'
        color = LEVEL_COLORS[lvl]
        body = f'<title>{title}</title>'
        if (c, wd) in hit:
            i = hit[(c, wd)]
            t = (0.5 + i * SHOT_TIME + 0.35) / T
            kt = [0, max(t - 0.001, 0), t, min(t + 0.15, 0.999), 1]
            body += (f'<animate attributeName="fill" dur="{T:.2f}s" repeatCount="indefinite" '
                     f'keyTimes="{";".join(f"{k:.4f}" for k in kt)}" '
                     f'values="{color};{color};#ffffff;{color};{color}"/>')
        out.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="3" fill="{color}">{body}</rect>')

    # raios (um por tiro) + nave
    def cx(c): return LEFT + c * PITCH + CELL / 2
    for i, c in enumerate(cols):
        t0 = (0.5 + i * SHOT_TIME + 0.25) / T
        t1 = (0.5 + i * SHOT_TIME + 0.5) / T
        y_top = TOP + active[c] * PITCH + CELL
        kt = [0, t0, min(t0 + 0.0001, 1), t1, min(t1 + 0.0001, 1), 1]
        out.append(f'<rect x="{cx(c) - 1:.1f}" y="{y_top}" width="2" height="{ship_y - 14 - y_top}" '
                   f'fill="#ff6b60" opacity="0"><animate attributeName="opacity" dur="{T:.2f}s" '
                   f'repeatCount="indefinite" keyTimes="{";".join(f"{k:.4f}" for k in kt)}" '
                   f'values="0;0;1;1;0;0"/></rect>')

    xs, kts = [], []
    xs.append(cx(cols[0]) if cols else LEFT); kts.append(0)
    for i, c in enumerate(cols):
        ta = (0.5 + i * SHOT_TIME) / T
        tb = (0.5 + i * SHOT_TIME + 0.55) / T
        for t in (ta, tb):
            xs.append(cx(c)); kts.append(min(t, 0.9999))
    xs.append(cx(cols[0]) if cols else LEFT); kts.append(1)
    vals = ";".join(f"{x:.1f} 0" for x in xs)
    out.append(f'<g transform="translate({xs[0]:.1f} 0)"><g transform="translate(0 {ship_y})">'
               '<polygon points="0,-14 8,10 0,5 -8,10" fill="#ff3b30"/><circle cy="1" r="3" fill="#fff"/></g>'
               f'<animateTransform attributeName="transform" type="translate" dur="{T:.2f}s" '
               f'repeatCount="indefinite" keyTimes="{";".join(f"{k:.4f}" for k in kts)}" values="{vals}"/></g>')
    out.append('</svg>')
    return "\n".join(out)


if __name__ == "__main__":
    weeks = sample_weeks() if "--sample" in sys.argv else fetch_weeks()
    os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(build(weeks))
    print("ok ->", OUT)
