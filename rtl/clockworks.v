// clockworks.v — clean-room gearbox + reset synchronizer.
// Covers tutorial Steps 2 + 13 (SLOW parameter) from first principles.
// concensus from research: divide by 2^(SLOW+1) via counter MSB; resetn
// is active-low internal reset, asserted synchronously for RPOR-like behavior.
// SPDX-License-Identifier: MIT
`default_nettype none

module clockworks #(
    parameter SLOW = 21,   // divide CLK by 2^(SLOW+1); omit param for full speed
    parameter HAS_SLOW = 1 // 1 = gearbox enabled, 0 = direct passthrough
) (
    input  wire CLK,
    input  wire RESET,  // board-level reset (active high push / finger-pin)
    output wire clk,    // design clock
    output wire resetn  // design reset, active low
);
    generate
        if (HAS_SLOW) begin : g_slow
            reg [SLOW:0] slow_cnt = 0;
            always @(posedge CLK) begin
                slow_cnt <= slow_cnt + 1'b1;
            end
            assign clk = slow_cnt[SLOW];
        end else begin : g_fast
            assign clk = CLK;
        end
    endgenerate

    // Simple synchronous reset stretcher: hold resetn low for 16 design
    // clocks after board RESET deasserts, so BRAM/register init settles.
    reg [3:0] rst_cnt = 4'hF;
    reg       rstn_q  = 1'b0;
    always @(posedge clk) begin
        if (RESET) begin
            rst_cnt <= 4'hF;
            rstn_q  <= 1'b0;
        end else if (rst_cnt != 0) begin
            rst_cnt <= rst_cnt - 1'b1;
            rstn_q  <= 1'b0;
        end else begin
            rstn_q <= 1'b1;
        end
    end
    assign resetn = rstn_q;
endmodule
