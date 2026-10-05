"""Clean-room RV32I golden model (functional, not cycle-accurate).

Purpose: independent oracle for verifying the Verilog quark_core.
Implements RV32I integer subset used by the From-Blinker-to-RISC-V path:
 R-type, I-type ALU, loads/stores (LB/H/W + unsigned), branches x6,
 JAL/JALR, LUI/AUIPC, EBREAK-as-halt. No CSRs, no FENCE (NOP), no M ext.

Memory: flat byte-addressed dict-backed list, little-endian, word-aligned
instruction fetch at PC, PC+=4. x0 hardwired to 0.

Verified by: sim/test_golden_model.py (executed, not hand-waved).
"""

MASK32 = 0xFFFFFFFF


def mask32(v):
    return v & MASK32


def to_signed(v):
    v &= MASK32
    return v - 0x100000000 if v & 0x80000000 else v


def sign_extend(v, bits):
    m = 1 << (bits - 1)
    v &= (1 << bits) - 1
    return (v ^ m) - m


class RV32IModel:
    def __init__(self, mem_words=1536):  # 6 KiB like IceStick BRAM
        self.mem = bytearray(mem_words * 4)
        self.reset()

    def reset(self):
        self.regs = [0] * 32
        self.pc = 0
        self.halted = False
        self.cycles = 0  # instruction count (functional)
        self.trace = []

    # ---- memory helpers (little-endian, RISC-V) ----
    def store_word(self, addr, val):
        val &= MASK32
        for i in range(4):
            self.mem[addr + i] = (val >> (8 * i)) & 0xFF

    def load_word(self, addr):
        return (
            self.mem[addr]
            | (self.mem[addr + 1] << 8)
            | (self.mem[addr + 2] << 16)
            | (self.mem[addr + 3] << 24)
        )

    def load_program(self, words, base=0):
        for i, w in enumerate(words):
            self.store_word(base + 4 * i, w)

    # ---- one step ----
    def step(self):
        if self.halted:
            return False
        instr = self.load_word(self.pc)
        # EBREAK = 0x00100073 halts (SYSTEM class minimal support)
        if instr == 0x00100073:
            self.halted = True
            self.trace.append((self.pc, instr, "EBREAK"))
            return False
        opcode = instr & 0x7F
        rd = (instr >> 7) & 0x1F
        funct3 = (instr >> 12) & 0x7
        rs1 = (instr >> 15) & 0x1F
        rs2 = (instr >> 20) & 0x1F
        funct7 = (instr >> 25) & 0x7F

        def wr(idx, val):
            if idx != 0:
                self.regs[idx] = mask32(val)

        pc = self.pc
        nxt = mask32(pc + 4)

        if opcode == 0x33:  # OP (R-type)
            a, b = self.regs[rs1], self.regs[rs2]
            if funct3 == 0x0:
                res = mask32(a - b) if funct7 & 0x20 else mask32(a + b)
            elif funct3 == 0x1:
                res = mask32(a << (b & 31))
            elif funct3 == 0x2:
                res = 1 if to_signed(a) < to_signed(b) else 0
            elif funct3 == 0x3:
                res = 1 if a < b else 0
            elif funct3 == 0x4:
                res = a ^ b
            elif funct3 == 0x5:
                sh = b & 31
                res = (to_signed(a) >> sh) & MASK32 if funct7 & 0x20 else (a >> sh)
            elif funct3 == 0x6:
                res = a | b
            elif funct3 == 0x7:
                res = a & b
            wr(rd, res)
        elif opcode == 0x13:  # OP-IMM
            imm = sign_extend(instr >> 20, 12)
            a = self.regs[rs1]
            sh = (instr >> 20) & 31
            if funct3 == 0x0:
                wr(rd, mask32(a + imm))
            elif funct3 == 0x1:
                wr(rd, mask32(a << sh))
            elif funct3 == 0x2:
                wr(rd, 1 if to_signed(a) < imm else 0)
            elif funct3 == 0x3:
                wr(rd, 1 if a < (imm & MASK32) else 0)
            elif funct3 == 0x4:
                wr(rd, mask32(a ^ (imm & MASK32)))
            elif funct3 == 0x5:
                if funct7 & 0x20:
                    wr(rd, (to_signed(a) >> sh) & MASK32)
                else:
                    wr(rd, a >> sh)
            elif funct3 == 0x6:
                wr(rd, mask32(a | (imm & MASK32)))
            elif funct3 == 0x7:
                wr(rd, mask32(a & (imm & MASK32)))
        elif opcode == 0x03:  # LOAD
            imm = sign_extend(instr >> 20, 12)
            addr = mask32(self.regs[rs1] + imm)
            if funct3 == 0x2:
                wr(rd, self.load_word(addr & ~3))
            elif funct3 == 0x0:  # LB
                b = self.mem[addr]
                wr(rd, mask32(sign_extend(b, 8)))
            elif funct3 == 0x4:  # LBU
                wr(rd, self.mem[addr])
            elif funct3 == 0x1:  # LH
                lo = self.mem[addr] | (self.mem[addr + 1] << 8)
                wr(rd, mask32(sign_extend(lo, 16)))
            elif funct3 == 0x5:  # LHU
                wr(rd, self.mem[addr] | (self.mem[addr + 1] << 8))
        elif opcode == 0x23:  # STORE
            imm = sign_extend(((instr >> 25) << 5) | ((instr >> 7) & 0x1F), 12)
            addr = mask32(self.regs[rs1] + imm)
            v = self.regs[rs2]
            if funct3 == 0x2:
                self.store_word(addr & ~3, v)
            elif funct3 == 0x0:
                self.mem[addr] = v & 0xFF
            elif funct3 == 0x1:
                self.mem[addr] = v & 0xFF
                self.mem[addr + 1] = (v >> 8) & 0xFF
        elif opcode == 0x63:  # BRANCH
            imm = sign_extend(
                (((instr >> 31) & 1) << 12)
                | (((instr >> 7) & 1) << 11)
                | (((instr >> 25) & 0x3F) << 5)
                | (((instr >> 8) & 0xF) << 1),
                13,
            )
            a, b = self.regs[rs1], self.regs[rs2]
            take = False
            if funct3 == 0x0:
                take = a == b
            elif funct3 == 0x1:
                take = a != b
            elif funct3 == 0x4:
                take = to_signed(a) < to_signed(b)
            elif funct3 == 0x5:
                take = to_signed(a) >= to_signed(b)
            elif funct3 == 0x6:
                take = a < b
            elif funct3 == 0x7:
                take = a >= b
            if take:
                nxt = mask32(pc + imm)
        elif opcode == 0x6F:  # JAL
            imm = sign_extend(
                (((instr >> 31) & 1) << 20)
                | (((instr >> 12) & 0xFF) << 12)
                | (((instr >> 20) & 1) << 11)
                | (((instr >> 21) & 0x3FF) << 1),
                21,
            )
            wr(rd, mask32(pc + 4))
            nxt = mask32(pc + imm)
        elif opcode == 0x67:  # JALR
            imm = sign_extend(instr >> 20, 12)
            wr(rd, mask32(pc + 4))
            nxt = mask32((self.regs[rs1] + imm) & ~1)
        elif opcode == 0x37:  # LUI
            wr(rd, instr & 0xFFFFF000)
        elif opcode == 0x17:  # AUIPC
            wr(rd, mask32(pc + (instr & 0xFFFFF000)))
        elif opcode == 0x0F:  # FENCE -> NOP
            pass
        else:
            raise ValueError(f"illegal opcode 0x{opcode:02x} at pc=0x{pc:08x}")
        self.pc = nxt
        self.cycles += 1
        self.trace.append((pc, instr, f"rd=x{rd}"))
        return True

    def run(self, max_steps=100000):
        n = 0
        while n < max_steps and self.step():
            n += 1
        return n
