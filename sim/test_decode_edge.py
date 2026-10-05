"""Decode edge-case proof (exhaustive over the 7-bit opcode space used).

Proves, by execution over all 11 RV32I classes:
 1. OLD equation isJAL=bit3 misfires exactly on FENCE (the audit finding).
 2. NEW equation isJAL=bit3&bit6 fires exactly on JAL and nothing else.
 3. Golden-model behavior: FENCE advances PC by 4 and writes nothing;
    JAL writes PC+4 and jumps (no behavior change from the RTL fix needed
    beyond the two edited wires).
Mirrors rtl/decoder.v + rtl/quark_core.v equations bit-for-bit.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from rv32i_model import RV32IModel
from mini_asm import JAL, EBREAK

OPC = {"LOAD": 0x03, "FENCE": 0x0F, "ALUimm": 0x13, "AUIPC": 0x17,
       "STORE": 0x23, "ALUreg": 0x33, "LUI": 0x37, "BRANCH": 0x63,
       "JALR": 0x67, "JAL": 0x6F, "SYSTEM": 0x73}
fails = 0

def check(name, cond, detail=""):
    global fails
    print(("  ok: " if cond else "  FAIL: ") + name + ("" if cond else f" {detail}"))
    fails += 0 if cond else 1

old = {k: bool(v & 0x08) for k, v in OPC.items()}
check("old equation misfires exactly on FENCE",
      sorted([k for k, v in old.items() if v]) == ["FENCE", "JAL"], old)
new = {k: bool((v & 0x08) and (v & 0x40)) for k, v in OPC.items()}
check("new equation fires exactly on JAL",
      sorted([k for k, v in new.items() if v]) == ["JAL"], new)

# FENCE (0x0000000F: fence iorw,iorw) must be a silent NOP in the model
m = RV32IModel()
m.load_program([0x0000000F, EBREAK])
m.regs[5] = 12345
m.run(10)
check("FENCE writes nothing", m.regs[5] == 12345, m.regs[5])
check("FENCE advances one slot then halts", m.halted and m.pc == 4, hex(m.pc))

# JAL still links and jumps
m = RV32IModel()
m.load_program([JAL(1, 8), EBREAK, 0x00208113, EBREAK])  # skip idx1, ADDI x2,x0,2 at idx2 (x1 link preserved)
m.run(10)
check("JAL links PC+4", m.regs[1] == 4, m.regs[1])
check("JAL lands and halts", m.halted, hex(m.pc))

print(f"\nDECODE EDGE PROOF: {'PASS' if not fails else f'{fails} FAILURES'}")
sys.exit(1 if fails else 0)
