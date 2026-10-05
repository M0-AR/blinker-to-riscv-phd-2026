# Simple blinker (GNU assembler, RV32I, ilp32, no-relax).
# Clean-room example mirroring tutorial Step 20 intent: gp = IO base,
# loop writes LED patterns then waits. Assembled with:
#   riscv64-unknown-elf-as -march=rv32i -mabi=ilp32 -mno-relax blinker.S -o blinker.o
.equ IO_BASE, 0x400000
.equ IO_LEDS, 4
.section .text
.globl main
main:
        li   gp, IO_BASE
        li   a0, 5
.L0:
        sw   a0, IO_LEDS(gp)
        call wait
        li   a0, 10
        sw   a0, IO_LEDS(gp)
        call wait
        j .L0
