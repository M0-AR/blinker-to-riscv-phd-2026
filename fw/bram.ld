/* bram.ld — link bare-metal programs into 6 KiB IceStick BRAM.
 * Layout: code+data from 0x0000, stack grows down from 0x1800.
 * ENTRY _start + KEEP .text.init first guarantees the reset vector lands
 * at address 0 (verified by sim/check_fw.py: ENTRY/KEEP/sp/io symbols).
 */
OUTPUT_ARCH("riscv")
ENTRY(_start)

MEMORY
{
    BRAM (RWX) : ORIGIN = 0x0000, LENGTH = 0x1800  /* 6 KiB */
}

SECTIONS
{
    .text :
    {
        . = ALIGN(4);
        KEEP(*(.text.init))   /* start.S _start first = reset vector */
        *(.text .text.*)
        *(.rodata .rodata.*)
    } >BRAM

    .data :
    {
        . = ALIGN(4);
        *(.data .data.* .sdata .sdata.*)
    } >BRAM

    .bss (NOLOAD) :
    {
        . = ALIGN(4);
        *(.bss .bss.* .sbss .sbss.* *(COMMON))
    } >BRAM

    /* Stack lives at the top of BRAM and grows down; keep 1 KiB clear. */
    stack_top = ORIGIN(BRAM) + LENGTH(BRAM);  /* = 0x1800 */
    io_base_addr = 0x400000;  /* IO page: LEDs bit0, UART_DAT bit1, UART_CNTL bit2 */
    ASSERT(. <= stack_top - 0x400, "overflowed 6 KiB BRAM: program too large for IceStick");
}
