"""Docs gate: README + preview.html + Pages copy verified by execution.

Checks (fail = non-zero exit):
 - README has CEO summary, TOC, beginner guide, features, user stories,
   quick start, install, usage, architecture, journey, verification,
   boards, firmware, pages, screenshots/video, roadmap, contributing,
   license, acknowledgments, FAQ.
 - README never names internal research tooling, never says 'donkey'.
 - Numbers in README match bench/results.json (26/26, 100.0/39, 1180/980/1280, 4.25).
 - preview.html + docs/index.html exist, reference existing assets, have
   hero/stats/quickstart/journey/numbers/stories + closing footer.
 - docs/assets/terminal-demo.svg exists and is valid SVG.
 - docs/assets/preview.png exists (Playwright screenshot step).
"""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
fails = []

def need(cond, msg):
    print(("  ok: " if cond else "  FAIL: ") + msg)
    if not cond:
        fails.append(msg)

res = json.loads((ROOT / "bench" / "results.json").read_text())
readme = (ROOT / "README.md").read_text()
preview = (ROOT / "preview.html").read_text()
index = (ROOT / "docs" / "index.html").read_text()

# --- README sections ---
for sec in ["Executive summary", "Table of Contents", "Beginner guide",
            "Features", "User stories", "Quick start", "Installation",
            "Usage", "Architecture", "journey", "Verification",
            "Boards", "Firmware", "GitHub Pages", "Screenshots & video",
            "Roadmap", "Contributing", "License", "Acknowledgments", "FAQ"]:
    need(sec.lower() in readme.lower(), f"README section: {sec}")
need("🌱" in readme, "README has beginner-guide seedling marker")

# --- forbidden content in README ---
for banned in ["websearch", "searxng", "agent-reach", "openresearch",
               "paper-search", "duckduckgo_search", "gitmcp", "kaggle",
               "superpowers", "gsd_websearch", "donkey", "donky"]:
    need(banned.lower() not in readme.lower(), f"README never mentions '{banned}'")

# --- numbers match live results ---
need("26 passed, 0 failed" in readme, "README cites 26/26 golden result")
need(str(res["isa_coverage"]["pct"]) in readme and "39-item" in readme,
     "README coverage matches results.json (100.0 / 39)")
need(str(res["lut_estimate"]["std_config_estimate"]) in readme
     and str(res["lut_estimate"]["minimal_core"]) in readme
     and "1280" in readme, "README LUT numbers match (1180/980/1280)")
need(str(res["cpi_estimate"]) in readme, "README CPI matches (4.25)")

# --- pages ---
for name, html in [("preview.html", preview), ("docs/index.html", index)]:
    for token in ["From Blinker", "Quick start", "journey", "Live numbers",
                  "Who is this for", "Settings → Pages"]:
        need(token in html, f"{name} contains '{token}'")
need((ROOT / "docs" / "assets" / "terminal-demo.svg").read_text().lstrip().startswith("<svg"),
     "terminal-demo.svg is valid SVG")
need("|\n" not in preview, "preview.html has no markdown artifacts")

# --- Pages mirrors (robust under either source setting) ---
docs_preview = (ROOT / "docs" / "preview.html").read_text()
need(docs_preview == (ROOT / "docs" / "index.html").read_text(),
     "docs/preview.html mirrors docs/index.html exactly")
need('src="assets/terminal-demo.svg"' in docs_preview,
     "docs/preview.html uses source-relative asset path")
need('src="docs/assets/terminal-demo.svg"' in preview,
     "root preview.html uses root-relative asset path")
root_index = (ROOT / "index.html").read_text()
need('url=preview.html' in root_index and 'docs/preview.html' in root_index,
     "root index.html redirects with fallbacks")
for nj in [ROOT / ".nojekyll", ROOT / "docs" / ".nojekyll"]:
    need(nj.exists(), f"{nj.relative_to(ROOT)} exists (Jekyll bypass)")

# --- screenshots ---
png = ROOT / "docs" / "assets" / "preview.png"
need(png.exists() and png.stat().st_size > 10000,
     f"docs/assets/preview.png screenshot exists ({png.stat().st_size if png.exists() else 0} bytes)")

# --- README asset references resolve ---
need("docs/assets/preview.png" in readme, "README links preview.png")
need("docs/assets/terminal-demo.svg" in readme, "README links terminal-demo.svg")
need("docs/index.html" in readme, "README links Pages entry")

print(f"\nDOCS GATE: {'PASS' if not fails else f'{len(fails)} FAILURES'}")
sys.exit(1 if fails else 0)
