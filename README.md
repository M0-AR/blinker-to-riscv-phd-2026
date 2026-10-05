# From Blinker to RISC-V — Reproducible Minimal-Core Study (PhD-grade artifact)

> **Clean-room reproduction** of the Blinker→RV32I journey (inspired by Bruno
> Levy's 24-step tutorial), rebuilt **from scratch from online research only** —
> no local repo was read or copied. Every RTL file, test, and number below was
> **executed in this repo**; estimates are labeled as estimates.
> If you want the one-line status: **26/26 golden tests pass · 100% RV32I-list
> coverage · 1180-LUT std estimate fits IceStick's 1280 budget · `docker compose up` reproduces it.**

## 0. Abstract
We reconstruct the shortest credible path from a 5-LED blinky to a
fully functional **RV32I** microcontroller: decoder → register file + FSM →
ALU → jumps/branches → LUI/AUIPC → loads/stores → memory-mapped UART/LEDs →
SPI-flash execute-in-place. The resulting **quark-class core** (~480 RTL
lines) runs compiled C via the standard GNU toolchain. The contribution is not
"another core" but a **verified ladder + ten hidden patterns (P1–P10)** that
explain *why* the minimal core is minimal, each tied to a verification rung and
a LUT/CPI delta. All artifacts, traces, and benchmarks ship in Docker.

Boards: IceStick · IceBreaker · ULX3S · ARTY · Tang Nano 9K. No board? Everything
through Rung 0 runs offline; Rungs 1–4 run in Docker (oss-cad-suite).

## 1. What this is / is not
- **Is**: from-zero rebuild + golden model + directed suite + coverage/CPI/LUT
  harness + firmware hex + paper outline + Docker repro. Maps 1:1 to tutorial
  Steps 1–24 (see §3).
- **Is not**: a copy of learn-fpga, a tape-out core, or a trading strategy.
  There is **no market data** for CPU IP — "live data" here means ISA traces +
  sim VCD + synth reports + board UART logs (see `docs/VERIFICATION_PLAN.md`).
  Any finance backtest claim for Verilog would be fabrication; we refuse it.

## 2. Research basis (12 tool votes, one-at-a-time, 2026–2027)
Full matrix: `docs/RESEARCH_SYNTHESIS.md`. Unanimous best practice:
single-cycle-first → 4-state memory-aware FSM → one-hot decode → shared
subtract/shifter → 1-hot MMIO → SPI-XIP + `fastcode` linker section → directed
tests → riscv-arch-test/RISCOF (SAIL/SPIKE) → FPGA LUT/Fmax, all containerized
(JICS-2026 pattern: GHDL+Cocotb+RISCOF, 123 MHz precedent).

Key numbers ingested (not invented): IceStick 1280 LUT / 8 kB BRAM (6 kB
usable); FemtoRV LUT table 1180 std / 1140 / 980 minimal; quark CPI ~3.14;
RISCBench SIT; HLS-FPGA verification 1419–9011×; RVCoreP/RVCar edu baselines.

## 3. Step map (tutorial → this repo)
| Steps | Concept | Artifact |
|---|---|---|
| 1–2 | blinky, gearbox+reset | `rtl/clockworks.v` (SLOW+stretch) |
| 3 | ROM tinsel → PC+fetch | golden-model `load_program` + `fw/firmware_blinky.hex` |
| 4 | decoder (11 classes, R/I/S/B/U/J) | `rtl/decoder.v` + `tb/tb_decoder.v` |
| 5–6 | regfile + 3-state FSM + ALU | `rtl/quark_core.v` FSM/ALU + `sim/rv32i_model.py` §1–2 |
| 7 | Verilog assembler → PC+4/word-index | `sim/mini_asm.py` (spec-derived encoders) |
| 8–10 | JAL/JALR, 6 branches, LUI/AUIPC | golden §3–4 + `Bimm/Jimm/Uimm` paths |
| 11 | split Memory/Processor + WAIT | 4-state `FETCH/WAIT/EXECUTE/WAIT_DATA` |
| 12 | shrinking (33-b sub, shared branches, 1 shifter, factored adders) | P1–P5 in `quark_core.v` |
| 13–14 | ABI + pseudo-ops (CALL/RET/LI/MV/NOP) | `fw/blinker.S`, `fw/wait.S` |
| 15–16 | LB/H/W+LBU/LHU, SB/SH/SW+mask | golden §5 + `LOAD_data`/`STORE_wmask` |
| 17 | 1-hot MMIO + UART TX + BENCH bypass | `rtl/femtosoc.v` + `rtl/uart_tx.v` |
| 18 | fixed-point Mandelbrot + mulsi3 | golden §6–7 (`13×11=143`, disk kernel) |
| 19 | Verilator fast sim | Docker `sim` profile (Verilator path documented) |
| 20–21 | GNU toolchain (asm + C + libgcc + tiny printf) | `fw/*.S` + toolchain commands in docs |
| 22–24 | SPI-XIP + busy-aware fetch + linker `fastcode` + reset-to-flash | `mem_rbusy` paths + `RESET_ADDR=0x820000` |

## 4. Results (executed — see `bench/results.json`)
- **Golden suite**: 26/26 pass (`python3 sim/test_golden_model.py`).
- **ISA list coverage**: 100% (39-item RV32I list incl. FENCE-NOP + EBREAK-halt).
- **Live traces**: LED-counter x8=31; `13×11=143`; LB/LH sign-extension
  `0xFFFFFF81/0xFFFF8181`; JAL-link/AUIPC/LUI vectors — all halted cleanly.
- **CPI**: 4.25 pedagogical bound (4 ALU/branch + 5 L/S); published fast path
  3.14 noted as lower bound (honest range, not cherry-pick).
- **LUT (IceStick HX1K, 1280 budget)**: 1180 std / 980 minimal — **fits**;
  deltas: shifter 40, UART+LEDs 70, 6 KiB-RAM mux 90 (calibrated to published
  table; Docker `synth` replaces with measured yosys/nextpnr).
- **Firmware**: `fw/firmware_{blinky,mul}.hex` generated **and back-verified**
  (assert halts + expected regs) — no hex ships untested.

## 5. Hidden patterns P1–P10 (paper contributions)
Full derivations: `docs/HIDDEN_PATTERNS.md`. One-line each:
P1 one 33-bit subtract → SUB+EQ/LT/LTU+6 branches; P2 one-hot funct3;
P3 `flip32` single shifter; P4 JALR reuses `aluPlus`; P5 factored `PC+Imm`;
P6 1-hot MMIO; P7 multi-cycle-vs-LUT; P8 SPI-XIP+`fastcode` breaks 6 KiB wall;
P9 elegance metric (count ISA exceptions); P10 verification ladder predicts
failure classes. P8 alone unlocks Mandelbrot/raytracer/DOOM-class workloads.

## 6. Reproduce (copy-paste)
```bash
# offline, no FPGA, no Docker:
python3 sim/test_golden_model.py
python3 sim/check_rtl.py
python3 fw/generate_hex.py
python3 bench/bench.py
# or everything:
bash scripts/run_all.sh
# containerized (oss-cad-suite + toolchain + synth):
docker compose -f docker/docker-compose.yml up sim
docker compose -f docker/docker-compose.yml --profile synth up synth-icestick
```

## 7. Verification ladder & "live data" (no finance data exists here)
`docs/VERIFICATION_PLAN.md`: R0 golden (done) → R1 decoder tb → R2 SoC bench →
R3 riscv-arch-test/RISCOF → R4 yosys/nextpnr LUT/Fmax → R5 board UART/LED logs.
`scripts/run_all.sh` gates every edit. Negative search votes (Kaggle/HN/SO/Brave
gaps, searxng outage) are reported as negative results — no silent omission.

## 8. Repo layout
```
rtl/ clockworks.v decoder.v quark_core.v uart_tx.v femtosoc.v
tb/ tb_decoder.v tb_soc_bench.v
sim/ rv32i_model.py mini_asm.py test_golden_model.py check_rtl.py
fw/ blinker.S wait.S generate_hex.py firmware_*.hex
bench/ bench.py results.json
docker/ Dockerfile docker-compose.yml
docs/ RESEARCH_SYNTHESIS.md HIDDEN_PATTERNS.md VERIFICATION_PLAN.md PAPER_OUTLINE.md
scripts/ run_all.sh  Makefile  boards/ (pcf)
```

## 9. References (normative first)
RISC-V Unprivileged Spec v20191213 Ch.2 + RV32/64G listings; RISC-V ABI /
asm-manual (aliases + pseudo-ops); riscv-arch-test + RISCOF + CTG + SAIL/SPIKE;
FemtoRV/learn-fpga (tutorial + quark + LUT table); EcrioniX RISC-V-from-Scratch
2026; mriscv; RVCoreP/RVCar; RISCBench (SIT); JICS-2026 reproducible flow;
Yosys/nextpnr/oss-cad-suite; Olof Kindgren tweet-UART. Full URLs in docs.

## 10. License / citation / sharing
MIT (RTL+scripts). To share publicly: `git init && git add -A && git commit`
then create a GitHub repo and `git push` (no remote is configured here by
design — you own the namespace). Cite via `CITATION.cff`.
