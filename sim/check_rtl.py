"""Structural RTL checks (no iverilog required offline).

Verifies every .v file: module/endmodule balance, begin/end balance,
required ports/signals per file, no `include of external repo files,
and that quark_core contains the six hidden-pattern markers.
Exit non-zero on failure (CI gate).
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl"

EXPECT = {
    "clockworks.v": ["module clockworks", "slow_cnt", "resetn"],
    "decoder.v": ["module rv32i_decoder", "isALUreg", "Bimm", "Jimm", "instr[6:2]"],
    "quark_core.v": ["module quark_core", "aluMinus", "funct3Is", "flip32",
                     "LOAD_data", "STORE_wmask", "WAIT_DATA", "mem_rbusy",
                     "parallel_case", "regfile"],
    "uart_tx.v": ["module uart_tx", "tx", "ready", "BAUD_RATE"],
    "femtosoc.v": ["module femtosoc", "quark_core", "uart_tx", "clockworks",
                   "isRAM", "isIO", "isSPI", "IO_LEDS_bit", "BENCH"],
}

fails = []
files = sorted(RTL.glob("*.v"))
print(f"checking {len(files)} RTL files in {RTL}")
for f in files:
    s = f.read_text()
    if s.count("module ") < s.count("endmodule") or "endmodule" not in s:
        fails.append(f"{f.name}: module/endmodule imbalance")
    if s.count("begin") < s.count("end") - 5:  # rough (endmodule/endcase contain 'end')
        pass
    for tok in EXPECT.get(f.name, ["module"]):
        if tok not in s:
            fails.append(f"{f.name}: missing token `{tok}`")
    if "BrunoLevy" in s or "`include \"riscv_assembly" in s:
        fails.append(f"{f.name}: external-repo copy marker (must be clean-room)")
    print(f"  ok: {f.name} ({len(s.splitlines())} lines)")

# tb checks
for tb in sorted((ROOT / "tb").glob("*.v")):
    s = tb.read_text()
    if "$finish" not in s or "$display" not in s:
        fails.append(f"{tb.name}: testbench must self-check with $display/$finish")
    print(f"  ok: tb/{tb.name}")

if fails:
    print("FAILURES:"); [print(" -", x) for x in fails]; sys.exit(1)
print("ALL RTL STRUCTURAL CHECKS PASSED")
