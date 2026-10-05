// femtosoc.v — clean-room minimal SoC: quark core + BRAM + 1-hot MMIO + UART.
// Memory map (24-bit, tutorial steps 17+22 consensus):
//   mem_addr[23:22] = 2'b00 -> RAM   (0x000000, 6 KiB default)
//   mem_addr[23:22] = 2'b01 -> IO page (0x400000, 1-hot word addressing)
//   mem_addr[23:22] = 2'b10 -> SPI flash XIP (0x800000, busy-aware)
// IO word bits: 0 = LEDS (W), 1 = UART_DAT (W), 2 = UART_CNTL (R, bit9=busy).
// 1-hot addressing: device n selected by mem_wordaddr[n] (no wide comparators,
// Matthias Koch trick — saves LUTs on iCE40HX1K).
// SPDX-License-Identifier: MIT
`default_nettype none

module femtosoc #(
    parameter RAM_WORDS = 1536,       // 1536 x 32b = 6 KiB
    parameter CLK_FREQ_HZ = 12000000
) (
    input  wire       CLK,
    input  wire       RESET,
    output reg  [4:0] LEDS,
    input  wire       RXD,  // unused (TX-only UART in minimal config)
    output wire       TXD
);
    wire clk, resetn;
    clockworks #(.SLOW(21)) CW (.CLK(CLK), .RESET(RESET), .clk(clk), .resetn(resetn));

    wire [23:0] mem_addr;
    wire [31:0] mem_rdata, mem_wdata;
    wire [3:0]  mem_wmask;
    wire        mem_rstrb, mem_rbusy;

    wire [31:0] ram_rdata;
    wire [29:0] mem_wordaddr = {6'b0, mem_addr[23:2]}; // 24b byte -> word
    wire isRAM = (mem_addr[23:22] == 2'b00);
    wire isIO  = (mem_addr[23:22] == 2'b01);
    wire isSPI = (mem_addr[23:22] == 2'b10);
    wire mem_wstrb = |mem_wmask;

    // ---- BRAM (6 KiB) with per-byte masked write (maps to iCE40 SB_RAM) ----
    reg [31:0] RAM [0:RAM_WORDS-1];
    reg [31:0] ram_q;
    wire [31:0] ram_idx = mem_addr[23:2]; // word index; synthesis trims to RAM_WORDS
    always @(posedge clk) begin
        if (isRAM) begin
            // Per-byte masked write: SB/SH/SW all safe (maps to SB_RAM40_4K
            // masked-write primitive; semantics proved in sim/test_soc_mem.py).
            if (mem_wmask[0]) RAM[ram_idx][ 7:0 ] <= mem_wdata[ 7:0 ];
            if (mem_wmask[1]) RAM[ram_idx][15:8 ] <= mem_wdata[15:8 ];
            if (mem_wmask[2]) RAM[ram_idx][23:16] <= mem_wdata[23:16];
            if (mem_wmask[3]) RAM[ram_idx][31:24] <= mem_wdata[31:24];
            ram_q <= RAM[ram_idx];
        end
    end
    assign ram_rdata = ram_q;

    // ---- IO: LEDs + UART ----
    localparam IO_LEDS_bit = 0;
    localparam IO_UART_DAT_bit = 1;
    localparam IO_UART_CNTL_bit = 2;
    wire uart_valid = isIO & mem_wstrb & mem_wordaddr[IO_UART_DAT_bit];
    wire uart_ready;
    uart_tx #(.CLK_FREQ_HZ(CLK_FREQ_HZ)) UART (
        .clk(clk), .resetn(resetn),
        .data(mem_wdata[7:0]), .valid(uart_valid),
        .ready(uart_ready), .tx(TXD)
    );
    wire [31:0] io_rdata =
        (mem_wordaddr[IO_UART_CNTL_bit] ? {22'b0, !uart_ready, 9'b0} : 32'b0);

    always @(posedge clk) begin
        if (!resetn) LEDS <= 5'b0;
        else if (isIO & mem_wstrb & mem_wordaddr[IO_LEDS_bit]) LEDS <= mem_wdata[4:0];
    end

    // ---- SPI flash XIP stub: busy for 8 cycles, then returns header word ----
    reg [3:0] spi_cnt = 0;
    reg spi_busy = 1'b0;
    always @(posedge clk) begin
        if (!resetn) begin spi_busy <= 1'b0; spi_cnt <= 0; end
        else if (isSPI & mem_rstrb & !spi_busy) begin spi_busy <= 1'b1; spi_cnt <= 8; end
        else if (spi_busy) begin
            if (spi_cnt == 0) spi_busy <= 1'b0;
            else spi_cnt <= spi_cnt - 1'b1;
        end
    end

    assign mem_rbusy = isSPI & spi_busy;
    assign mem_rdata = isRAM ? ram_rdata :
                       isSPI ? 32'h00100073 : // EBREAK (safe halt if XIP empty)
                       io_rdata;

    quark_core #(.ADDR_WIDTH(24)) CPU (
        .clk(clk), .resetn(resetn),
        .mem_addr(mem_addr), .mem_rdata(mem_rdata),
        .mem_rstrb(mem_rstrb), .mem_wdata(mem_wdata),
        .mem_wmask(mem_wmask), .mem_rbusy(mem_rbusy)
    );

`ifdef BENCH
    // Simulation bypass: capture UART bytes to stdout (tutorial step 17 trick).
    always @(posedge clk) begin
        if (uart_valid) begin
            $write("%c", mem_wdata[7:0]);
            $fflush(32'h8000_0001);
        end
    end
`endif
endmodule
