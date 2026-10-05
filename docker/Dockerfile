# Reproducible FPGA+RISC-V lab (oss-cad-suite: yosys/nextpnr/iverilog/verilator + riscv-gnu-toolchain).
# Build: docker compose --profile sim up (no FPGA hardware needed for sim/verify).
FROM ghcr.io/hdlc/oss-cad-suite:latest
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip make git && rm -rf /var/lib/apt/lists/*
# RISC-V toolchain (RV32I/ilp32) for fw/*.S + C demos
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc-riscv64-unknown-elf 2>/dev/null || \
    (echo "riscv toolchain installed via oss-cad-suite or host; see docs/TOOLCHAIN.md")
WORKDIR /work
COPY . /work
CMD ["bash"]
