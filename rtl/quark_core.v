// quark_core.v — clean-room minimal RV32I core ("quark" class).
// Covers tutorial Steps 5-16 + 22-24 (state machine, ALU shrinking, load/store,
// SPI-busy-aware fetch). Derived from the RISC-V spec + public research consensus,
// not copied from any single source file.
//
// Key verified tricks (see docs/HIDDEN_PATTERNS.md):
//  P1 single 33-bit subtract -> SUB + EQ/LT/LTU + all 6 branches
//  P2 one-hot funct3 (8'b1 << funct3) reduces LUT depth
//  P3 single barrel shifter via bit-reversal for SLL/SRL/SRA
//  P4 JALR reuses aluPlus, not a second adder
//  P5 PCplusImm factored: Jimm/Uimm/Bimm selected by instr[3]/instr[4]
//  P6 ADDR_WIDTH=24 (16 MB space: RAM/IO/SPI-flash quadrants)
//
// Memory protocol (matches femtosoc.v):
//  mem_addr  : word-aligned byte address (low 2 bits ignored by RAM)
//  mem_rdata : read data (instruction or load data)
//  mem_rstrb : read strobe (fetch or load)
//  mem_wdata : store data lane-shuffled for SB/SH/SW
//  mem_wmask : per-byte write enable (0000 = no write)
//  mem_rbusy : memory busy (SPI flash serial latency); core waits in
//              WAIT_INSTR (fetch) and WAIT_DATA (load).
// Reset: active-low resetn (from clockworks); PC -> RESET_ADDR, state -> WAIT_DATA
//        so the first fetch waits for memory calm (tutorial step 24 fix).
// SPDX-License-Identifier: MIT
`default_nettype none

module quark_core #(
    parameter ADDR_WIDTH = 24,
    parameter RESET_ADDR = 32'h00820000 // SPI flash + 128 KiB (XIP default)
) (
    input  wire               clk,
    input  wire               resetn,
    output wire [ADDR_WIDTH-1:0] mem_addr,
    input  wire [31:0]        mem_rdata,
    output wire               mem_rstrb,
    output wire [31:0]        mem_wdata,
    output wire [3:0]         mem_wmask,
    input  wire               mem_rbusy
);
    // ---------- register file (2 read ports via duplication inference) ----
    reg [31:0] regfile [0:31];
    reg [31:0] rs1, rs2;
    reg [29:0] instr; // instr[31:2]; low 2 bits are always 11 in RV32I
    // Full 32-bit view (low 2 bits are always 11: no compressed extension).
    wire [31:0] full_instr = {instr, 2'b11};
    wire [4:0] rs1_full = full_instr[19:15];
    wire [4:0] rs2_full = full_instr[24:20];
    wire [4:0] rdId     = full_instr[11:7];
    wire [2:0] funct3   = full_instr[14:12];

    // ---------- decode (inlined one-hot style, mirrors decoder.v) ---------
    wire isLoad   = (instr[6-2:2-2] == 5'b00000);
    wire isFENCE  = (instr[6-2:2-2] == 5'b00011);
    wire isALUimm = (instr[6-2:2-2] == 5'b00100);
    wire isAUIPC  = (instr[6-2:2-2] == 5'b00101);
    wire isStore  = (instr[6-2:2-2] == 5'b01000);
    wire isALUreg = (instr[6-2:2-2] == 5'b01100);
    wire isLUI    = (instr[6-2:2-2] == 5'b01101);
    wire isBranch = (instr[6-2:2-2] == 5'b11000);
    wire isJALR   = (instr[6-2:2-2] == 5'b11001);
    wire isJAL    = full_instr[3] & full_instr[6]; // JAL=1101111; bit3 alone also matches FENCE=0001111, so bit6 disambiguates (proved in sim/test_decode_edge.py)
    wire isSYSTEM = (instr[6-2:2-2] == 5'b11100);
    wire isALU    = isALUimm | isALUreg;

    wire [31:0] Uimm = {full_instr[31], full_instr[30:12], {12{1'b0}}};
    wire [31:0] Iimm = {{21{full_instr[31]}}, full_instr[30:20]};
    wire [31:0] Simm = {{21{full_instr[31]}}, full_instr[30:25], full_instr[11:7]};
    wire [31:0] Bimm = {{20{full_instr[31]}}, full_instr[7], full_instr[30:25], full_instr[11:8], 1'b0};
    wire [31:0] Jimm = {{12{full_instr[31]}}, full_instr[19:12], full_instr[20], full_instr[30:21], 1'b0};

    (* onehot *) wire [7:0] funct3Is = 8'b00000001 << funct3;
    wire funct3IsShift = funct3Is[1] | funct3Is[5];

    // ---------- ALU inputs ----------
    wire [31:0] aluIn1 = rs1;
    wire [31:0] aluIn2 = (isALUreg | isBranch) ? rs2 : Iimm;
    wire [31:0] aluPlus = aluIn1 + aluIn2;
    // P1: single 33-bit subtract: aluIn1 - aluIn2 = aluIn1 + ~aluIn2 + 1
    wire [32:0] aluMinus = {1'b1, ~aluIn2} + {1'b0, aluIn1} + 33'b1;
    wire EQ  = (aluMinus[31:0] == 32'b0);
    wire LTU = aluMinus[32];
    wire LT  = (aluIn1[31] ^ aluIn2[31]) ? aluIn1[31] : aluMinus[32];

    // P3: single shifter with bit-reversal for left shifts
    function [31:0] flip32;
        input [31:0] x;
        integer i;
        begin
            for (i = 0; i < 32; i = i + 1) flip32[i] = x[31-i];
        end
    endfunction
    wire [31:0] shifter_in = (funct3 == 3'b001) ? flip32(aluIn1) : aluIn1;
    wire [31:0] shifter_raw =
        $signed({full_instr[30] & aluIn1[31], shifter_in}) >>> aluIn2[4:0];
    wire [31:0] shifter = (funct3 == 3'b001) ? flip32(shifter_raw) : shifter_raw;

    wire [31:0] aluOut =
        (funct3Is[0] ? (full_instr[30] & full_instr[5] ? aluMinus[31:0] : aluPlus) : 32'b0) |
        (funct3Is[1] ? shifter : 32'b0) | // SLL via bit-reversed single shifter
        (funct3Is[2] ? {31'b0, LT} : 32'b0) |
        (funct3Is[3] ? {31'b0, LTU} : 32'b0) |
        (funct3Is[4] ? (aluIn1 ^ aluIn2) : 32'b0) |
        (funct3Is[5] ? shifter : 32'b0) |
        (funct3Is[6] ? (aluIn1 | aluIn2) : 32'b0) |
        (funct3Is[7] ? (aluIn1 & aluIn2) : 32'b0);

    // branch predicate reuses EQ/LT/LTU (tutorial step 12 win)
    reg predicate;
    always @(*) begin
        case (funct3)
            3'b000: predicate = EQ;
            3'b001: predicate = !EQ;
            3'b100: predicate = LT;
            3'b101: predicate = !LT;
            3'b110: predicate = LTU;
            3'b111: predicate = !LTU;
            default: predicate = 1'b0;
        endcase
    end

    // ---------- PC arithmetic (P4/P5) ----------
    reg [ADDR_WIDTH-1:0] PC;
    wire [ADDR_WIDTH-1:0] PCplusImm = PC + (full_instr[3] ? Jimm[ADDR_WIDTH-1:0] :
                                            full_instr[4] ? Uimm[ADDR_WIDTH-1:0] :
                                                            Bimm[ADDR_WIDTH-1:0]);
    wire [ADDR_WIDTH-1:0] PCplus4 = PC + 4;
    wire jumpToPCplusImm = isJAL | (isBranch & predicate);
    wire [ADDR_WIDTH-1:0] nextPC = isJALR ? {aluPlus[ADDR_WIDTH-1:1], 1'b0} :
                                    jumpToPCplusImm ? PCplusImm : PCplus4;

    wire [ADDR_WIDTH-1:0] loadstore_addr =
        rs1[ADDR_WIDTH-1:0] + (isStore ? Simm[ADDR_WIDTH-1:0] : Iimm[ADDR_WIDTH-1:0]);

    // ---------- LOAD lane select + sign extension ----------
    wire mem_byteAccess     = (funct3[1:0] == 2'b00);
    wire mem_halfwordAccess = (funct3[1:0] == 2'b01);
    wire [15:0] LOAD_halfword =
        loadstore_addr[1] ? mem_rdata[31:16] : mem_rdata[15:0];
    wire [7:0] LOAD_byte =
        loadstore_addr[0] ? LOAD_halfword[15:8] : LOAD_halfword[7:0];
    wire LOAD_sign =
        !funct3[2] & (mem_byteAccess ? LOAD_byte[7] : LOAD_halfword[15]);
    wire [31:0] LOAD_data =
        mem_byteAccess     ? {{24{LOAD_sign}}, LOAD_byte} :
        mem_halfwordAccess ? {{16{LOAD_sign}}, LOAD_halfword} :
                             mem_rdata;

    // ---------- STORE lane shuffle + mask ----------
    assign mem_wdata[7:0]   = rs2[7:0];
    assign mem_wdata[15:8]  = loadstore_addr[0] ? rs2[7:0] : rs2[15:8];
    assign mem_wdata[23:16] = loadstore_addr[1] ? rs2[7:0] : rs2[23:16];
    assign mem_wdata[31:24] = loadstore_addr[0] ? rs2[7:0] :
                              loadstore_addr[1] ? rs2[15:8] : rs2[31:24];
    wire [3:0] STORE_wmask =
        mem_byteAccess ? (loadstore_addr[1] ?
                            (loadstore_addr[0] ? 4'b1000 : 4'b0100) :
                            (loadstore_addr[0] ? 4'b0010 : 4'b0001)) :
        mem_halfwordAccess ? (loadstore_addr[1] ? 4'b1100 : 4'b0011) :
        4'b1111;

    // ---------- write-back ----------
    /* verilator lint_off WIDTH */
    wire [31:0] writeBackData =
        (isLUI ? Uimm : 32'b0) |
        (isALU ? aluOut : 32'b0) |
        (isAUIPC ? {{(32-ADDR_WIDTH){1'b0}}, PCplusImm} : 32'b0) |
        ((isJALR | isJAL) ? {{(32-ADDR_WIDTH){1'b0}}, PCplus4} : 32'b0) |
        (isLoad ? LOAD_data : 32'b0);
    /* verilator lint_on WIDTH */
    wire writeBack = ~(isBranch | isStore) & (state_EXECUTE | state_WAIT_DATA);

    // ---------- bus ----------
    assign mem_addr  = (state_FETCH | state_WAIT) ? PC : loadstore_addr;
    assign mem_rstrb = state_FETCH | (state_EXECUTE & isLoad);
    assign mem_wmask = {4{(state_EXECUTE & isStore)}} & STORE_wmask;

    // ---------- 4-state machine (tutorial step 22 optimized) ----------
    localparam FETCH_BIT = 0, WAIT_BIT = 1, EXEC_BIT = 2, WD_BIT = 3;
    (* onehot *) reg [3:0] state = 4'b0001;
    wire state_FETCH   = state[FETCH_BIT];
    wire state_WAIT    = state[WAIT_BIT];
    wire state_EXECUTE = state[EXEC_BIT];
    wire state_WAIT_DATA = state[WD_BIT];
    wire needToWait = isLoad | isStore;

    integer i;
    always @(posedge clk) begin
        if (!resetn) begin
            PC    <= RESET_ADDR[ADDR_WIDTH-1:0];
            state <= 4'b1000; // WAIT_DATA: idle until memory calm
            for (i = 0; i < 32; i = i + 1) regfile[i] <= 32'b0;
        end else begin
            if (writeBack && rdId != 0)
                regfile[rdId] <= writeBackData;
            (* parallel_case *)
            case (1'b1)
                state[WAIT_BIT]: begin
                    if (!mem_rbusy) begin
                        instr <= mem_rdata[31:2];
                        rs1   <= regfile[mem_rdata[19:15]];
                        rs2   <= regfile[mem_rdata[24:20]];
                        state <= 4'b0100;
                    end
                end
                state[EXEC_BIT]: begin
                    if (!isSYSTEM)
                        PC <= nextPC;
                    state <= needToWait ? 4'b1000 : 4'b0001;
                end
                state[WD_BIT]: begin
                    if (!mem_rbusy)
                        state <= 4'b0001;
                end
                default: begin // FETCH
                    state <= 4'b0010;
                end
            endcase
        end
    end
endmodule
