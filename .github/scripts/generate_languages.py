import os
import json
import urllib.request
import collections

USERNAME = "HernanFx"
TOKEN = os.environ.get("GITHUB_TOKEN", "")

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
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())

def get_repos():
    repos = []
    page = 1
    while True:
        data = req(f"https://api.github.com/users/{USERNAME}/repos?per_page=100&page={page}&type=public")
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

    items = sorted(languages.items(), key=lambda x: x[1], reverse=True)
    total_display = sum(v for _, v in items)

    bars = []
    y = 0
    for name, bytes_count in items:
        pct = (bytes_count / total_display) * 100
        bar_w = int((bytes_count / total_display) * 280)
        color = LANG_COLORS.get(name, "#736be4")
        pct_str = f"{pct:.1f}%"

        bars.append(f"""
    <tr style="border: none;">
      <td style="border: none; text-align: left; font-family: 'Segoe UI', monospace; font-size: 13px; color: #c3c9d4; padding: 5px 15px; width: 90px;">{name}</td>
      <td style="border: none; padding: 5px 0;">
        <svg width="280" height="8" xmlns="http://www.w3.org/2000/svg"><rect x="0" y="0" width="280" height="8" rx="4" ry="4" fill="#161b22"/><rect x="0" y="0" width="{bar_w}" height="8" rx="4" ry="4" fill="{color}"/></svg>
      </td>
      <td style="border: none; text-align: right; font-family: 'Segoe UI', monospace; font-size: 13px; color: #c3c9d4; padding: 5px 15px; width: 50px;">{pct_str}</td>
    </tr>""")
        y += 1

    bars_html = "\n".join(bars)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="520" height="{len(items) * 28 + 20}" viewBox="0 0 520 {len(items) * 28 + 20}">
  <foreignObject width="100%" height="100%">
    <div xmlns="http://www.w3.org/1999/xhtml" style="font-family: 'Segoe UI', sans-serif; background: transparent;">
      <table style="border-collapse: collapse; border: none; margin: 0;">
        {bars_html}
      </table>
    </div>
  </foreignObject>
</svg>"""
    return svg

def generate_empty_svg():
    return """<svg xmlns="http://www.w3.org/2000/svg" width="400" height="60" viewBox="0 0 400 60">
  <foreignObject width="100%" height="100%">
    <div xmlns="http://www.w3.org/1999/xhtml" style="font-family: 'Segoe UI', sans-serif; background: transparent; text-align: center; padding-top: 20px;">
      <span style="color: #c3c9d4; font-size: 14px;">No language data yet — push code to your repos!</span>
    </div>
  </foreignObject>
</svg>"""

def main():
    os.makedirs("dist", exist_ok=True)

    repos = get_repos()
    all_langs = collections.Counter()

    for repo in repos:
        if repo.get("fork"):
            continue
        langs = get_languages(repo["full_name"])
        all_langs.update(langs)

    svg = generate_svg(all_langs)

    with open("dist/github-languages.svg", "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"Generated SVG with {len(all_langs)} languages from {len(repos)} repos")

if __name__ == "__main__":
    main()
