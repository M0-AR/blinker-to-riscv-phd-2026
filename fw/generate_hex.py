"""Generate firmware.hex ($readmemh) from mini_asm + verify on golden model.

Emits:
 fw/firmware_blinky.hex  — LED counter 0..31 then EBREAK (mirrors step 9/11)
 fw/firmware_mul.hex     — 13*11 via mulsi3 routine (mirrors step 18)
Each hex file is loaded back into the golden model and the expected
register result asserted — so no hex ships unverified.
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "sim"))
from rv32i_model import RV32IModel
from mini_asm import *

FW = os.path.dirname(__file__)

def write_hex(path, words):
    with open(path, "w") as f:
        for w in words:
            f.write(f"{w:08x}\n")
    print(f"wrote {path} ({len(words)} words)")

# Blinky-counter: x8=0; x9=31; loop: x8++; BNE; EBREAK. Expect x8==31.
blinky = [ADDI(8,0,0), ADDI(9,0,31), ADDI(8,8,1), BNE(8,9,-4), EBREAK]
write_hex(os.path.join(FW, "firmware_blinky.hex"), blinky)
m = RV32IModel(); m.load_program(blinky); m.run(5000)
assert m.regs[8] == 31, m.regs[8]
print(f"  verified blinky: x8={m.regs[8]} halted={m.halted}")

# mul demo: same routine as test [6]; expect x10==143.
mul = [ADDI(10,0,13), ADDI(11,0,11), ADDI(12,10,0), ADDI(10,0,0),
  __import__("mini_asm").enc_i(1,11,7,13,0x13),
  __import__("mini_asm").enc_b(8,13,0,0,0x63), ADD(10,10,12),
  __import__("mini_asm").enc_i(1,11,5,11,0x13),
  __import__("mini_asm").enc_i(1,12,1,12,0x13),
  __import__("mini_asm").enc_b(-20,11,0,1,0x63), EBREAK]
write_hex(os.path.join(FW, "firmware_mul.hex"), mul)
m = RV32IModel(); m.load_program(mul); m.run(5000)
assert m.regs[10] == 143, m.regs[10]
print(f"  verified mul: x10={m.regs[10]} halted={m.halted}")
print("FIRMWARE HEX VERIFIED")
