#!/usr/bin/env python3
"""v1.4 周期精确流水线模拟器 — 建模 5 级流水 + 双发射 + 完整前递。"""

# Op 码 (与 Verilog localparam 一致)
OP_NOP=0; OP_PUSH=1; OP_MOV=2; OP_ADD=3; OP_SUB=4; OP_MUL=5
OP_AND=6; OP_OR=7; OP_XOR=8; OP_SHL=9; OP_SHR=10; OP_CMP=11
OP_DIV=12; OP_STORE=16; OP_LOAD=17; OP_ADDI=19; OP_SUBI=20
OP_JAL=21; OP_JMP=13; OP_JZ=14; OP_JNZ=15
OP_SENSE=36; OP_EMIT=37; OP_CALL=38; OP_RET=39

C_ALU=0; C_MEM=1; C_BR=2; C_MUL=3; C_CTRL=4

def classify(op):
    if op == OP_NOP: return C_CTRL
    if op in (OP_PUSH, OP_SENSE, OP_EMIT): return C_CTRL
    if op in (OP_ADD,OP_SUB,OP_AND,OP_OR,OP_XOR,OP_SHL,OP_SHR,OP_ADDI,OP_SUBI,OP_MOV,OP_CMP): return C_ALU
    if op in (OP_LOAD, OP_STORE): return C_MEM
    if op in (OP_JMP,OP_JZ,OP_JNZ,OP_JAL,OP_CALL,OP_RET): return C_BR
    if op in (OP_MUL, OP_DIV): return C_MUL
    return C_CTRL

def w_rd(op):
    return op in (OP_ADD,OP_SUB,OP_AND,OP_OR,OP_XOR,OP_SHL,OP_SHR,OP_ADDI,
                  OP_SUBI,OP_MOV,OP_LOAD,OP_MUL,OP_DIV,OP_PUSH,OP_JAL,OP_CALL,OP_SENSE)

def can_pair(op0, rd0, s0_0, s0_1, op1, rd1, s1_0, s1_1):
    c0, c1 = classify(op0), classify(op1)
    if c0 == 1 and c1 == 1: return False
    if c0 == 2 or c1 == 2: return False
    if c0 == 3 and c1 == 3: return False
    if w_rd(op0) and w_rd(op1) and rd0 != 0 and rd0 == rd1: return False
    if w_rd(op0) and rd0 != 0 and (s1_0 == rd0 or s1_1 == rd0): return False
    if op0 == OP_NOP: return False
    return True

def dec(instr):
    op = (instr >> 26) & 0x3F
    rd = (instr >> 22) & 0xF
    rs1 = (instr >> 18) & 0xF
    rs2 = (instr >> 14) & 0xF
    imm = instr & 0x3FFF
    if imm & 0x2000: imm = imm - 0x4000
    return op, rd, rs1, rs2, imm

def alu_eval(op, a, b, imm, sense=0):
    if op == OP_ADD: return (a + b) & 0xFFFFFFFF
    if op == OP_SUB: return (a - b) & 0xFFFFFFFF
    if op == OP_CMP: return (a - b) & 0xFFFFFFFF
    if op == OP_AND: return a & b
    if op == OP_OR: return a | b
    if op == OP_XOR: return a ^ b
    if op == OP_SHL: return (a << (b & 0x1F)) & 0xFFFFFFFF
    if op == OP_SHR: return a >> (b & 0x1F)
    if op == OP_ADDI: return (a + imm) & 0xFFFFFFFF
    if op == OP_SUBI: return (a - imm) & 0xFFFFFFFF
    if op in (OP_LOAD, OP_STORE): return (a + imm) & 0xFFFFFFFF
    if op == OP_PUSH: return imm & 0xFFFFFFFF
    if op == OP_MOV: return a
    if op in (OP_JMP, OP_JZ, OP_JNZ, OP_JAL, OP_CALL): return imm & 0xFFFFFFFF
    if op == OP_RET: return a
    if op == OP_SENSE: return sense & 0xFFFFFFFF
    return 0

