"""Minimal RV32I assembler for directed tests (clean-room, spec-derived).

Encoders follow the RISC-V unprivileged spec v20191213, Chapter 2 +
instruction listings (the same normative source the tutorial cites).
Only what the verification suite needs; cross-checked against
hand-computed vectors in sim/test_golden_model.py.
"""


def enc_r(f7, rs2, rs1, f3, rd, op):
    return ((f7 & 0x7F) << 25) | ((rs2 & 31) << 20) | ((rs1 & 31) << 15) | ((f3 & 7) << 12) | ((rd & 31) << 7) | (op & 0x7F)


def enc_i(imm, rs1, f3, rd, op):
    return (((imm & 0xFFF) << 20) | ((rs1 & 31) << 15) | ((f3 & 7) << 12) | ((rd & 31) << 7) | (op & 0x7F))


def enc_s(imm, rs2, rs1, f3, op):
    imm &= 0xFFF
    return (((imm >> 5) & 0x7F) << 25) | ((rs2 & 31) << 20) | ((rs1 & 31) << 15) | ((f3 & 7) << 12) | ((imm & 0x1F) << 7) | (op & 0x7F)


def enc_b(imm, rs2, rs1, f3, op):
    assert imm % 2 == 0
    imm &= 0x1FFF
    b12 = (imm >> 12) & 1
    b11 = (imm >> 11) & 1
    b10_5 = (imm >> 5) & 0x3F
    b4_1 = (imm >> 1) & 0xF
    return (b12 << 31) | (b10_5 << 25) | ((rs2 & 31) << 20) | ((rs1 & 31) << 15) | ((f3 & 7) << 12) | (b4_1 << 8) | (b11 << 7) | (op & 0x7F)


def enc_u(imm20, rd, op):
    return (((imm20 & 0xFFFFF) << 12) | ((rd & 31) << 7) | (op & 0x7F))


def enc_j(imm, rd, op):
    assert imm % 2 == 0
    imm &= 0x1FFFFF
    b20 = (imm >> 20) & 1
    b19_12 = (imm >> 12) & 0xFF
    b11 = (imm >> 11) & 1
    b10_1 = (imm >> 1) & 0x3FF
    return (b20 << 31) | (b19_12 << 12) | (b11 << 20) | (b10_1 << 21) | ((rd & 31) << 7) | (op & 0x7F)


# Convenience mnemonics used by tests
def ADD(rd, rs1, rs2):
    return enc_r(0x00, rs2, rs1, 0x0, rd, 0x33)


def SUB(rd, rs1, rs2):
    return enc_r(0x20, rs2, rs1, 0x0, rd, 0x33)


def ADDI(rd, rs1, imm):
    return enc_i(imm, rs1, 0x0, rd, 0x13)


def LW(rd, rs1, imm):
    return enc_i(imm, rs1, 0x2, rd, 0x03)


def SW(rs2, rs1, imm):
    return enc_s(imm, rs2, rs1, 0x2, 0x23)


def BEQ(rs1, rs2, imm):
    return enc_b(imm, rs2, rs1, 0x0, 0x63)


def BNE(rs1, rs2, imm):
    return enc_b(imm, rs2, rs1, 0x1, 0x63)


def JAL(rd, imm):
    return enc_j(imm, rd, 0x6F)


def JALR(rd, rs1, imm):
    return enc_i(imm, rs1, 0x0, rd, 0x67)


def LUI(rd, imm20):
    return enc_u(imm20, rd, 0x37)


EBREAK = 0x00100073
NOP = ADDI(0, 0, 0)
RET = JALR(0, 1, 0)
