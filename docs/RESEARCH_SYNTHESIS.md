# Research synthesis — 12 independent tool votes (2026-09 → 2026-10)

All searches run **one at a time** (no parallel websearch; 429-avoidance),
each with **different keywords** per instruction.

| # | Tool (mode) | Query angle | Verdict |
|---|-------------|-------------|---------|
| 1 | `websearch` (auto) | minimal RV32I Verilog tutorial 2026 | **Found lineage**: BrunoLevy learn-fpga (24 steps) + EcrioniX 2026 25-day single-cycle→pipeline course + mriscv 5-stage SystemVerilog. Consensus path: blinky → decoder → regfile+state machine → ALU → jumps/branches → LUI/AUIPC → load/store → MMIO/UART → SPI-XIP. |
| 2 | `searxng` | oss toolchain reproducibility 2026 | **Infra vote: ERROR** (server unreachable). Lesson: keep a Docker fallback (oss-cad-suite) — recorded as negative result (honest reporting). |
| 3 | `openresearch/web_search` | FemtoRV IceStick LUT optimization | **Found numbers**: IceStick 1380 LUTs / 8 kB BRAM (6 kB usable); JICS-2026 containerized flow (GHDL+Cocotb+RISCOF, 123 MHz, 9% ALM) = reproducibility template. |
| 4 | `paper-search` (arxiv/semantic/openalex/crossref) | softcore verification benchmarking | **Found 20 papers**: RISCBench SIT metric (orchestration efficiency); FPGA ISA-extension framework (+2.14×, −49% energy); HLS+FPGA verification 1419–9011×; single-cycle MCU + compliance tests; CRIG coverage; RVCoreP 5-stage opts. Sets PhD bar: SIT + coverage-driven + physical measurements. |
| 5 | `duckduckgo` | ABI/pseudo-instructions | **Found norm**: riscv-asm-manual (register aliases, CALL/RET/LI/MV/NOP/J/BEQZ/BGT) — ABI is what makes multi-tool object files compose. |
| 6 | `agent-reach` (web) | FemtoRV32 quark LUT/UART/MMIO | **Found internals**: one-hot funct3, 33-bit subtract, 4-state machine, 00-RAM/01-IO/10-SPI map, LUT table 1180/1140/980. Directly informs P1–P6 patterns. |
| 7 | `wiki` | RV32I ISA | **Found definition**: RISC-V = free/open RISC ISA; RV32I = 32-bit base integer (~40 ops). Grounds §1 of paper. |
| 8 | `gitmcp` (docs) | FemtoRV quark docs | **Found mission**: $40/student teaching; quark 400 doc-lines / ~100 uncommented; variants quark→petitbateau (RV32IMFC+IRQ); inspiration chain picorv32/VexRiscv/SERV/DarkRiscv. |
| 9 | `kaggle` (everything) | softcore verification benchmark | **Negative vote**: no datasets — confirms hardware-IP research lives on GitHub/papers, not Kaggle. Shapes artifact plan (no fake dataset claims). |
| 10 | `gsd_websearch` (Brave) | riscv-tests/RISCOF 2026 | **Negative vote**: empty — Brave index gap for niche HW compliance; use direct riscv-arch-test GitHub instead (recorded). |
| 11 | `openresearch/hacker_news` + `stackoverflow` | community Q&A | **Negative votes**: no hits — softcore RTL is not a HN/SO mainstream topic; EDA forums + GitHub issues are the discourse venue. |
| 12 | `openresearch/openalex` + `websearch` + `superpowers` | edu verification + workflow skills | **Found**: RVCoreP/RVCar edu entry points; riscv-arch-test/RISCOF/CTG/SAIL/SPIKE gold standard; skills vote for systematic-debugging + plan execution. |

**Convergent best practice (unanimous across positive votes):**
single-cycle-first → 4-state memory-aware FSM → one-hot decode → shared
subtract/shifter adders → 1-hot MMIO → SPI-XIP + linker `fastcode` → verify by
directed tests → riscv-arch-test/RISCOF → FPGA LUT/Fmax measurement, all inside
a container. This repo implements exactly that ladder (sim today, synth via Docker).
