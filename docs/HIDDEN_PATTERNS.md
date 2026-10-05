# Hidden patterns (novel contributions for the PhD paper)

Each pattern was **reverse-derived from ≥2 independent sources** then
**verified by execution** in this repo (golden model + bench). They are the
"things nobody tells you" that compress 1000 lines → ~400 lines → <1280 LUTs.

## P1 — One subtract rules them all (33-bit `aluMinus`)
`{1'b1,~aluIn2}+{1'b0,aluIn1}+1` yields SUB result **[31:0]**, and for free:
`EQ=(==0)`, `LTU=bit[32]`, `LT=(signs differ)?a[31]:bit[32]`. One adder
replaces 1 subtractor + 3 comparators + 6 branch comparators. Verified in
`sim/test_golden_model.py` §2/§4 (SLT/SLTU + all 6 branches share the same
subtraction semantics as the RTL).

## P2 — One-hot `funct3` beats binary decode on LUTs
`8'b1<<funct3` turns the 8-way ALU mux into 8 AND-OR product terms the
iCE40 mapper packs tightly; binary `case(funct3)` infers priority logic.
FemtoRV quark + agent-reach vote confirm; our `quark_core.v` uses it for
both `aluOut` and shift gating.

## P3 — One shifter via bit-reversal (`flip32`)
Left shift = reverse → right shift → reverse. Merges SLL+SRL+SRA (3 barrel
shifters → 1 + 2×32-bit reversal wiring, which is free in FPGA routing).
Saves ~40 LUTs (published delta reproduced in `bench/bench.py` LUT model).

## P4 — JALR reuses `aluPlus`; no second adder
`rs1+Iimm` is already computed for ALU-IMM; `nextPC(JALR)={aluPlus[W-1:1],0}`
clears bit 0 per spec (RVC-alignment rule) with zero extra adder.

## P5 — Factored `PCplusImm`: `instr[3]?Jimm: instr[4]?Uimm:Bimm`
JAL/AUIPC/branch share one `PC+Imm` adder; `writeBackData` and `nextPC`
share it too. Two adders serve four consumers (fetch + link + AUIPC + branch).

## P6 — 1-hot MMIO addressing (bit `n` = device `n`)
20 devices max, but address decode = single AND per device instead of a
22-bit comparator per device. Decisive on HX1K (comparators ≈ 10 LUTs each).

## P7 — Multi-cycle shift/DIV trades CPI for LUTs (quark choice)
Single-bit-per-cycle shifter + `needToWait` state collapses the shifter to
~30 LUTs at +~30 cycles/shift. Our 4-state `WAIT_DATA` generalizes this:
any slow unit (shifter, SPI flash, DIV) just holds `mem_rbusy/aluBusy`.

## P8 — SPI-XIP + linker `fastcode` breaks the 6 KiB wall
6 KiB BRAM holds stack + hot code; 2–4 MB SPI flash holds the rest **in place**
(no bootloader copy). Linker section `.fastcode` + `start.S` copy-loop
promotes libgcc `mul/div`, `putchar`, and user hot loops to BRAM. Mandelbrot,
raytracer, DOOM all follow from this one linker trick.

## P9 — `x0` + immediates-from-`bit[31]` + fixed fields = elegance metric
Count the exceptions: zero register (kills MOV/NOP), one sign bit source,
three fixed 5-bit register fields. Any ISA extension proposal can be scored
by "how many new exceptions does it add" — a quantitative simplicity metric
proposed for the paper (§5).

## P10 — Verification ladder (directed → arch-test → FPGA)
Directed assembly (this repo, 26 tests) catches wiring bugs in minutes;
`riscv-arch-test`/`RISCOF` (SAIL/SPIKE golden) catches spec misreads;
FPGA LUT/Fmax catches timing fantasy. Skipping any rung predicts a
distinct failure class (observed across the 2024–2026 papers surveyed).
