import os
import re
import json
import datetime
import urllib.request

USERNAME = "HernanFx"
TOKEN = os.environ.get("LANG_TOKEN") or os.environ.get("GITHUB_TOKEN", "")

if os.environ.get("LANG_TOKEN"):
    print("Using LANG_TOKEN (private included)")
elif os.environ.get("GITHUB_TOKEN"):
    print("Using GITHUB_TOKEN (public only)")
else:
    print("Using no token (unauthenticated)")

# Palette: profile purple levels (GitHub dark style)
LEVEL_COLORS = {
    0: "#161B22",
    1: "#3C33BB",
    2: "#4035CE",
    3: "#5349DF",
    4: "#736BE4",
}
LEVEL_NAMES = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

MONTHS_ES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
# Row index in the Sunday-first grid -> day label (optional, left side)
DAY_LABELS = {1: "Lun", 3: "Mié", 5: "Vie"}

FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

# Layout constants
SVG_W = 740
SVG_H = 146
CARD_RX = 14
GRID_X = 46
GRID_Y = 39
CELL = 10
GAP = 3
PITCH = CELL + GAP  # 13
TITLE_Y = 20
MONTH_Y = 33
LEGEND_Y = 140


def escape_xml(text):
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def gql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Content-Type": "application/json",
            "User-Agent": "github-readme-contributions",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  ERROR GraphQL -> {e}")
        return {}


def get_calendar():
    today = datetime.date.today()
    from_date = today - datetime.timedelta(days=365)
    query = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            level
          }
        }
      }
    }
  }
}
"""
    data = gql(query, {
        "login": USERNAME,
        "from": from_date.isoformat() + "T00:00:00Z",
        "to": today.isoformat() + "T23:59:59Z",
    })
    try:
        cal = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        return cal
    except Exception:
        print("  FULL RESPONSE:", json.dumps(data)[:600])
        print("  ERRORS:", json.dumps(data.get("errors", "none"))[:600])
        print("  HAS DATA:", "data" in data,
              "| HAS USER:", "user" in data.get("data", {}),
              "| HAS CONTRIBUTIONS:", "contributionsCollection" in data.get("data", {}).get("user", {}))
        print("  ERROR: no contribution calendar in response")
        return None


def fetch_public_days():
    """Fallback: parse the public HTML contributions page (same data source as snk).
    Returns a list of {date, contributionCount, level} in DOM order, or None."""
    url = f"https://github.com/users/{USERNAME}/contributions"
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            html = r.read().decode("utf-8")
    except Exception as e:
        print(f"  ERROR HTML fetch -> {e}")
        return None

    # Calendar cells: <td> tags carrying BOTH data-date and data-level.
    # Scoping to <td> excludes the legend divs (contribution-graph-legend-level-*),
    # which also carry data-level but are NOT calendar cells.
    tds = re.findall(r"<td[^>]*>", html)
    cells = [t for t in tds if "data-date" in t and "data-level" in t]
    dates = [re.search(r'data-date="([^"]+)"', t).group(1) for t in cells]
    levels = [int(re.search(r'data-level="([0-9])"', t).group(1)) for t in cells]

    # Real daily counts: the page emits one <tool-tip> per cell in the same
    # DOM order, e.g. "5 contributions on September 12th." or
    # "No contributions on August 3rd." (cells have no aria-label).
    tips = re.findall(r"<tool-tip[^>]*>([^<]*)</tool-tip>", html)
    print(f"  HTML cells: dates={len(dates)} levels={len(levels)} tooltips={len(tips)}")
    if not dates or not (len(dates) == len(levels) == len(tips)):
        print("  ERROR: cell/level/tooltip count mismatch — HTML structure changed")
        return None

    days = []
    for date, lvl, tip in zip(dates, levels, tips):
        m = re.search(r"(\d+)\s+contributions?", tip)
        count = int(m.group(1)) if m else 0
        days.append({"date": date, "contributionCount": count, "level": lvl})
    return days


def group_weeks(days):
    """Group days into Sunday-Saturday week columns, ordered chronologically.
    Works regardless of DOM order (GitHub's HTML calendar is row-major:
    all Sundays first, then Mondays, etc.)."""
    by_week = {}
    for day in days:
        d = datetime.date.fromisoformat(day["date"])
        sunday = d - datetime.timedelta(days=(d.weekday() + 1) % 7)
        by_week.setdefault(sunday, []).append(day)
    weeks = []
    for sunday in sorted(by_week):
        col = sorted(by_week[sunday], key=lambda x: x["date"])
        weeks.append({"contributionDays": col})
    return weeks


def build_svg(cal):
    total = cal.get("totalContributions", 0)
    weeks = cal.get("weeks", [])
    total_str = f"{total:,}"

    cells = ""
    months = ""
    last_month = None
    last_label_x = None

    for wi, week in enumerate(weeks):
        x = GRID_X + wi * PITCH
        days = week.get("contributionDays", [])
        rows_done = set()

        # Month label: month of the first day of this week (Spanish)
        if days:
            d = datetime.date.fromisoformat(days[0]["date"])
            m = MONTHS_ES[d.month - 1]
            if m != last_month and (last_label_x is None or x >= last_label_x + 32):
                months += (
                    f'<text x="{x}" y="{MONTH_Y}" font-family="{FONT}" '
                    f'font-size="11" fill="#8B949E">{m}</text>'
                )
                last_month = m
                last_label_x = x

        # Contribution cells
        for day in days:
            d = datetime.date.fromisoformat(day["date"])
            row = (d.weekday() + 1) % 7  # Sunday-first grid: Lun=1 ... Dom=0
            rows_done.add(row)
            count = day.get("contributionCount", 0)
            lvl = day.get("level")
            if isinstance(lvl, str):
                lvl = LEVEL_NAMES.get(lvl, 0)
            if not isinstance(lvl, int) or lvl < 0 or lvl > 4:
                lvl = 0
            if count == 0:
                lvl = 0
            color = LEVEL_COLORS[lvl]
            cells += (
                f'<rect x="{x}" y="{GRID_Y + row * PITCH}" width="{CELL}" '
                f'height="{CELL}" rx="2" ry="2" fill="{color}"/>'
            )

        # Boundary weeks may have < 7 days: fill missing rows with level0
        if len(rows_done) < 7:
            for row in range(7):
                if row not in rows_done:
                    cells += (
                        f'<rect x="{x}" y="{GRID_Y + row * PITCH}" width="{CELL}" '
                        f'height="{CELL}" rx="2" ry="2" fill="{LEVEL_COLORS[0]}"/>'
                    )

    # Day labels on the left (Lun / Mié / Vie)
    day_labels = ""
    for row, label in DAY_LABELS.items():
        day_labels += (
            f'<text x="38" y="{GRID_Y + row * PITCH + 8}" text-anchor="end" '
            f'font-family="{FONT}" font-size="10" fill="#8B949E">{label}</text>'
        )

    # Legend (right aligned): Menos | cells | Más
    legend_x = 592
    cells_x = legend_x + 36
    legend_cells = ""
    for lvl in range(5):
        cx = cells_x + lvl * PITCH
        legend_cells += (
            f'<rect x="{cx}" y="{LEGEND_Y - 8}" width="{CELL}" height="{CELL}" '
            f'rx="2" ry="2" fill="{LEVEL_COLORS[lvl]}"/>'
        )
    mas_x = cells_x + 5 * PITCH + 6

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_W}" height="{SVG_H}" viewBox="0 0 {SVG_W} {SVG_H}">
  <rect x="0" y="0" width="{SVG_W}" height="{SVG_H}" rx="{CARD_RX}" ry="{CARD_RX}" fill="#0D1117" stroke="#30363D" stroke-width="1" />
  <text x="24" y="{TITLE_Y}" font-family="{FONT}" font-size="14" font-weight="600" fill="#C9D1D9">{escape_xml(total_str)} contribuciones en el último año</text>
  {months}
  {day_labels}
  {cells}
  <text x="{legend_x}" y="{LEGEND_Y}" font-family="{FONT}" font-size="11" fill="#8B949E">Menos</text>
  {legend_cells}
  <text x="{mas_x}" y="{LEGEND_Y}" font-family="{FONT}" font-size="11" fill="#8B949E">Más</text>
</svg>"""
    return svg


