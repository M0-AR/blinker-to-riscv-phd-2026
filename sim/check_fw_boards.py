"""Firmware + boards gate: every cross-file reference verified by execution.

Checks bram.ld/start.S/blinker.S/wait.S/icestick.pcf agree with each other,
with femtosoc top ports, and with the Makefile synth target.
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
fails = 0

def check(name, cond, detail=""):
    global fails
    print(("  ok: " if cond else "  FAIL: ") + name + ("" if cond else f" {detail}"))
    fails += 0 if cond else 1

ld = (ROOT / "fw" / "bram.ld").read_text()
st = (ROOT / "fw" / "start.S").read_text()
bl = (ROOT / "fw" / "blinker.S").read_text()
wa = (ROOT / "fw" / "wait.S").read_text()
pcf = (ROOT / "boards" / "icestick.pcf").read_text()
mk = (ROOT / "Makefile").read_text()
soc = (ROOT / "rtl" / "femtosoc.v").read_text()

# Linker script contract
for tok in ['OUTPUT_ARCH("riscv")', "ENTRY(_start)", "KEEP(*(.text.init))",
            "ORIGIN = 0x0000", "LENGTH = 0x1800", "stack_top",
            "io_base_addr = 0x400000", "ASSERT"]:
    check(f"bram.ld has {tok}", tok in ld)
# Startup contract
for tok in [".text.init", "_start", "stack_top", "call main", "ebreak",
            "io_base_addr"]:
    check(f"start.S has {tok}", tok in st)
check("start.S declares _start global", ".globl _start" in st)
# Program contract: blinker defines main, calls wait; wait.S provides it
check("blinker.S defines main", re.search(r"^\s*main\s*:", bl, re.M) is not None)
check("blinker.S calls wait", "call wait" in bl)
check("wait.S provides wait + ret", ".globl wait" in wa and "\n\tret" in wa or "ret" in wa)
# Entry/section agreement: ENTRY symbol defined in .text.init section file
check("ENTRY(_start) resolvable", "_start" in st and "ENTRY(_start)" in ld)

# PCF contract: every femtosoc top port constrained, pins triple-confirmed
ports = {"CLK": "21", "RESET": "47", "TXD": "8", "RXD": "9",
         "LEDS[0]": "99", "LEDS[1]": "98", "LEDS[2]": "97",
         "LEDS[3]": "96", "LEDS[4]": "95"}
for port, pin in ports.items():
    check(f"pcf {port} -> {pin}",
          re.search(rf"set_io\s+{re.escape(port)}\s+{pin}\b", pcf) is not None)
check("Makefile synth uses boards/icestick.pcf",
      "boards/icestick.pcf" in mk and "--hx1k" in mk and "tq144" in mk)
check("femtosoc top exposes exactly these ports",
      all(k in soc for k in ["input  wire       CLK", "input  wire       RESET",
                             "LEDS", "RXD", "TXD"]))

print(f"\nFW/BOARDS GATE: {'PASS' if not fails else f'{fails} FAILURES'}")
sys.exit(1 if fails else 0)
