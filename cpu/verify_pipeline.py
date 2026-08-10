#!/usr/bin/env python3
"""v1.4 周期精确流水线模拟器

用途: 提供流水线级结构追踪 (cycle-trace) 用于前递逻辑验证。
与 hunyuan_cpu_v14.v 语义对齐:
- DE/EM/MW 流水寄存器; DE 保持期间冻结 EM/MW (防同一指令重复推进)
- JZ/JNZ 的 ALU 输出 = 测试值 a (f0_0), 不是 imm
- STORE 的 rs2 数据走前递网络 (f0_1)
- 双发射丢弃 i1: 配对失败的单发射指令后补 NOP 填充, 标签地址基于实际发射地址
- 自跳 JMP (目标=自身地址, 8 字节对齐) 作为 halt, 检测到即停机返回实际周期
- 前递优先级: MW → EM (EM 更新), LOAD 结果仅 MW 阶段可用 (无 LOAD stall)
- 四个测试全部通过: Σ(1..100)=5050, 25*17=425, 1000/13=76, logic(dmem[0]=100,dmem[4]=105)
"""

import sys
OP_NOP=0; OP_PUSH=1; OP_MOV=2; OP_ADD=3; OP_SUB=4; OP_MUL=5
OP_AND=6; OP_OR=7; OP_XOR=8; OP_SHL=9; OP_SHR=10; OP_CMP=11
OP_DIV=12; OP_STORE=16; OP_LOAD=17; OP_ADDI=19; OP_SUBI=20
OP_JAL=21; OP_JMP=13; OP_JZ=14; OP_JNZ=15
OP_SENSE=36; OP_EMIT=37; OP_CALL=38; OP_RET=39

def dec(i):
    imm_field = i & 0x3FFF
    imm = (imm_field - 0x4000) if (imm_field & 0x2000) else imm_field
    return (i>>26)&0x3F, (i>>22)&0xF, (i>>18)&0xF, (i>>14)&0xF, imm

def alu(op,a,b,imm):
    if op==OP_ADD: return (a+b)&0xFFFFFFFF
    if op==OP_SUB: return (a-b)&0xFFFFFFFF
    if op==OP_ADDI: return (a+imm)&0xFFFFFFFF
    if op==OP_SUBI: return (a-imm)&0xFFFFFFFF
    if op==OP_AND: return a&b
    if op==OP_OR: return a|b
    if op==OP_XOR: return a^b
    if op==OP_SHL: return (a<<(b&0x1F))&0xFFFFFFFF
    if op==OP_SHR: return a>>(b&0x1F)
    if op==OP_CMP: return (a-b)&0xFFFFFFFF
    if op in (OP_LOAD,OP_STORE): return (a+imm)&0xFFFFFFFF
    if op==OP_PUSH: return imm&0xFFFFFFFF
    if op==OP_MOV: return a
    if op in (OP_JMP,OP_JAL,OP_CALL): return imm&0xFFFFFFFF
    if op in (OP_JZ,OP_JNZ): return a
    if op==OP_RET: return a
    if op==OP_SENSE: return 0
    return 0

def classify(op):
    if op==OP_NOP: return 4
    if op in (OP_PUSH,OP_SENSE,OP_EMIT): return 4
    if op in (OP_ADD,OP_SUB,OP_AND,OP_OR,OP_XOR,OP_SHL,OP_SHR,OP_ADDI,OP_SUBI,OP_MOV,OP_CMP): return 0
    if op in (OP_LOAD,OP_STORE): return 1
    if op in (OP_JMP,OP_JZ,OP_JNZ,OP_JAL,OP_CALL,OP_RET): return 2
    if op in (OP_MUL,OP_DIV): return 3
    return 4

def w_rd(op):
    return op in (OP_ADD,OP_SUB,OP_AND,OP_OR,OP_XOR,OP_SHL,OP_SHR,OP_ADDI,OP_SUBI,OP_MOV,OP_LOAD,OP_MUL,OP_DIV,OP_PUSH,OP_JAL,OP_CALL,OP_SENSE)

def can_pair(op0,rd0,s0_0,s0_1,op1,rd1,s1_0,s1_1):
    c0,c1 = classify(op0),classify(op1)
    if c0==1 and c1==1: return False
    if c0==2 or c1==2: return False
    if c0==3 and c1==3: return False
    if w_rd(op0) and w_rd(op1) and rd0!=0 and rd0==rd1: return False
    if w_rd(op0) and rd0!=0 and (s1_0==rd0 or s1_1==rd0): return False
    if op0==OP_NOP: return False
    return True

