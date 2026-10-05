// uart_tx.v — clean-room 8N1 UART transmitter (TX only).
// Research basis: Olof Kindgren tweet-size UART concept (RS232 over FTDI USB),
// 115200 baud default, BOARD_FREQ_MHZ parameter. Clean-room implementation:
// 10-bit frame {stop=1, data[7:0] LSB-first, start=0}, busy flag for polling
// (tutorial step 17: bit 9 of CNTL word). RX path omitted by design (TX-only
// halves LUTs; sim bench bypasses wire and captures mem_wdata directly).
// SPDX-License-Identifier: MIT
`default_nettype none

module uart_tx #(
    parameter CLK_FREQ_HZ = 12000000,
    parameter BAUD_RATE   = 115200
) (
    input  wire       clk,
    input  wire       resetn,   // active low
    input  wire [7:0] data,
    input  wire       valid,    // 1-cycle strobe to send `data`
    output wire       ready,    // 1 when idle (not busy)
    output wire       tx        // serial line, idle high
);
    localparam DIV = CLK_FREQ_HZ / BAUD_RATE;
    reg [15:0] div_cnt = 0;
    reg [3:0]  bit_cnt = 0;
    reg [9:0]  shift   = 10'b1111111111;
    reg        busy    = 1'b0;

    assign ready = !busy;
    assign tx = shift[0];

    always @(posedge clk) begin
        if (!resetn) begin
            busy <= 1'b0; shift <= 10'b1111111111;
            div_cnt <= 0; bit_cnt <= 0;
        end else if (busy) begin
            if (div_cnt == DIV - 1) begin
                div_cnt <= 0;
                shift <= {1'b1, shift[9:1]};
                if (bit_cnt == 10) begin
                    busy <= 1'b0; bit_cnt <= 0;
                end else begin
                    bit_cnt <= bit_cnt + 1'b1;
                end
            end else begin
                div_cnt <= div_cnt + 1'b1;
            end
        end else if (valid) begin
            shift <= {1'b1, data, 1'b0};
            busy <= 1'b1; bit_cnt <= 0; div_cnt <= 0;
        end
    end
endmodule
