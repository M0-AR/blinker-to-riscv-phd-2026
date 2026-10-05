.PHONY: verify sim synth-icestick bench fw clean
verify: sim
sim:
	python3 sim/test_golden_model.py
	python3 sim/check_rtl.py
	python3 fw/generate_hex.py
	python3 bench/bench.py
bench:
	python3 bench/bench.py
fw:
	python3 fw/generate_hex.py
# Requires oss-cad-suite (docker compose --profile synth up) or host yosys/nextpnr
synth-icestick:
	yosys -p "read_verilog rtl/clockworks.v rtl/decoder.v rtl/quark_core.v rtl/uart_tx.v rtl/femtosoc.v; synth_ice40 -top femtosoc -json build.json" || echo "yosys not installed; use docker"
	nextpnr-ice40 --hx1k --package tq144 --json build.json --pcf boards/icestick.pcf --asc soc.asc || echo "nextpnr not installed; use docker"
clean:
	rm -rf build.json soc.asc *.vcd obj_dir
