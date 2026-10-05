// tb_soc_bench.v — minimal SoC bench: drives clocks, observes LEDS/UART bypass.
// Run (oss-cad-suite): iverilog -DBENCH -o sim tb_soc_bench.v ../rtl/*.v && vvp sim
`timescale 1ns/1ps
module tb_soc_bench;
    reg CLK = 0, RESET = 1;
    wire [4:0] LEDS; wire RXD = 1'b1, TXD;
    always #5 CLK = ~CLK;
    femtosoc dut(.CLK(CLK), .RESET(RESET), .LEDS(LEDS), .RXD(RXD), .TXD(TXD));
    initial begin
        $dumpfile("tb_soc.vcd"); $dumpvars(0, tb_soc_bench);
        #100 RESET = 0;
        #200000 $display("TIMEOUT LEDs=%b (no EBREAK trap in minimal bench)", LEDS);
        $finish;
    end
    // EBREAK trap: quark halts PC on SYSTEM; surface it here
    always @(posedge CLK) begin
        if (dut.CPU.isSYSTEM && dut.CPU.state_EXECUTE) begin
            $display("EBREAK observed at PC=%h LEDs=%b", dut.CPU.PC, LEDS);
            $finish;
        end
    end
endmodule
