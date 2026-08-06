import os
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
        print("  ERROR: no contribution calendar in response")
        return None


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
            lvl = LEVEL_NAMES.get(day.get("level"), 0)
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
