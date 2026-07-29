#!/usr/bin/env python3
"""v1.4 验证器 — (1) 解码指令核对 Verilog 编码 (2) 功能执行核对 Σ/MUL/DIV"""

# ── 编码定义 (必须与 Verilog localparam 完全一致) ──
OP_NOP=0; OP_PUSH=1; OP_MOV=2; OP_ADD=3; OP_SUB=4; OP_MUL=5
OP_AND=6; OP_OR=7; OP_XOR=8; OP_SHL=9; OP_SHR=10; OP_CMP=11
OP_DIV=12; OP_STORE=16; OP_LOAD=17; OP_ADDI=19; OP_SUBI=20
OP_JAL=21; OP_JMP=13; OP_JZ=14; OP_JNZ=15
OP_SENSE=36; OP_EMIT=37; OP_CALL=38; OP_RET=39

OP_BY_NAME = {v:k for k,v in list(globals().items()) if k.startswith('OP_')}

def dec(instr):
    op = (instr >> 26) & 0x3F
    rd = (instr >> 22) & 0xF
    rs1 = (instr >> 18) & 0xF
    rs2 = (instr >> 14) & 0xF
    imm_raw = instr & 0x3FFF
    # sign extend from 14 bits
    if imm_raw & 0x2000:
        imm = imm_raw - 0x4000
    else:
        imm = imm_raw
    return op, rd, rs1, rs2, imm

def enc(op, rd, rs1, rs2, imm):
    imm_u = imm & 0x3FFF
    return ((op & 0x3F) << 26) | ((rd & 0xF) << 22) | ((rs1 & 0xF) << 18) | ((rs2 & 0xF) << 14) | imm_u

# ── 功能执行器 ──
def run(hexfile):
    imem = []
    with open(hexfile) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            v = int(line, 16)
            lo = v & 0xFFFFFFFF
            hi = (v >> 32) & 0xFFFFFFFF
            imem.append(lo)
            imem.append(hi)

    rf = [0]*32; rf[0] = 0  # r0 always 0
    dmem = {}
    pc = 0
    cyc = 0
    max_cyc = 100000

    while cyc < max_cyc:
        cyc += 1
        idx = pc // 4
        if idx < 0 or idx >= len(imem):
            print(f"  pc={pc} out of range")
            return dmem.get(0, None), cyc
        instr = imem[idx]
        op, rd, rs1, rs2, imm = dec(instr)

        if op == OP_NOP:
            pc += 4
        elif op == OP_PUSH:
            rf[rd] = imm & 0xFFFFFFFF
            pc += 4
        elif op == OP_MOV:
            rf[rd] = rf[rs1]
            pc += 4
        elif op == OP_ADD:
            rf[rd] = (rf[rs1] + rf[rs2]) & 0xFFFFFFFF
            pc += 4
        elif op == OP_SUB:
            rf[rd] = (rf[rs1] - rf[rs2]) & 0xFFFFFFFF
            pc += 4
        elif op == OP_MUL:
            rf[rd] = (rf[rs1] * rf[rs2]) & 0xFFFFFFFF
            pc += 4
        elif op == OP_DIV:
            a = rf[rs1]; b = rf[rs2]
            if b == 0:
                rf[rd] = 0
            else:
                rf[rd] = a // b  # unsigned div for simplicity
            pc += 4
        elif op == OP_ADDI:
            rf[rd] = (rf[rs1] + imm) & 0xFFFFFFFF
            pc += 4
        elif op == OP_SUBI:
            rf[rd] = (rf[rs1] - imm) & 0xFFFFFFFF
            pc += 4
        elif op == OP_AND:
            rf[rd] = rf[rs1] & rf[rs2]; pc += 4
        elif op == OP_OR:
            rf[rd] = rf[rs1] | rf[rs2]; pc += 4
        elif op == OP_XOR:
            rf[rd] = rf[rs1] ^ rf[rs2]; pc += 4
        elif op == OP_CMP:
            # sets rd = rs1 - rs2 (or flags); simplified: rd = difference
            rf[rd] = (rf[rs1] - rf[rs2]) & 0xFFFFFFFF
            pc += 4
        elif op == OP_LOAD:
            rf[rd] = dmem.get(rf[rs1] + imm, 0)
            pc += 4
        elif op == OP_STORE:
            addr = (rf[rs1] + imm) & 0xFFFFFFFF
            dmem[addr] = rf[rs2] & 0xFFFFFFFF  # Verilog uses rs2 as data
            pc += 4
        elif op == OP_JMP:
            pc = imm
        elif op == OP_JZ:
            pc = imm if rf[rs1] == 0 else pc + 4
        elif op == OP_JNZ:
            pc = imm if rf[rs1] != 0 else pc + 4
        elif op == OP_JAL:
            rf[rd] = (pc + 4) & 0xFFFFFFFF if rd != 0 else rf[rd]
            pc = imm
        elif op == OP_CALL:
            rf[1] = (pc + 4) & 0xFFFFFFFF
            pc = imm
        elif op == OP_RET:
            pc = rf[1]
        elif op == OP_SENSE:
            rf[rd] = 0  # no sensors
            pc += 4
        elif op == OP_EMIT:
            pc += 4
        else:
            print(f"  unknown op={op} at pc={pc}")
            pc += 4

        # halt detection: infinite loop on self-jump
        if cyc > 100 and pc == prev_pc and op == OP_JMP:
            return dmem.get(0, None), cyc
        prev_pc = pc

    return dmem.get(0, None), cyc


