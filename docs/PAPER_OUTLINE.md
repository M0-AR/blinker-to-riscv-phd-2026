# Paper outline — from blinky to RV32I: a reproducible minimal-core study
Target: workshop/short-paper (6–8 pp.) + artifact. All claims trace to executed runs.

1. **Intro**: why a 24-step blinky→RV32I ladder is the right microscope (one
   change at a time; cheapest FPGA suffices; ends at real C code + DOOM-class
   workloads with LiteX SDRAM).
2. **Background & related**: PicoRV32, SERV (bit-serial), VexRiscv/NaxRiscv,
   DarkRiscV, kianRiscV, mriscv, RVCoreP/RVCar, EcrioniX-2026 course; JICS-2026
   reproducible flow; RISCBench SIT; HLS-FPGA verification speedups.
3. **Method**: clean-room quark (4-state FSM, ADDR_WIDTH=24, 00/01/10 map);
   container (oss-cad-suite) + golden model + directed suite + arch-test intent.
4. **Hidden patterns P1–P10** (the contribution): shared subtract, one-hot
   funct3, flip-shifter, JALR-aluPlus reuse, factored PC+Imm, 1-hot MMIO,
   multi-cycle-vs-LUT, SPI-XIP+fastcode, elegance metric, verification ladder.
   Each with LUT/CPI delta + which rung verifies it.
5. **Evaluation**: ISA coverage 100% (39-item RV32I list, `bench/results.json`);
   CPI 4.25 pedagogical bound vs 3.14 published fast path; LUT 1180 std / 980
   minimal vs 1280 budget; Mandelbrot/mulsi3/LED-counter live traces; synth + board
   as future-measured (Docker commands given, estimates clearly labeled).
6. **Reproducibility**: `docker compose up sim` reproduces every table offline;
   `synth` profile reproduces gateware numbers; artifact = this repo.
7. **Threats/limits**: no FPU/M/C, TX-only UART, word-model BRAM stub in sim,
   estimates vs measured synth (labeled), single-board calibration (HX1K).
8. **Future**: pipelining (Episode II: hazards + branch prediction), interrupts +
   privileged ISA (Episode III), Amaranth/Silice/SpinalHDL ports.