def build_fallback_svg():
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_W}" height="{SVG_H}" viewBox="0 0 {SVG_W} {SVG_H}">
  <rect x="0" y="0" width="{SVG_W}" height="{SVG_H}" rx="{CARD_RX}" ry="{CARD_RX}" fill="#0D1117" stroke="#30363D" stroke-width="1" />
  <text x="370" y="75" text-anchor="middle" font-family="{FONT}" font-size="14" fill="#C9D1D9">No se pudieron cargar las contribuciones de {escape_xml(USERNAME)}</text>
</svg>"""


def main():
    os.makedirs("dist", exist_ok=True)

    print("Fetching contribution calendar (GraphQL)...")
    cal = get_calendar()

    if not cal:
        print("GraphQL unavailable, using public HTML endpoint (no private contributions)")
        days = fetch_public_days()
        if days:
            cal = {
                "totalContributions": sum(d["contributionCount"] for d in days),
                "weeks": group_weeks(days),
            }

    if not cal:
        print("No contribution data available, writing fallback SVG")
        svg = build_fallback_svg()
    else:
        total = cal.get("totalContributions", 0)
        weeks = len(cal.get("weeks", []))
        print(f"totalContributions: {total}")
        print(f"weeks: {weeks}")
        svg = build_svg(cal)

    with open("dist/github-contributions.svg", "w", encoding="utf-8") as f:
        f.write(svg)

    print("Generated dist/github-contributions.svg")


if __name__ == "__main__":
    main()
