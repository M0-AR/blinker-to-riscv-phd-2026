# start.S — reset entry: stack + IO pointer, then C/assembly main.
# Clean-room, follows the universal bare-metal pattern (ENTRY section first
# via KEEP in bram.ld, sp from stack_top symbol, gp = IO page, call main).
# Assembled with: riscv64-unknown-elf-as -march=rv32i -mabi=ilp32 -mno-relax
.section .text.init, "ax"
.globl _start
.type _start, @function
_start:
.option push
.option norelax
        la gp, io_base_addr   # IO page (0x400000), kept in gp by convention
.option pop
        la sp, stack_top     # linker-provided top of 6 KiB BRAM
        call main
        ebreak                # halt if main ever returns
