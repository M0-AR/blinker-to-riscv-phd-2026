# wait.S — delay loop subroutine (clean-room).
# a0 preserved across call per ABI (uses t0 only); returns via ret.
.section .text
.globl wait
wait:
        li t0, 1
        slli t0, t0, 17
.L1:
        addi t0, t0, -1
        bnez t0, .L1
        ret
