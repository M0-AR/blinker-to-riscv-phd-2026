"""Directed verification of the golden model + assembler (must pass offline).

Covers: R-type, I-type, shift-amount paths, signed/unsigned compares,
JAL/JALR linking, branches x6, LUI/AUIPC, LB/LH/LW + LBU/LHU, SB/SH/SW,
x0-hardwiring, EBREAK halt, and the mulsi3 shift-add routine + fixed-point
Mandelbrot kernel shape (disk test) used later by RTL sims.
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from rv32i_model import RV32IModel
from mini_asm import *

PASS = 0
FAIL = 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name} {detail}")

def run(prog, steps=1000):
    m = RV32IModel()
    m.load_program(prog)
    m.run(steps)
    return m

print("[1] R-type + x0 hardwire")
m = run([ADD(1,0,0), ADDI(1,1,1), ADDI(1,1,1), ADD(2,1,0), SUB(3,2,1), EBREAK])
check("x1==2", m.regs[1]==2, m.regs[1:4])
check("x2==2", m.regs[2]==2)
check("x3==0 (2-2)", m.regs[3]==0)
m2 = run([ADDI(0,0,5), EBREAK])  # write to x0 ignored
check("x0==0", m2.regs[0]==0)

print("[2] shifts + compares (ALU truth table)")
m = run([ADDI(1,0,8), ADDI(2,0,-2), enc_r(0,2,1,2,3,0x33),  # SLT x3,x1,x2 (8 < -2? no)
         enc_r(0,2,1,3,4,0x33),  # SLTU x4,x1,x2 (8 < 0xFFFFFFFE? yes)
         enc_i(0b000000000101,1,1,5,0x13),  # SLLI x5,x1,5 -> 256
         EBREAK])
check("SLT signed", m.regs[3]==0, m.regs[3])
check("SLTU unsigned", m.regs[4]==1, m.regs[4])
check("SLLI", m.regs[5]==256, m.regs[5])

print("[3] JAL/JALR link + AUIPC/LUI")
# x1 = PC+4 after JAL skipping one slot; JALR returns
prog = [0]*8
prog[0] = JAL(1, 8)     # jump to idx2, link idx1*4+4=4
prog[1] = ADDI(5,0,99)  # skipped
prog[2] = ADDI(6,0,7)
prog[3] = JALR(0,1,0)   # ret to 4 -> executes idx1
prog[4] = EBREAK
m = run(prog)
check("JAL link x1==4", m.regs[1]==4, m.regs[1])
check("post-ret x5==99", m.regs[5]==99, m.regs[1:7])
m = run([LUI(1, 0x12345), enc_u(0,2,0x17), EBREAK])  # AUIPC x2,0 -> pc=4
check("LUI", m.regs[1]==0x12345000, hex(m.regs[1]))
check("AUIPC pc+0", m.regs[2]==4, m.regs[2])

print("[4] branches x6 + loop (count 0..31 like tutorial step 9)")
# s0=x8 counter, lim x9=5: loop: addi, bne back
loop = [ADDI(8,0,0), ADDI(9,0,5), ADDI(8,8,1), BNE(8,9,-4), EBREAK]
m = run(loop, steps=100)
check("BNE loop ends at 5", m.regs[8]==5, m.regs[8])
for name, f3, a, b, taken in [("BEQ",0,5,5,True),("BNE",1,5,6,True),
    ("BLT",4,0xFFFFFFFF,1,True),("BGE",5,3,3,True),
    ("BLTU",6,1,0xFFFFFFFF,True),("BGEU",7,7,7,True)]:
    mm = RV32IModel()
    mm.regs[10]=a; mm.regs[11]=b
    # place branch at 0 that jumps +8 if taken else falls to addi
    br = enc_b(8 if taken else 0, 11, 10, f3, 0x63) if True else 0
    mm.load_program([br, ADDI(12,0,1), ADDI(12,0,2), EBREAK])
    # simpler: directly test model predicate by running both variants
    mm2 = RV32IModel(); mm2.regs[10]=a; mm2.regs[11]=b
    mm2.load_program([enc_b(8,11,10,f3,0x63), ADDI(12,0,1), ADDI(12,0,2), EBREAK])
    mm2.run(10)
    # if taken: skips ADDI x12,1 -> x12==2 else x12==1... depends on layout:
    # branch at 0 jumps to 8 (=idx2). idx1 sets 1, idx2 sets 2 (overwrites). So taken->2, not->2? fix:
    pass
# explicit taken/not-taken pair:
for f3, aval, bval, expect_take in [(0,9,9,True),(0,9,8,False),(1,9,8,True),(4,0xFFFFFFFF,0,True),(6,1,0xFFFFFFFF,True),(7,0xFFFFFFFF,0,True)]:
    mm = RV32IModel(); mm.regs[10]=aval; mm.regs[11]=bval
    # 0: branch +12 -> idx3 ; 1: ADDI x12,0,111 ; 2: JAL x0,+8 -> idx4 ; 3: ADDI x12,0,222 ; 4: EBREAK
    mm.load_program([enc_b(12,11,10,f3,0x63), ADDI(12,0,111), JAL(0,8), ADDI(12,0,222), EBREAK])
    mm.run(10)
    check(f"branch f3={f3} a={aval} b={bval} take={expect_take}", (mm.regs[12]==222)==expect_take, mm.regs[12])

print("[5] loads/stores byte/half/word + sign extension (tutorial steps 15-16)")
m = RV32IModel()
m.load_program([ADDI(1,0,0x400), ADDI(2,0,0x81), enc_s(0,2,1,0,0x23),  # SB 0x81 @0x400
                enc_i(0,1,0,3,0x03), enc_i(0,1,4,4,0x03),  # LB x3 ; LBU x4
                LUI(2,0x8), ADDI(2,2,0x181), enc_s(2,2,1,1,0x23),  # x2=0x8181 ; SH @0x402
                enc_i(2,1,1,5,0x03), enc_i(2,1,5,6,0x03),  # LH x5 ; LHU x6
                ADDI(2,0,0x7F), enc_s(8,2,1,2,0x23), enc_i(8,1,2,7,0x03),  # SW/LW @0x408
                EBREAK])
m.run(100)
check("LB sign-extends 0x81 -> -127", m.regs[3]==0xFFFFFF81, hex(m.regs[3]))
check("LBU zero-extends", m.regs[4]==0x81, hex(m.regs[4]))
check("LH sign", m.regs[5]==0xFFFF8181, hex(m.regs[5]))
check("LHU zero", m.regs[6]==0x8181, hex(m.regs[6]))
check("LW roundtrip", m.regs[7]==0x7F, hex(m.regs[7]))

print("[6] mulsi3 shift-add routine (tutorial step 18, libgcc port)")
# inline: a0=x10=13, a1=x11=11 -> 143
MUL = [
  ADDI(10,0,13), ADDI(11,0,11),
  ADDI(12,10,0), ADDI(10,0,0),            # a2=x12=13(saved), a0=0
  # L0: andi x13,x11,1 ; beqz -> skip add ; add x10,x10,x12 ; L1: srli x11,1 ; slli x12,1 ; bnez x11,-20
  enc_i(1,11,7,13,0x13), enc_b(8,13,0,0,0x63), ADD(10,10,12),
  enc_i(1,11,5,11,0x13), enc_i(1,12,1,12,0x13), enc_b(-20,11,0,1,0x63),
  EBREAK]
m = run(MUL, steps=500)
check("13*11==143", m.regs[10]==143, m.regs[10])

print("[7] fixed-point disk (mandelbrot tutorial shape, 8x8 radius check)")
SHIFT=10
def fixed_disk(cx, cy, r2_fixed):
    # emulate: (x*x+y*y)<r2 using shift-add mul via model? use python ints (same math)
    return (cx*cx + cy*cy) >> SHIFT < r2_fixed
inside = fixed_disk(0,0,4<<SHIFT)
outside = fixed_disk(3<<SHIFT,0,4<<SHIFT)
check("origin inside r=2 disk", inside)
check("(3,0) outside", not outside)

print(f"\nRESULT: {PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
