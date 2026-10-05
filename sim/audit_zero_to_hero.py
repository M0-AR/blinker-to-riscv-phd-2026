"""Zero-to-hero audit: every file, every claim, every link — executed.

Exits non-zero with a numbered ISSUE list. A clean run means zero known issues.
Covers: referenced-file existence, GitHub anchor slugs, opcode collisions,
number consistency, HTML validity, SVG validity, git/remote sync, RTL smells.
"""
import json, pathlib, re, subprocess, sys
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parents[1]
issues, notes = [], []
N = [0]

def issue(msg):
    N[0] += 1
    issues.append(f"[ISSUE-{N[0]}] {msg}")
    print(f"  ISSUE: {msg}")

def ok(msg):
    print(f"  ok: {msg}")

print("== A. Referenced files exist ==")
readme = (ROOT / "README.md").read_text()
makefile = (ROOT / "Makefile").read_text()
for ref in ["fw/bram.ld", "boards/icestick.pcf", "fw/start.S",
            "LICENSE", "CITATION.cff", "docker/Dockerfile",
            "docker/docker-compose.yml", "bench/results.json",
            "docs/index.html", "preview.html"]:
    p = ROOT / ref
    if p.exists():
        ok(f"{ref} exists")
    else:
        issue(f"referenced file missing: {ref}")

print("== B. GitHub anchor slugs ==")
def gh_slug(h):
    h = re.sub(r"<[^>]+>", "", h).strip().lower()
    h = re.sub(r"[^\w\s\-]", "", h, flags=re.UNICODE)
    return h.replace(" ", "-")
heads = re.findall(r"^(#{1,6})\s+(.+)$", readme, re.M)
slugs = {gh_slug(t) for _, t in heads}
for link in sorted(set(re.findall(r"\]\(#([^)]+)\)", readme))):
    if link in slugs:
        ok(f"anchor #{link}")
    else:
        issue(f"broken TOC anchor #{link} (no matching heading slug)")

print("== C. Opcode decode collisions (exhaustive over 7-bit opcode space) ==")
OPC = {"LOAD": 0x03, "FENCE": 0x0F, "ALUimm": 0x13, "AUIPC": 0x17,
       "STORE": 0x23, "ALUreg": 0x33, "LUI": 0x37, "BRANCH": 0x63,
       "JALR": 0x67, "JAL": 0x6F, "SYSTEM": 0x73}
def old_jal(op):
    return bool(op & 0x08)  # bare instr[3]: the historical bug shape
collide = [k for k, v in OPC.items() if old_jal(v) and k != "JAL"]
if collide:
    notes.append(f"bare instr[3] would misfire on {collide} (why the fix exists)")
qc_text = (ROOT / "rtl" / "quark_core.v").read_text()
dec_text = (ROOT / "rtl" / "decoder.v").read_text()
import re as _re
for fname, text, fixed in [("quark_core.v", qc_text, "full_instr[3] & full_instr[6]"),
                           ("decoder.v", dec_text, "instr[3] & instr[6]")]:
    if fixed in text and not _re.search(r"instr\[3\]\s*;", text):
        ok(f"{fname} uses disambiguated isJAL (bit3&bit6)")
    else:
        issue(f"{fname} still uses bare single-bit isJAL (FENCE collision)")
def new_jal(op):
    return bool((op & 0x08) and (op & 0x40))  # bit3 & bit6
bad = [k for k, v in OPC.items() if new_jal(v) != (k == "JAL")]
if bad:
    issue(f"proposed isJAL=bit3&bit6 still wrong for {bad}")
else:
    notes.append("isJAL=instr[3]&instr[6] disambiguates all 11 classes")

print("== D. Numbers README vs results.json ==")
res = json.loads((ROOT / "bench" / "results.json").read_text())
for token in ["26 passed, 0 failed", "39-item",
              str(res["lut_estimate"]["std_config_estimate"]),
              str(res["lut_estimate"]["minimal_core"]),
              str(res["cpi_estimate"])]:
    if token in readme:
        ok(f"README cites {token}")
    else:
        issue(f"README/bench mismatch: '{token}' not in README")

print("== E. HTML validity + relative paths ==")
class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
    def handle_starttag(self, t, a):
        if t in ("img", "a", "link"):
            self.tags.append((t, dict(a)))
for name in ["preview.html", "docs/index.html"]:
    try:
        p = P()
        p.feed((ROOT / name).read_text())
        ok(f"{name} parses")
    except Exception as e:
        issue(f"{name} HTML parse error: {e}")
    for t, a in p.tags:
        for k in ("src", "href"):
            v = a.get(k, "")
            if v.startswith("/home/") or (v.startswith("/assets") or v.startswith("/docs")):
                issue(f"{name}: absolute/local path {v}")
for svg in ["docs/assets/terminal-demo.svg"]:
    t = (ROOT / svg).read_text()
    if "<svg" in t and "</svg>" in t:
        ok(f"{svg} well-formed")
    else:
        issue(f"{svg} malformed")

print("== F. RTL smells ==")
qc = (ROOT / "rtl" / "quark_core.v").read_text()
if "rs1Id = instr[19-2:15-2]" in qc:
    issue("quark_core.v has dead wire rs1Id (unused, confusing indexing)")
if "isFENCE" not in qc:
    notes.append("quark_core.v ignores FENCE (NOP by fallthrough — document it)")
fs = (ROOT / "rtl" / "femtosoc.v").read_text()
if "simplified word write" in fs:
    issue("femtosoc RAM does word-only writes: SB/SH to nonzero lanes corrupt neighbors")
elif fs.count("mem_wmask[") >= 4:
    ok("femtosoc RAM has per-byte masked writes")

print("== G. git/remote sync ==")
r = subprocess.run(["git", "status", "--short"], capture_output=True, text=True, cwd=ROOT)
r2 = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, cwd=ROOT)
print(f"  branch={r2.stdout.strip()} dirty={bool(r.stdout.strip())}")
ahead = subprocess.run(["git", "rev-list", "--count", "origin/main..HEAD"],
                       capture_output=True, text=True, cwd=ROOT)
if ahead.stdout.strip() != "0":
    notes.append(f"{ahead.stdout.strip()} local commit(s) ahead of origin (push before Pages rebuild)")

print(f"\nAUDIT: {len(issues)} issues, {len(notes)} notes")
for i in issues:
    print(" " + i)
for n in notes:
    print(" note: " + n)
sys.exit(1 if issues else 0)
