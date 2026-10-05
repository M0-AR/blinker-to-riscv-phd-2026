# Verification plan — what "live data" means for CPU IP

> There is **no stock-market / trading data** for an FPGA softcore. Any paper
> claiming backtests on XAUUSD for a Verilog ALU would be fabrication. The live
> ground truth in this domain is: (a) ISA execution traces, (b) simulation VCD,
> (c) synthesis LUT/Fmax reports, (d) on-board UART/LED observations.
> This plan verifies each, with nothing hand-claimed.

## Rung 0 — Golden model (done, offline, no FPGA needed)
`python3 sim/test_golden_model.py` → **26/26 pass** (R-type, shifts, compares,
JAL/JALR, LUI/AUIPC, 6 branches incl. signed/unsigned corners, LB/LH/LW +
LBU/LHU sign/zero extension, SB/SH/SW lanes, x0 hardwire, EBREAK halt,
`mulsi3` shift-add 13×11=143, fixed-point disk kernel).

## Rung 1 — Decoder testbench (needs iverilog — via Docker)
`iverilog -o tb_decoder tb/tb_decoder.v rtl/decoder.v && vvp tb_decoder`
expects `ALL DECODER TESTS PASSED` (ADD/ADDI/LW/SW/BEQ-negative/LUI/JAL/EBREAK).

## Rung 2 — SoC bench (needs iverilog — via Docker)
`iverilog -DBENCH -o sim_soc tb/tb_soc_bench.v rtl/*.v && vvp sim_soc`
expects `EBREAK observed at PC=...` + UART-captured bytes on stdout.

## Rung 3 — ISA compliance (needs riscv-toolchain — via Docker)
Clone `riscv-arch-test`, build with `-march=rv32i -mabi=ilp32`, run RV32I suite
through the golden model (instruction-by-instruction) then through Verilator
(`--top-module femtosoc`). Target: 100% of I-suite (FENCE NOP-documented,
EBREAK halt-documented). SAIL/SPIKE cross-check per RISCOF flow.

## Rung 4 — Synthesis truth (needs yosys/nextpnr — via Docker)
`make synth-icestick` → LUT ≤ 1280, Fmax report, BRAM map (2 kB regfile +
6 kB RAM). Calibrated estimate today: **1180 LUT std / 980 minimal**
(`bench/results.json`); Docker run replaces estimates with measured numbers.

## Rung 5 — Board truth (needs IceStick/ULX3S hardware)
`iceprog soc.bin` + `./terminal.sh` (115200 baud): blinky → hello → mandelbrot.
Record LED video + UART logs as `docs/BOARD_LOG.md` evidence.

## Continuous gate
`scripts/run_all.sh` runs Rungs 0–1 offline; CI runs Rungs 0–4 in Docker on
every push. No file is edited without re-running its rung (repo rule).