def sim(hexfile, max_cyc=5000):
    flat=[]
    with open(hexfile) as f:
        for line in f:
            line=line.strip()
            if not line: continue
            v=int(line,16); flat.append(v&0xFFFFFFFF); flat.append((v>>32)&0xFFFFFFFF)
    rf=[0]*32; dmem=[0]*4096
    pc_reg=0; fetch_idle=True
    fd_inflight=False; fd_adr=0
    FD={"valid":False,"i0":0,"i1":0,"pc":0}
    DE={"valid":False}
    EM={"valid":False}
    MW={"valid":False}
    md_active=False; md_done=False; md_cnt=0; md_is_div=False; md_is_lane1=False; md_a=0; md_b=0; md_res=0

    for cyc in range(1, max_cyc+1):
        md_done=False
        # COMBINATIONAL: forward
        f0_0=DE.get("v0_0",0); f0_1=DE.get("v0_1",0); f1_0=DE.get("v1_0",0); f1_1=DE.get("v1_1",0)
        if MW.get("valid"):
            if MW.get("wen0") and MW["rd0"]!=0:
                v = MW["mem"] if MW.get("isload") else MW["alu0"]
                if MW["rd0"]==DE.get("s0_0",0): f0_0=v
                if MW["rd0"]==DE.get("s0_1",0): f0_1=v
                if MW["rd0"]==DE.get("s1_0",0): f1_0=v
                if MW["rd0"]==DE.get("s1_1",0): f1_1=v
            if MW.get("wen1") and MW.get("rd1",0)!=0:
                v=MW["alu1"]
                if MW["rd1"]==DE.get("s0_0",0): f0_0=v
                if MW["rd1"]==DE.get("s0_1",0): f0_1=v
                if MW["rd1"]==DE.get("s1_0",0): f1_0=v
                if MW["rd1"]==DE.get("s1_1",0): f1_1=v
        if EM.get("valid"):
            if EM["rd0"]!=0 and EM["op0"] not in (OP_STORE,OP_NOP,OP_LOAD):
                v=EM["alu0"]
                if EM["rd0"]==DE.get("s0_0",0): f0_0=v
                if EM["rd0"]==DE.get("s0_1",0): f0_1=v
                if EM["rd0"]==DE.get("s1_0",0): f1_0=v
                if EM["rd0"]==DE.get("s1_1",0): f1_1=v
            if EM.get("rd1",0)!=0 and EM.get("op1",0) not in (OP_STORE,OP_NOP,OP_LOAD) and EM.get("op1") is not None:
                v=EM["alu1"]
                if EM["rd1"]==DE.get("s0_0",0): f0_0=v
                if EM["rd1"]==DE.get("s0_1",0): f0_1=v
                if EM["rd1"]==DE.get("s1_0",0): f1_0=v
                if EM["rd1"]==DE.get("s1_1",0): f1_1=v

        # EX outputs
        alu0_out = alu(DE.get("op0",OP_NOP),f0_0,f0_1,DE.get("imm0",0)) if DE.get("valid") else 0
        alu1_out = alu(DE.get("op1",OP_NOP),f1_0,f1_1,DE.get("imm1",0)) if DE.get("valid") else 0
        alu0_zero = (alu0_out==0)

        br_taken=False; br_target=0; halted=False
        if DE.get("valid"):
            op0=DE["op0"]
            if op0==OP_JMP: br_target=DE["imm0"]; br_taken=True
            elif op0==OP_JZ: br_target=DE["imm0"]; br_taken=alu0_zero
            elif op0==OP_JNZ: br_target=DE["imm0"]; br_taken=not alu0_zero
            elif op0==OP_JAL: br_target=DE["imm0"]; br_taken=True
            elif op0==OP_CALL: br_target=DE["imm0"]; br_taken=True
            elif op0==OP_RET: br_target=f0_0; br_taken=True
            if br_taken and op0==OP_JMP and br_target==DE.get("pc",0):
                halted=True   # 自跳 JMP = halt 惯用法

        # MUL/DIV
        md_just_started=False
        if not md_active and DE.get("valid"):
            if DE.get("dual") and DE.get("op1",0) in (OP_MUL,OP_DIV):
                md_active=True; md_is_lane1=True; md_is_div=(DE["op1"]==OP_DIV)
                md_a=f1_0; md_b=f1_1; md_cnt=8 if md_is_div else 4
                md_just_started=True
            elif DE.get("op0") in (OP_MUL,OP_DIV):
                md_active=True; md_is_lane1=False; md_is_div=(DE["op0"]==OP_DIV)
                md_a=f0_0; md_b=f0_1; md_cnt=8 if md_is_div else 4
                md_just_started=True
        if md_active and not md_just_started:
            if md_cnt>1: md_cnt-=1
            else:
                md_active=False; md_done=True
                md_res = (md_a//md_b if md_b!=0 else 0) if md_is_div else md_a*md_b
                md_res &= 0xFFFFFFFF

        lane0_final = md_res if (not md_active and md_done and not md_is_lane1) else alu0_out
        lane1_final = (md_res if (not md_active and md_done and md_is_lane1) else
                       (0 if (DE.get("valid") and DE.get("dual") and DE.get("op1",0) in (OP_MUL,OP_DIV)) else alu1_out))
        lane1_wen = (DE.get("valid") and DE.get("dual") and DE.get("op1",0) not in (OP_STORE,OP_NOP,OP_EMIT) and DE.get("rd1",0)!=0) or (md_done and md_is_lane1)

        # DE 保持期间(等待取指/MUL执行)冻结 EM/MW, 防止同一指令被重复推进执行
        de_kept = md_active or (not br_taken and not FD.get("valid", False) and not md_done)

        # SEQUENTIAL: WB
        if MW.get("valid"):
            if MW.get("wen0") and MW["rd0"]!=0:
                wb0 = MW["mem"] if MW.get("isload") else (MW["pc"]+8 if MW["op0"] in (OP_JAL,OP_CALL) else MW["alu0"])
                rf[MW["rd0"]]=wb0&0xFFFFFFFF
            if MW.get("wen1") and MW.get("rd1",0)!=0 and not (MW.get("wen0") and MW["rd0"]!=0 and MW["rd0"]==MW["rd1"]):
                wb1 = (MW["pc"]+8 if MW.get("op1",0) in (OP_JAL,OP_CALL) else MW["alu1"])
                rf[MW.get("rd1")]=wb1&0xFFFFFFFF

        # Detect halt: any JMP that loops to self or falls into NOP zone
        # Heuristic for Σ: STORE dmem[0] is final; once STORE hits dmem[0] we can stop
        # But for correct behavior, use cycle limit (like testbench)

        # SEQUENTIAL: MW <- EM
        nMW={"valid":False}
        if de_kept:
            nMW = MW
        elif EM.get("valid"):
            wen1 = (EM.get("dual") and EM.get("op1",0) not in (OP_STORE,OP_NOP,OP_EMIT) and EM.get("rd1",0)!=0) or (md_done and EM.get("dual"))
            wen0 = (EM["op0"] not in (OP_STORE,OP_NOP,OP_EMIT) and EM.get("rd0",0)!=0)
            if EM["op0"]==OP_STORE:
                dmem[EM["alu0"]%4096]=EM.get("rs2",0)&0xFFFFFFFF
                nMW={"valid":True,"op0":OP_NOP,"op1":EM.get("op1",0),
                     "alu0":EM["alu0"],"alu1":EM["alu1"],"rd0":0,"rd1":EM.get("rd1",0),
                     "wen0":0,"wen1":wen1,"isload":False,"mem":0,"pc":EM.get("pc",0)}
            elif EM["op0"]==OP_LOAD:                nMW={"valid":True,"op0":EM["op0"],"op1":EM.get("op1",0),
                     "alu0":EM["alu0"],"alu1":EM["alu1"],"rd0":EM["rd0"],"rd1":EM.get("rd1",0),
                     "wen0":1,"wen1":wen1,"isload":True,"mem":dmem[EM["alu0"]%4096],"pc":EM.get("pc",0)}
            else:
                nMW={"valid":True,"op0":EM["op0"],"op1":EM.get("op1",0),
                     "alu0":EM["alu0"],"alu1":EM["alu1"],"rd0":EM["rd0"],"rd1":EM.get("rd1",0),
                     "wen0":wen0,"wen1":wen1,"isload":False,"mem":0,"pc":EM.get("pc",0)}
        MW=nMW

        # SEQUENTIAL: EM <- DE (with md_res applied)
        nEM={"valid":False}
        if de_kept:
            nEM = EM
        elif DE.get("valid"):
            rd0 = 1 if DE["op0"] in (OP_JAL,OP_CALL) else DE.get("rd0",0)
            rd1 = 1 if DE.get("op1",0) in (OP_JAL,OP_CALL) else DE.get("rd1",0)
            wen0 = int(DE["op0"] not in (OP_STORE,OP_NOP,OP_EMIT) and rd0!=0)
            wen1 = int(DE.get("dual") and DE.get("op1",0) not in (OP_STORE,OP_NOP,OP_EMIT) and rd1!=0)
            nEM={"valid":True,"op0":DE["op0"],"op1":DE.get("op1",0),
                 "alu0":lane0_final,"alu1":lane1_final,"rd0":rd0,"rd1":rd1,
                 "rs2":f0_1,"dual":DE.get("dual",False),"pc":DE.get("pc",0),
                 "wen0":wen0,"wen1":wen1}
        EM=nEM

        # SEQUENTIAL: DE <- FD (保持/清空/新指令)
        # DE 是流水寄存器: 无新指令时保持, MUL/DIV 期间保持, flush 时清空
        nDE={"valid":False}
        if br_taken:
            pc_reg = br_target & 0xFFFFFFFF
            fetch_idle = True
            fd_inflight = False
            FD={"valid":False}
        elif md_active:
            nDE = DE        # MUL/DIV 执行期间保持 DE
        elif FD.get("valid"):
            op0,rd0,s0_0,s0_1,imm0=dec(FD["i0"])
            op1,rd1,s1_0,s1_1,imm1=dec(FD["i1"])
            pair = can_pair(op0,rd0,s0_0,s0_1,op1,rd1,s1_0,s1_1) and not md_active
            nDE={"valid":True,"pc":FD.get("pc",0),"dual":pair,
                 "op0":op0,"rd0":rd0,"s0_0":s0_0,"s0_1":s0_1,"imm0":imm0,
                 "v0_0":rf[s0_0],"v0_1":rf[s0_1]}
            if pair:
                nDE["op1"]=op1; nDE["rd1"]=rd1; nDE["s1_0"]=s1_0; nDE["s1_1"]=s1_1; nDE["imm1"]=imm1
                nDE["v1_0"]=rf[s1_0]; nDE["v1_1"]=rf[s1_1]
            else:
                nDE["op1"]=OP_NOP; nDE["rd1"]=0; nDE["s1_0"]=0; nDE["s1_1"]=0; nDE["imm1"]=0
                nDE["v1_0"]=0; nDE["v1_1"]=0
            FD={"valid":False}
        elif md_done:
            nDE={"valid":False}     # MUL/DIV 结果已锁存进 EM, 清空 DE 防重复锁存覆盖
        else:
            nDE = DE                # 无新指令: 保持 DE
        DE=nDE

        # SEQUENTIAL: FD <- IF (Wishbone: 发出取指 1 周期, ack 下周期到达 => 每 2 周期取一次)
        if not md_active and not br_taken:
            if fd_inflight:
                adr = fd_adr
                i0 = flat[(adr//4)%len(flat)] if flat else 0
                i1 = flat[((adr//4)+1)%len(flat)] if flat else 0
                FD={"valid":True,"i0":i0,"i1":i1,"pc":adr}
                fetch_idle = True
                fd_inflight = False
                pc_reg = (adr + 8) & 0xFFFFFFFF
            elif fetch_idle:
                fd_adr = pc_reg
                fetch_idle = False
                fd_inflight = True

        # halt: 自跳 JMP 即停机, 提前返回实际周期
        if halted:
            return dmem, cyc

    return dmem, max_cyc

if __name__ == "__main__":
    for fn, exp, desc in [
        ("prog_sigma_100.hex", 5050, "Σ(1..100)"),
        ("prog_mul.hex", 425, "25*17"),
        ("prog_div.hex", 76, "1000/13"),
        ("prog_logic.hex", (100, 105), "logic ops (dmem[0]=100,dmem[4]=105)"),
    ]:
        dmem, cyc = sim(fn)
        if isinstance(exp, tuple):
            ok = dmem[0] == exp[0] and dmem[4] == exp[1]
            res = f"dmem[0]={dmem[0]} dmem[4]={dmem[4]}"
        else:
            ok = dmem[0] == exp
            res = f"dmem[0]={dmem[0]}"
        status = "PASS" if ok else "FAIL"
        print(f"[{status}] {desc}: {res} expected={exp} cycles={cyc}")
