#!/usr/bin/env python3
"""v1.4 双发射汇编器 — 自动配对感知, 与 Verilog can_pair 严格对应。

指令格式: bits[31:26]=opcode [25:22]=rd [21:18]=rs1 [17:14]=rs2 [13:0]=imm
STORE: rs2=data, rs1=address base (data 从 source 角度的 'rd' 进入 encoder, 变成 rs2 字段)
"""

OP = {
    'NOP':0, 'PUSH':1, 'MOV':2, 'ADD':3, 'SUB':4, 'MUL':5,
    'AND':6, 'OR':7, 'XOR':8, 'SHL':9, 'SHR':10, 'CMP':11,
    'DIV':12, 'STORE':16, 'LOAD':17, 'ADDI':19, 'SUBI':20,
    'JAL':21, 'JMP':13, 'JZ':14, 'JNZ':15, 'SENSE':36,
    'EMIT':37, 'CALL':38, 'RET':39,
}


def decode_regs(line):
    """解析操作数. 返回 (op, rd, rs1, rs2, imm_token).
    关键: 对 STORE, 把 data register 放入 rs2 (匹配 Verilog 编码); 其余按恒等映射."""
    parts = line.replace(',', ' ').replace('[', ' ').replace(']', ' ').split()
    parts = [p for p in parts if p]
    op = parts[0]
    rnums = [int(p.replace('r', '')) for p in parts[1:] if p.startswith('r')]
    itoks = [p for p in parts[1:] if not p.startswith('r')]

    rd = rs1 = rs2 = 0
    if op == 'STORE':
        rs2 = rnums[0] if len(rnums) >= 1 else 0  # data → rs2 field
        rs1 = rnums[1] if len(rnums) >= 2 else 0  # addr base → rs1 field
    elif op == 'LOAD':
        rd  = rnums[0] if len(rnums) >= 1 else 0
        rs1 = rnums[1] if len(rnums) >= 2 else 0
    elif op in ('JZ', 'JNZ', 'RET'):
        rs1 = rnums[0] if len(rnums) >= 1 else 0  # tested register → rs1 (matches Verilog)
    else:
        rd  = rnums[0] if len(rnums) >= 1 else 0
        rs1 = rnums[1] if len(rnums) >= 2 else 0
        rs2 = rnums[2] if len(rnums) >= 3 else 0

    imm_tok = itoks[-1] if itoks else '0'
    return op, rd, rs1, rs2, imm_tok


def classify(op):
    if op == 'NOP': return 5
    if op in ('PUSH', 'SENSE', 'EMIT'): return 4
    if op in ('ADD','SUB','AND','OR','XOR','SHL','SHR','ADDI','SUBI','MOV','CMP'): return 0
    if op in ('LOAD','STORE'): return 1
    if op in ('JMP','JZ','JNZ','JAL','CALL','RET'): return 2
    if op in ('MUL','DIV'): return 3
    return 4


def writes_rd(op):
    return op in ('ADD','SUB','AND','OR','XOR','SHL','SHR','ADDI','SUBI',
                  'MOV','LOAD','MUL','DIV','PUSH','JAL','CALL','SENSE')


def can_pair(op0, rd0, s0_0, s0_1, op1, rd1, s1_0, s1_1):
    """与 Verilog 中的 can_pair 函数严格一致。"""
    c0, c1 = classify(op0), classify(op1)
    if c0 == 1 and c1 == 1: return False   # 双 MEM
    if c0 == 2 or c1 == 2: return False    # branch 不配对
    if c0 == 3 and c1 == 3: return False   # 双 MUL
    if writes_rd(op0) and writes_rd(op1) and rd0 != 0 and rd0 == rd1:
        return False  # WAW
    if writes_rd(op0) and rd0 != 0 and (s1_0 == rd0 or s1_1 == rd0):
        return False  # RAW (op1 读取 op0 要写入的 reg; 对 STORE, s1_1 已经是 data reg)
    if op0 == 'NOP': return False
    return True