# ── 打印 hex 文件 (反汇编) ──
def disasm(hexfile, n=None):
    imem = []
    with open(hexfile) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            v = int(line, 16)
            lo = v & 0xFFFFFFFF
            hi = (v >> 32) & 0xFFFFFFFF
            imem.append(lo)
            imem.append(hi)

    print(f"  {hexfile}: {len(imem)} entries")
    for i, instr in enumerate(imem):
        if n is not None and i >= n: break
        op, rd, rs1, rs2, imm = dec(instr)
        opname = OP_BY_NAME.get(op, f"?{op}")
        if op == OP_STORE:
            print(f"    [{i*4:3d}] {opname} r{rd}=data, r{rs1}[{imm}]")
        elif op in (OP_PUSH, OP_JMP, OP_JAL, OP_CALL):
            print(f"    [{i*4:3d}] {opname} rd=r{rd} imm={imm}")
        elif op in (OP_JZ, OP_JNZ):
            print(f"    [{i*4:3d}] {opname} r{rs1} -> {imm}")
        elif op in (OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_AND, OP_OR, OP_XOR):
            print(f"    [{i*4:3d}] {opname} r{rd} = r{rs1}, r{rs2}")
        elif op in (OP_ADDI, OP_SUBI):
            print(f"    [{i*4:3d}] {opname} r{rd} = r{rs1}, {imm}")
        elif op == OP_LOAD:
            print(f"    [{i*4:3d}] {opname} r{rd} = mem[r{rs1}+{imm}]")
        elif op == OP_NOP:
            print(f"    [{i*4:3d}] NOP")
        else:
            print(f"    [{i*4:3d}] {opname} rd={rd} rs1={rs1} rs2={rs2} imm={imm}")

if __name__ == "__main__":
    print("=== v1.4 反汇编 ===")
    print()
    for fn in ["prog_sigma_100.hex", "prog_mul.hex", "prog_div.hex"]:
        disasm(fn)
        print()

    print("=== v1.4 功能执行 ===")
    for fn, expected, desc in [
        ("prog_sigma_100.hex", 5050, "Σ(1..100)"),
        ("prog_mul.hex", 425, "25*17"),
        ("prog_div.hex", 76, "1000/13"),
    ]:
        result, cyc = run(fn)
        status = "PASS" if result == expected else "FAIL"
        print(f"  {desc}: dmem[0]={result} expected={expected} {status} (cycles={cyc})")