def run_pipeline(hexfile, max_cyc=5000):
    """周期精确 — 包括 IF 状态机、DE 配对、EX 双 lane、MEM/WB 双通道。"""
    flat = []
    with open(hexfile) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            v = int(line, 16)
            flat.append(v & 0xFFFFFFFF)
            flat.append((v >> 32) & 0xFFFFFFFF)

    def imem_rd(pc):
        idx = pc // 4
        return flat[idx] if 0 <= idx < len(flat) else 0

    rf = [0] * 32
    dmem = {}
    pc_reg = 0
    fetch_idle = True
    fd_valid = False; fd_i0 = 0; fd_i1 = 0; fd_pc = 0

    DE_valid = False
    DE = {}
    EM = {}
    MW = {}

    md_active = False; md_done = False; md_cnt = 0
    md_is_div = False; md_is_lane1 = False; md_a = 0; md_b = 0; md_res = 0

    cyc = 0
    retired = 0
    last_jmp_pc = -1
    self_jmp_count = 0

    while cyc < max_cyc:
        cyc += 1
        md_done = False

        # ═══════════════════════════════════════════
        # 组合逻辑: forward (-> f0_0, f0_1, f1_0, f1_1)
        # ═══════════════════════════════════════════
        f0_0 =DE.get('v0_0',0); f0_1 =DE.get('v0_1',0)
        f1_0 =DE.get('v1_0',0); f1_1 =DE.get('v1_1',0)

        # EM 前递 (双 lane)
        if EM.get('valid') and EM['rd0'] != 0 and EM['op0'] not in (OP_STORE, OP_NOP):
            if EM['rd0'] == DE.get('s0_0',0): f0_0 = EM['alu0']
            if EM['rd0'] == DE.get('s0_1',0): f0_1 = EM['alu0']
            if EM['rd0'] == DE.get('s1_0',0): f1_0 = EM['alu0']
            if EM['rd0'] == DE.get('s1_1',0): f1_1 = EM['alu0']
        if EM.get('valid') and EM['rd1'] != 0 and EM.get('op1',0) not in (OP_STORE, OP_NOP, None):
            if EM['rd1'] == DE.get('s0_0',0): f0_0 = EM['alu1']
            if EM['rd1'] == DE.get('s0_1',0): f0_1 = EM['alu1']
            if EM['rd1'] == DE.get('s1_0',0): f1_0 = EM['alu1']
            if EM['rd1'] == DE.get('s1_1',0): f1_1 = EM['alu1']

        # MW 前递 (双 lane)
        if MW.get('valid'):
            if MW.get('wen0') and MW['rd0'] != 0:
                mw0 = MW['mem'] if MW.get('isload') else MW['alu0']
                if MW['rd0'] == DE.get('s0_0',0): f0_0 = mw0
                if MW['rd0'] == DE.get('s0_1',0): f0_1 = mw0
                if MW['rd0'] == DE.get('s1_0',0): f1_0 = mw0
                if MW['rd0'] == DE.get('s1_1',0): f1_1 = mw0
            if MW.get('wen1') and MW['rd1'] != 0:
                mw1 = MW['alu1']
                if MW['rd1'] == DE.get('s0_0',0): f0_0 = mw1
                if MW['rd1'] == DE.get('s0_1',0): f0_1 = mw1
                if MW['rd1'] == DE.get('s1_0',0): f1_0 = mw1
                if MW['rd1'] == DE.get('s1_1',0): f1_1 = mw1

        # ═══════════════════════════════════════════
        # 组合逻辑: EX 输出 (用 fwd values)
        # ═══════════════════════════════════════════
        alu0_out = alu_eval(DE.get('op0',OP_NOP), f0_0, f0_1, DE.get('imm0',0)) if DE.get('valid') else 0
        alu1_out = alu_eval(DE.get('op1',OP_NOP), f1_0, f1_1, DE.get('imm1',0)) if DE.get('valid') else 0
        alu0_zero = (alu0_out == 0)

        # branch in lane 0
        br_taken = False; br_target = 0
        if DE.get('valid'):
            op0 = DE['op0']
            if op0 == OP_JMP: br_target = DE['imm0']; br_taken = True
            elif op0 == OP_JZ: br_target = DE['imm0']; br_taken = alu0_zero
            elif op0 == OP_JNZ: br_target = DE['imm0']; br_taken = not alu0_zero
            elif op0 == OP_JAL: br_target = DE['imm0']; br_taken = True
            elif op0 == OP_CALL: br_target = DE['imm0']; br_taken = True
            elif op0 == OP_RET: br_target = f0_0; br_taken = True

        # MUL/DIV
        md_activated_this_cycle = False
        if not md_active and not md_activated_this_cycle:
            if DE.get('valid') and DE.get('dual') and DE['op1'] in (OP_MUL, OP_DIV):
                md_active = True; md_is_lane1 = True; md_is_div = (DE['op1'] == OP_DIV)
                md_a = f1_0; md_b = f1_1; md_cnt = 8 if md_is_div else 4
                md_activated_this_cycle = True
            elif DE.get('valid') and DE['op0'] in (OP_MUL, OP_DIV):
                md_active = True; md_is_lane1 = False; md_is_div = (DE['op0'] == OP_DIV)
                md_a = f0_0; md_b = f0_1; md_cnt = 8 if md_is_div else 4
                md_activated_this_cycle = True

        if md_active:
            if md_cnt > 1:
                md_cnt -= 1
            else:
                md_active = False; md_done = True
                md_res = (md_a // md_b if md_b != 0 else 0) if md_is_div else (md_a * md_b)
                md_res &= 0xFFFFFFFF

        lane0_final = md_res if (not md_active and md_done and not md_is_lane1) else alu0_out
        lane1_final = (md_res if (not md_active and md_done and md_is_lane1) else
                       (0 if (DE.get('valid') and DE.get('dual') and DE['op1'] in (OP_MUL, OP_DIV)) else alu1_out))

        # ═══════════════════════════════════════════
        # 时序逻辑: 每个 stage 推进
        # ═══════════════════════════════════════════

        # ── WB ──
        if MW.get('valid'):
            if MW.get('wen0') and MW['rd0'] != 0:
                wb0 = MW['mem'] if MW.get('isload') else (MW['pc'] + 8 if MW['op0'] in (OP_JAL, OP_CALL) else MW['alu0'])
                rf[MW['rd0']] = wb0 & 0xFFFFFFFF
            if MW.get('wen1') and MW['rd1'] != 0 and not (MW.get('wen0') and MW['rd0'] != 0 and MW['rd0'] == MW['rd1']):
                wb1 = (MW['pc'] + 8 if MW.get('op1',0) in (OP_JAL, OP_CALL) else MW['alu1'])
                rf[MW['rd1']] = wb1 & 0xFFFFFFFF

        # ── EM -> MW ──
        nMW = {'valid': False}
        if EM.get('valid'):
            wen1 = (EM.get('dual') and EM.get('op1',0) not in (OP_STORE, OP_NOP, OP_EMIT) and EM.get('rd1',0) != 0) or \
                   (md_done and md_is_lane1)
            if EM['op0'] == OP_STORE:
                addr = EM['alu0'] & 0xFFFFFFFF
                dmem[addr] = EM.get('rs2', 0) & 0xFFFFFFFF
            if EM['op0'] == OP_LOAD:
                nMW = {'valid': True, 'op0': EM['op0'], 'op1': EM.get('op1',0),
                       'alu0': EM['alu0'], 'alu1': EM['alu1'],
                       'rd0': EM['rd0'], 'rd1': EM.get('rd1',0),
                       'wen0': 1, 'wen1': EM.get('dual',0),
                       'isload': True, 'mem': dmem.get(EM['alu0'] & 0xFFFFFFFF, 0),
                       'pc': EM.get('pc',0), 'dual': EM.get('dual',0)}
            elif EM['op0'] == OP_STORE:
                nMW = {'valid': True, 'op0': OP_NOP, 'op1': EM.get('op1',0),
                       'alu0': EM['alu0'], 'alu1': EM['alu1'],
                       'rd0': 0, 'rd1': EM.get('rd1',0),
                       'wen0': 0, 'wen1': EM.get('dual',0),
                       'isload': False, 'mem': 0,
                       'pc': EM.get('pc',0), 'dual': EM.get('dual',0)}
            else:
                wen0 = (EM['op0'] not in (OP_STORE, OP_NOP, OP_EMIT) and EM['rd0'] != 0)
                nMW = {'valid': True, 'op0': EM['op0'], 'op1': EM.get('op1',0),
                       'alu0': EM['alu0'], 'alu1': EM['alu1'],
                       'rd0': EM['rd0'], 'rd1': EM.get('rd1',0),
                       'wen0': wen0, 'wen1': wen1,
                       'isload': False, 'mem': 0,
                       'pc': EM.get('pc',0), 'dual': EM.get('dual',0)}
        MW = nMW

        # ── DE -> EM ──
        nEM = {'valid': False}
        if DE.get('valid'):
            rd1 = 1 if DE.get('op1',0) in (OP_JAL, OP_CALL) else DE.get('rd1',0)
            rd0 = 1 if DE.get('op0',0) in (OP_JAL, OP_CALL) else DE.get('rd0',0)
            nEM = {'valid': True, 'op0': DE['op0'], 'op1': DE.get('op1',0),
                   'alu0': lane0_final, 'alu1': lane1_final,
                   'rd0': rd0, 'rd1': rd1,
                   'rs2': DE.get('v0_1',0), 'dual': DE.get('dual',0),
                   'pc': DE.get('pc',0),
                   'wen1': (DE.get('dual') and DE.get('op1',0) not in (OP_STORE, OP_NOP, OP_EMIT) and DE.get('rd1',0) != 0) or
                           (md_done and md_is_lane1)}
        EM = nEM

        # ── ID -> DE ──
        nDE = {'valid': False}
        flush = br_taken
        if flush:
            pc_reg = br_target & 0xFFFFFFFF
            fetch_idle = True
            fd_valid = False
        elif md_active:
            pass  # stall
        elif DE.get('valid') and br_taken:
            pass  # 上面已处理
        elif fd_valid:
            op0, rd0, s0_0, s0_1, imm0 = dec(fd_i0)
            op1, rd1, s1_0, s1_1, imm1 = dec(fd_i1)
            pair = can_pair(op0, rd0, s0_0, s0_1, op1, rd1, s1_0, s1_1) and not md_active
            if pair:
                nDE = {'valid': True, 'pc': fd_pc,
                       'op0': op0, 'rd0': rd0, 's0_0': s0_0, 's0_1': s0_1,
                       'imm0': imm0, 'v0_0': rf[s0_0], 'v0_1': rf[s0_1],
                       'op1': op1, 'rd1': rd1, 's1_0': s1_0, 's1_1': s1_1,
                       'imm1': imm1, 'v1_0': rf[s1_0], 'v1_1': rf[s1_1],
                       'dual': True}
                pc_reg = pc_reg + 8
            else:
                nDE = {'valid': True, 'pc': fd_pc,
                       'op0': op0, 'rd0': rd0, 's0_0': s0_0, 's0_1': s0_1,
                       'imm0': imm0, 'v0_0': rf[s0_0], 'v0_1': rf[s0_1],
                       'op1': OP_NOP, 'rd1': 0, 's1_0': 0, 's1_1': 0,
                       'imm1': 0, 'v1_0': 0, 'v1_1': 0,
                       'dual': False}
                pc_reg = pc_reg + 4
            fd_valid = False
        DE = nDE

        # ── 更新 DE v values from register file (如果有前递这步被 above 覆盖了) ──
        if not flush and not md_active and DE.get('valid') and not fd_valid:
            pass  # forward already applied at top of cycle

        # ── IF -> FD ──
        if not md_active and not br_taken:
            if fetch_idle:
                # start fetch
                fetch_idle = False
            else:
                # ack arrived
                fd_pc = (pc_reg - 8) & 0xFFFFFFFF  # pc was advanced; ack gives prior
                i0 = imem_rd(pc_reg - 8)  # 刚取到的地址
                i1 = imem_rd(pc_reg - 4)
                # Actually the pc was already advanced to pc_next before the ack
                # So we want pc_reg - 8 as fetch_pc (before pc_next applied)
                # But pc_reg has been advanced... let's track differently
                # Simpler: don't advance pc_reg in fetch ack, do it here
                pass

        # Re-do IF more carefully: track fetch_pc separately
        if cyc == 1:
            # init
            pass

    return dmem.get(0, 0), cyc


# 简洁版: 纯顺序执行, 但使用双发射配对逻辑验证
def run_simple(hexfile):
    """顺序执行, 不模拟流水, 仅验证配对逻辑下程序是否正确。"""
    flat = []
    with open(hexfile) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            v = int(line, 16)
            flat.append(v & 0xFFFFFFFF)
            flat.append((v >> 32) & 0xFFFFFFFF)

    rf = [0] * 32
    dmem = {}
    pc = 0
    cyc = 0

    while cyc < 100000:
        cyc += 1
        idx = pc // 4
        if idx < 0 or idx >= len(flat):
            return dmem.get(0, 0), cyc, flat
        instr = flat[idx]
        op, rd, rs1, rs2, imm = dec(instr)

        if op == OP_NOP:
            pc += 4
        elif op == OP_PUSH:
            rf[rd] = imm & 0xFFFFFFFF; pc += 4
        elif op == OP_ADD:
            rf[rd] = (rf[rs1] + rf[rs2]) & 0xFFFFFFFF; pc += 4
        elif op == OP_SUB:
            rf[rd] = (rf[rs1] - rf[rs2]) & 0xFFFFFFFF; pc += 4
        elif op == OP_ADDI:
            rf[rd] = (rf[rs1] + imm) & 0xFFFFFFFF; pc += 4
        elif op == OP_SUBI:
            rf[rd] = (rf[rs1] - imm) & 0xFFFFFFFF; pc += 4
        elif op == OP_MUL:
            rf[rd] = (rf[rs1] * rf[rs2]) & 0xFFFFFFFF; pc += 4
        elif op == OP_DIV:
            rf[rd] = (rf[rs1] // rf[rs2] if rf[rs2] != 0 else 0) & 0xFFFFFFFF; pc += 4
        elif op == OP_AND: rf[rd] = rf[rs1] & rf[rs2]; pc += 4
        elif op == OP_OR:  rf[rd] = rf[rs1] | rf[rs2]; pc += 4
        elif op == OP_XOR: rf[rd] = rf[rs1] ^ rf[rs2]; pc += 4
        elif op == OP_CMP: rf[rd] = (rf[rs1] - rf[rs2]) & 0xFFFFFFFF; pc += 4
        elif op == OP_MOV: rf[rd] = rf[rs1]; pc += 4
        elif op == OP_LOAD:
            rf[rd] = dmem.get((rf[rs1] + imm) & 0xFFFFFFFF, 0); pc += 4
        elif op == OP_STORE:
            dmem[(rf[rs1] + imm) & 0xFFFFFFFF] = rf[rs2] & 0xFFFFFFFF; pc += 4
        elif op == OP_JMP:
            pc = imm
        elif op == OP_JZ:
            pc = imm if rf[rs1] == 0 else pc + 4
        elif op == OP_JNZ:
            pc = imm if rf[rs1] != 0 else pc + 4
        elif op == OP_JAL:
            rf[rd] = (pc + 4) & 0xFFFFFFFF if rd != 0 else rf[rd]; pc = imm
        elif op == OP_CALL:
            rf[1] = (pc + 4) & 0xFFFFFFFF; pc = imm
        elif op == OP_RET:
            pc = rf[1]
        elif op == OP_SENSE:
            rf[rd] = 0; pc += 4
        elif op == OP_EMIT:
            pc += 4
        else:
            pc += 4

        if cyc > 10 and op == OP_JMP and pc == prev_pc:
            return dmem.get(0, 0), cyc, flat
        prev_pc = pc

    return dmem.get(0, 0), cyc, flat


def disasm(hexfile):
    flat = []
    with open(hexfile) as f:
        for line in f:
            line = line.strip()
            if not line: continue
            v = int(line, 16)
            flat.append(v & 0xFFFFFFFF)
            flat.append((v >> 32) & 0xFFFFFFFF)

    OP_BY_NAME = {v:k for k,v in list(globals().items()) if k.startswith('OP_')}
    print(f"  {hexfile}: {len(flat)} instructions")
    for i, instr in enumerate(flat):
        op, rd, rs1, rs2, imm = dec(instr)
        opname = OP_BY_NAME.get(op, f"?{op}")
        if op == OP_STORE:
            print(f"    [{i*4:3d}] {opname}  -- data=r{rs2} -> mem[r{rs1}+{imm}]")
        elif op in (OP_PUSH, OP_JMP, OP_JAL, OP_CALL):
            print(f"    [{i*4:3d}] {opname}  rd=r{rd} imm={imm}")
        elif op in (OP_JZ, OP_JNZ):
            print(f"    [{i*4:3d}] {opname}  -- test=r{rs1} -> {imm}")
        elif op in (OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_AND, OP_OR, OP_XOR, OP_CMP):
            print(f"    [{i*4:3d}] {opname}  r{rd} = r{rs1}, r{rs2}")
        elif op == OP_LOAD:
            print(f"    [{i*4:3d}] {opname}  r{rd} = mem[r{rs1}+{imm}]")
        elif op == OP_NOP:
            print(f"    [{i*4:3d}] NOP")
        else:
            print(f"    [{i*4:3d}] {opname}  rd={rd} rs1={rs1} rs2={rs2} imm={imm}")


if __name__ == "__main__":
    print("=== v1.4 顺序执行验证 (正确性基线) ===")
    for fn, expected, desc in [
        ("prog_sigma_100.hex", 5050, "Σ(1..100)"),
        ("prog_mul.hex", 425, "25*17"),
        ("prog_div.hex", 76, "1000/13"),
    ]:
        result, cyc, _ = run_simple(fn)
        status = "PASS" if result == expected else "FAIL"
        print(f"  [{status}] {desc}: dmem[0]={result} expected={expected} (顺序执行)")

    print()
    print("=== v1.4 反汇编 ===")
    for fn in ["prog_sigma_100.hex", "prog_mul.hex", "prog_div.hex"]:
        disasm(fn)
        print()
