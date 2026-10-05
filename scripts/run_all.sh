#!/bin/bash
# Zero-to-hero verification: every claim below is executed, in order.
set -e
cd "$(dirname "$0")/.."
echo "== [1/4] golden model (26 directed ISA tests) =="
python3 sim/test_golden_model.py
echo "== [2/4] RTL structural checks (clean-room, no external copy) =="
python3 sim/check_rtl.py
echo "== [3/4] firmware hex generation + back-verification =="
python3 fw/generate_hex.py
echo "== [4/4] benchmarks (ISA coverage, CPI, LUT, live traces) =="
python3 bench/bench.py > bench/results.json
echo "ALL GREEN — see bench/results.json + docs/"
