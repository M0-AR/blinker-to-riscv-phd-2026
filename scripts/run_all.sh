#!/bin/bash
# Zero-to-hero verification: every claim below is executed, in order.
set -e
cd "$(dirname "$0")/.."
echo "== [1/8] golden model (26 directed ISA tests) =="
python3 sim/test_golden_model.py
echo "== [2/8] RTL structural checks (clean-room, no external copy) =="
python3 sim/check_rtl.py
echo "== [3/8] decode edge proof (FENCE/JAL disambiguation) =="
python3 sim/test_decode_edge.py
echo "== [4/8] SoC memory-lane proof (byte-masked writes) =="
python3 sim/test_soc_mem.py
echo "== [5/8] firmware hex generation + back-verification =="
python3 fw/generate_hex.py
echo "== [6/8] firmware + boards contract =="
python3 sim/check_fw_boards.py
echo "== [7/8] benchmarks (ISA coverage, CPI, LUT, live traces) =="
python3 bench/bench.py > bench/results.json
echo "== [8/8] docs gate (README + preview.html + Pages copy) =="
python3 sim/check_docs.py
echo "== [audit] zero-to-hero audit (must report 0 issues) =="
python3 sim/audit_zero_to_hero.py
echo "ALL GREEN — see bench/results.json + docs/"