def assemble(raw_lines):
    # 第一遍: 收集指令与标签 (标签记录指令索引)
    labels = {}
    stripped = []
    for line in raw_lines:
        line = line.strip()
        if '#' in line: line = line[:line.index('#')].strip()
        if not line: continue
        if line.startswith('LABEL '):
            labels[line.split()[1]] = len(stripped)
            continue
        stripped.append(line)

    # 配对
    pairs = []
    i = 0
    while i < len(stripped):
        if i + 1 < len(stripped):
            op0, rd0, s0_0, s0_1, _ = decode_regs(stripped[i])
            op1, rd1, s1_0, s1_1, _ = decode_regs(stripped[i + 1])
            if can_pair(op0, rd0, s0_0, s0_1, op1, rd1, s1_0, s1_1):
                pairs.append((i, i + 1))
                i += 2
                continue
        pairs.append((i, None))
        i += 1

    # 每条指令在最终二进制中的实际发射地址
    # (单发射指令后插入 NOP 填充, 实际地址与源码顺序地址可能不同)
    ins_addr = {}
    a = 0
    for i0, i1 in pairs:
        ins_addr[i0] = a
        a += 4
        if i1 is not None:
            ins_addr[i1] = a
            a += 4
        else:
            a += 4  # NOP 填充占一个槽位

    # 编码: 每条 emit 为一条 32-bit, 用 0 (NOP) 填充奇数 length
    code = []
    for i0, i1 in pairs:
        for idx in (i0, i1):
            ln = stripped[idx] if idx is not None else 'NOP'
            op, rd, rs1, rs2, itok = decode_regs(ln)
            if itok and itok in labels:
                imm = ins_addr[labels[itok]]
            else:
                imm = int(itok) if (itok and not itok.startswith('r')) else 0
            enc = ((OP[op] & 0x3F) << 26) | ((rd & 0xF) << 22) | ((rs1 & 0xF) << 18) | ((rs2 & 0xF) << 14) | (imm & 0x3FFF)
            code.append(enc)

    return code


def write_hex(name, code):
    assert len(code) % 2 == 0, f"odd length: {len(code)}"
    with open(name, 'w') as f:
        for i in range(0, len(code), 2):
            lo, hi = code[i], code[i + 1]
            f.write(f"{(hi << 32) | lo:016x}\n")
    print(f"  {name}: {len(code)} ins -> {len(code)//2} entries")


# ─── Σ(1..100) = 5050 ───
# halt 用 8 字节对齐的自跳 JMP (跳到自身): v1.4 双发射丢弃 i1,
# 非对齐跳转目标会把回边的 JMP 放在 i1 位置而被丢弃, halt 循环失效
sigma_src = """
PUSH r1, 100
PUSH r2, 0
LABEL loop
ADD r2, r2, r1
SUBI r1, r1, 1
JNZ r1, loop
STORE r2, r0[0]
LABEL halt
JMP halt
"""

# ─── MUL 25 * 17 = 425 ───
mul_src = """
PUSH r1, 25
PUSH r2, 17
MUL r3, r1, r2
STORE r3, r0[0]
LABEL halt
JMP halt
"""

# ─── DIV 1000 / 13 = 76 ───
div_src = """
PUSH r1, 1000
PUSH r2, 13
DIV r3, r1, r2
STORE r3, r0[0]
LABEL halt
JMP halt
"""

# ─── 逻辑/移位/内存综合测试 ───
# r3=80 r4=10 r5=20 r6=17 r7=0 r8=30 r9=30 r10=-10
# JZ(not taken) -> r11=5; r12=100; dmem[0]=100; r13=105; dmem[4]=105
logic_src = """
PUSH r1, 10
PUSH r2, 3
SHL r3, r1, r2
SHR r4, r3, r2
MOV r5, r4
ADD r5, r5, r1
SUB r6, r5, r2
AND r7, r5, r1
OR r8, r5, r1
XOR r9, r5, r1
CMP r10, r7, r1
JZ r10, taken
PUSH r11, 5
LABEL taken
ADDI r12, r8, 70
STORE r12, r0[0]
LOAD r13, r0[0]
SHL r14, r1, r2
NOP
ADD r13, r13, r11
STORE r13, r0[4]
LABEL halt
JMP halt
"""

if __name__ == "__main__":
    for name, src in [("prog_sigma_100.hex", sigma_src),
                       ("prog_mul.hex", mul_src),
                       ("prog_div.hex", div_src),
                       ("prog_logic.hex", logic_src)]:
        code = assemble(src.strip().split('\n'))
        write_hex(name, code)
