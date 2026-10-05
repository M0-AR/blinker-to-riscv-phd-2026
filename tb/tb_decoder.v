// tb_decoder.v — self-checking testbench for rv32i_decoder.
// Vectors hand-derived from RISC-V spec listings (same source as mini_asm.py).
// Run: iverilog -o tb_decoder tb_decoder.v ../rtl/decoder.v && vvp tb_decoder
`timescale 1ns/1ps
module tb_decoder;
    reg [31:0] instr;
    wire isALUreg, isALUimm, isBranch, isJAL, isJALR, isAUIPC, isLUI, isLoad, isStore, isSYSTEM, isFENCE;
    wire [4:0] rs1Id, rs2Id, rdId;
    wire [2:0] funct3; wire [6:0] funct7;
    wire [31:0] Iimm, Simm, Bimm, Uimm, Jimm;
    integer errors = 0;

    rv32i_decoder dut(.instr(instr), .isALUreg(isALUreg), .isALUimm(isALUimm),
        .isBranch(isBranch), .isJAL(isJAL), .isJALR(isJALR), .isAUIPC(isAUIPC),
        .isLUI(isLUI), .isLoad(isLoad), .isStore(isStore), .isSYSTEM(isSYSTEM),
        .isFENCE(isFENCE), .rs1Id(rs1Id), .rs2Id(rs2Id), .rdId(rdId),
        .funct3(funct3), .funct7(funct7),
        .Iimm(Iimm), .Simm(Simm), .Bimm(Bimm), .Uimm(Uimm), .Jimm(Jimm));

    task check(input ok, input [255:0] name);
        begin
            if (!ok) begin $display("FAIL: %0s instr=%h", name, instr); errors = errors + 1; end
            else $display("ok: %0s", name);
        end
    endtask

    initial begin
        // ADD x1,x0,x0 = 0000000_00000_00000_000_00001_0110011
        instr = 32'b0000000_00000_00000_000_00001_0110011; #1;
        check(isALUreg & rdId==1 & rs1Id==0 & rs2Id==0, "ADD decode");
        // ADDI x1,x1,1
        instr = 32'b000000000001_00001_000_00001_0010011; #1;
        check(isALUimm & $signed(Iimm)==1, "ADDI Iimm=1");
        // LW x2,0(x1)
        instr = 32'b000000000000_00001_010_00010_0000011; #1;
        check(isLoad & rdId==2, "LW decode");
        // SW x2,0(x1)
        instr = 32'b0000000_00010_00001_010_00000_0100011; #1;
        check(isStore & $signed(Simm)==0, "SW Simm=0");
        // BEQ with negative offset -4: imm bits -> Bimm == -4
        instr = {1'b1,6'b111111,5'd2,5'd1,3'b000,4'b1100,1'b1,7'b1100011}; #1;
        check(isBranch & $signed(Bimm)==-4, "BEQ Bimm=-4");
        // LUI x1,0x12345 -> Uimm check
        instr = {20'h12345, 5'd1, 7'b0110111}; #1;
        check(isLUI & Uimm==32'h12345000, "LUI Uimm");
        // JAL x0,+8
        instr = 32'h0080006F; #1;
        check(isJAL & $signed(Jimm)==8, "JAL Jimm=8");
        // EBREAK
        instr = 32'h00100073; #1;
        check(isSYSTEM, "EBREAK SYSTEM");
        if (errors==0) $display("ALL DECODER TESTS PASSED");
        else $display("%0d TEST(S) FAILED", errors);
        $finish;
    end
endmodule
