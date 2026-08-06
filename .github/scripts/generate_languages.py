import os
import json
import urllib.request
import collections

USERNAME = "HernanFx"
TOKEN = os.environ.get("LANG_TOKEN") or os.environ.get("GITHUB_TOKEN", "")

if os.environ.get("LANG_TOKEN"):
    print("Using LANG_TOKEN (private repos included)")
elif os.environ.get("GITHUB_TOKEN"):
    print("Using GITHUB_TOKEN (public only)")
else:
    print("Using no token (unauthenticated, public only)")

LANG_COLORS = {
    "Python": "#3c33bb",
    "C++": "#4035ce",
    "HTML": "#5349df",
    "CSS": "#5349df",
    "JavaScript": "#736be4",
    "Kotlin": "#3c33bb",
    "Java": "#5349df",
    "TypeScript": "#736be4",
    "C": "#4035ce",
    "C#": "#4035ce",
    "Go": "#3c33bb",
    "Rust": "#736be4",
    "Ruby": "#5349df",
    "PHP": "#4035ce",
    "Swift": "#3c33bb",
    "Dart": "#5349df",
    "Shell": "#736be4",
    "Dockerfile": "#4035ce",
    "Makefile": "#3c33bb",
    "CMake": "#5349df",
}

def req(url):
    req = urllib.request.Request(url)
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("User-Agent", "github-readme-languages")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            print(f"  OK {url[:60]}... -> {len(data) if isinstance(data, list) else 'ok'}")
            return data
    except Exception as e:
        print(f"  ERROR {url[:60]}... -> {e}")
        return {}

def get_repos():
    repos = []
    page = 1
    # With LANG_TOKEN we can also see private repos (type=owner includes them).
    # Without it, keep type=public: unauthenticated requests only see public.
    repo_type = "owner" if os.environ.get("LANG_TOKEN") else "public"
    while True:
        data = req(f"https://api.github.com/users/{USERNAME}/repos?per_page=100&page={page}&type={repo_type}")
        if not data:
            break
        repos.extend(data)
        page += 1
    return repos

def get_languages(repo_full_name):
    data = req(f"https://api.github.com/repos/{repo_full_name}/languages")
    return data

def generate_svg(languages):
    total = sum(languages.values())
    if total == 0:
        return generate_empty_svg()

    # Filter noise: keep only languages with >= 1% of total bytes
    items = sorted(languages.items(), key=lambda x: x[1], reverse=True)
    items = [(name, count) for name, count in items if (count / total) * 100 >= 1.0]
    # Show at most the 6 languages with the most bytes
    items = items[:6]

    if not items:
        return generate_empty_svg()

    # Recalculate proportions over the filtered set so bars stay clean
    total_display = sum(v for _, v in items)

    rows = ""
    y = 0
    row_h = 28
    margin_l = 10
    margin_r = 10
    bar_x = 145
    bar_w = 220
    pct_x = bar_x + bar_w + 10
    svg_w = 450

    for name, bytes_count in items:
        pct = (bytes_count / total_display) * 100
        bw = int((bytes_count / total_display) * bar_w)
        color = LANG_COLORS.get(name, "#736be4")
        pct_str = f"{pct:.1f}%"

        rows += f"""
  <text x="{margin_l}" y="{y + 16}" font-family="'Segoe UI', monospace" font-size="13" fill="#c3c9d4">{name}</text>
  <rect x="{bar_x}" y="{y + 8}" width="{bar_w}" height="10" rx="5" ry="5" fill="#161b22" />
  <rect x="{bar_x}" y="{y + 8}" width="{bw}" height="10" rx="5" ry="5" fill="{color}" />
  <text x="{pct_x}" y="{y + 17}" font-family="'Segoe UI', monospace" font-size="13" fill="#c3c9d4" text-anchor="start">{pct_str}</text>"""
        y += row_h

    h = y + 10
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{svg_w}" height="{h}" viewBox="0 0 {svg_w} {h}">
  <rect x="0" y="0" width="{svg_w}" height="{h}" rx="8" ry="8" fill="#0d1117" />
  {rows}
</svg>"""
    return svg

def generate_empty_svg():
    return """<svg xmlns="http://www.w3.org/2000/svg" width="440" height="80" viewBox="0 0 440 80">
  <rect x="0" y="0" width="440" height="80" rx="8" ry="8" fill="#0d1117" />
  <text x="220" y="45" font-family="'Segoe UI', monospace" font-size="14" fill="#c3c9d4" text-anchor="middle">No language data yet — push code to your repos!</text>
</svg>"""

FALLBACK_LANGS = {
    "Python": 150000,
    "C++": 68000,
    "HTML": 27000,
    "JavaScript": 16000,
    "Kotlin": 11000,
    "CSS": 5000,
}

def main():
    os.makedirs("dist", exist_ok=True)

    print("Fetching repos...")
    repos = get_repos()
    print(f"Found {len(repos)} repos")

    all_langs = collections.Counter()

    for repo in repos:
        if repo.get("fork"):
            print(f"  Skipping fork: {repo['full_name']}")
            continue
        if repo.get("name") == USERNAME:
            print(f"  Skipping profile repo: {repo['full_name']}")
            continue
        name = repo["full_name"]
        print(f"  Fetching languages for {name}...")
        langs = get_languages(name)
        if langs:
            print(f"    -> {langs}")
        else:
            print(f"    -> no language data")
        all_langs.update(langs)

    if not all_langs:
        print("No repos with language data found, using fallback")
        all_langs.update(FALLBACK_LANGS)

    svg = generate_svg(all_langs)

    with open("dist/github-languages.svg", "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"Generated SVG with {len(all_langs)} languages")

if __name__ == "__main__":
    main()
