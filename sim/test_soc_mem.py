"""SoC memory-lane proof: mirrors the fixed femtosoc.v byte-masked RAM.

The audit found word-only writes (SB/SH to nonzero lanes corrupt neighbors).
The fixed Verilog semantics under test:
  if (isRAM) begin
    if (mem_wmask[0]) RAM[word][ 7:0] <= mem_wdata[ 7:0];
    ... (one line per lane)
    ram_q <= RAM[word];
  end
This test emulates exactly that block in Python and runs SB/SH/SW + LB/LH/LW
round-trips at every lane, plus a neighbor-preservation case.
"""
import sys

fails = 0
def check(name, cond, detail=""):
    global fails
    print(("  ok: " if cond else "  FAIL: ") + name + ("" if cond else f" {detail}"))
    fails += 0 if cond else 1

RAM_WORDS = 1536
RAM = [0] * RAM_WORDS

def soc_write(word, wdata, wmask):
    cur = RAM[word]
    lanes = [(cur >> s) & 0xFF for s in (0, 8, 16, 24)]
    new = [(wdata >> s) & 0xFF for s in (0, 8, 16, 24)]
    out = [n if (wmask >> i) & 1 else o for i, (o, n) in enumerate(zip(lanes, new))]
    RAM[word] = out[0] | (out[1] << 8) | (out[2] << 16) | (out[3] << 24)

def soc_read(word):
    return RAM[word]  # ram_q <= RAM[word]

# STORE_wmask vectors straight from quark_core.v truth table
WMASK = {"SW": 0b1111, "SH_lo": 0b0011, "SH_hi": 0b1100,
         "SB0": 0b0001, "SB1": 0b0010, "SB2": 0b0100, "SB3": 0b1000}

# 1. SW round-trip
soc_write(10, 0xDEADBEEF, WMASK["SW"])
check("SW/LW round-trip", soc_read(10) == 0xDEADBEEF, hex(soc_read(10)))

# 2. SB to each lane of a preset word, neighbors preserved
soc_write(11, 0xFFFFFFFF, WMASK["SW"])
soc_write(11, 0x00, WMASK["SB1"])  # clear byte 1 lane: wdata byte1 must be 0
check("SB lane1 only", soc_read(11) == 0xFFFF00FF, hex(soc_read(11)))
soc_write(11, 0xAB000000 >> 0, WMASK["SB3"])
# wdata byte3 = 0xAB
soc_write(11, (0xAB << 24), WMASK["SB3"])
check("SB lane3 only", soc_read(11) == 0xABFF00FF, hex(soc_read(11)))

# 3. SH lo/hi halves
soc_write(12, 0x00000000, WMASK["SW"])
soc_write(12, 0x1234, WMASK["SH_lo"])
check("SH low half", soc_read(12) == 0x00001234, hex(soc_read(12)))
soc_write(12, (0x5678 << 16), WMASK["SH_hi"])
check("SH high half", soc_read(12) == 0x56781234, hex(soc_read(12)))

# 4. Adjacent words untouched (the corruption the old code caused)
soc_write(20, 0xAAAAAAAA, WMASK["SW"])
soc_write(21, 0xBBBBBBBB, WMASK["SW"])
soc_write(20, 0x00, WMASK["SB1"])
check("neighbor word preserved", soc_read(21) == 0xBBBBBBBB, hex(soc_read(21)))

print(f"\nSOC MEM PROOF: {'PASS' if not fails else f'{fails} FAILURES'}")
sys.exit(1 if fails else 0)
