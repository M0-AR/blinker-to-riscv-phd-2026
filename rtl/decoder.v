// decoder.v — clean-room RV32I instruction decoder.
// Normative source: RISC-V Unprivileged Spec v20191213, Ch.2 + RV32/64G listings.
// Research consensus (tutorial step 4, EcrioniX Day 8, FemtoRV quark):
//  - opcode = instr[6:0] (10 classes used; FENCE/SYSTEM minimal)
//  - rd/rs1/rs2 fixed at [11:7]/[19:15]/[24:20] for all formats (elegance pattern #1)
//  - funct3 = [14:12], funct7 = [31:25]; only instr[30] matters for ADD/SUB, SRL/SRA
//  - immediates: I/S/B/U/J with sign extension always from instr[31] (pattern #2)
//  - low two bits of instr are 11 for all RV32I (compressed ext. absent)
// SPDX-License-Identifier: MIT
`default_nettype none

module rv32i_decoder (
    input  wire [31:0] instr,
    output wire        isALUreg,
    output wire        isALUimm,
    output wire        isBranch,
    output wire        isJAL,
    output wire        isJALR,
    output wire        isAUIPC,
    output wire        isLUI,
    output wire        isLoad,
    output wire        isStore,
    output wire        isSYSTEM,
    output wire        isFENCE,
    output wire [4:0]  rs1Id,
    output wire [4:0]  rs2Id,
    output wire [4:0]  rdId,
    output wire [2:0]  funct3,
    output wire [6:0]  funct7,
    output wire [31:0] Iimm,
    output wire [31:0] Simm,
    output wire [31:0] Bimm,
    output wire [31:0] Uimm,
    output wire [31:0] Jimm
);
    assign isLoad   = (instr[6:2] == 5'b00000);
    assign isFENCE  = (instr[6:2] == 5'b00011);
    assign isALUimm = (instr[6:2] == 5'b00100);
    assign isAUIPC  = (instr[6:2] == 5'b00101);
    assign isStore  = (instr[6:2] == 5'b01000);
    assign isALUreg = (instr[6:2] == 5'b01100);
    assign isLUI    = (instr[6:2] == 5'b01101);
    assign isBranch = (instr[6:2] == 5'b11000);
    assign isJALR   = (instr[6:2] == 5'b11001);
    assign isJAL    =  instr[3]; // 11011; single-bit test (FemtoRV trick)
    assign isSYSTEM = (instr[6:2] == 5'b11100);

    assign rs1Id  = instr[19:15];
    assign rs2Id  = instr[24:20];
    assign rdId   = instr[11:7];
    assign funct3 = instr[14:12];
    assign funct7 = instr[31:25];

    assign Uimm = {instr[31], instr[30:12], {12{1'b0}}};
    assign Iimm = {{21{instr[31]}}, instr[30:20]};
    assign Simm = {{21{instr[31]}}, instr[30:25], instr[11:7]};
    assign Bimm = {{20{instr[31]}}, instr[7], instr[30:25], instr[11:8], 1'b0};
    assign Jimm = {{12{instr[31]}}, instr[19:12], instr[20], instr[30:21], 1'b0};
endmodule
