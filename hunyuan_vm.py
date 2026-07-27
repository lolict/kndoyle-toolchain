#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混元解释器 v0.1 (HunYuan VM)
================================
概念映射（形式化框架 → 工程实现）：

  64进制数字        = 大齿轮的一齿（每齿 6 bit，齿轮比 6:1）
  瓦片 Tile         = 254B 负载（子涵，内部） + 2B 外部寄存（阴/阳） = 256 = 2^8（补足律）
  三元组块 Group    = 3 瓦片对齐：762B 负载 = 1016 个 64 进制数字（对齐律 lcm(8,6)=24bit）
  克隆填充          = 瓦片自相似克隆填满 3D 张量网格 I×J×K（克隆残差律）
  阴阳寄存器        = 瓦片第 254/255 号码位，外置命名，不进位、不占内部空间（不进位律）
  ⟦·⟧_ours         = 本文件定义的求值函子；不借用系统语义（架空律：硬件只是电平基底）
  拔插式操作码表    = OPS 表可随时整体替换为文档版本（同型可替换律）

指令编码：每条指令 = 1 个 64 进制数字的操作码 + 0~4 个数字的操作数。
"""

import time

# ---------------------------------------------------------------- 进制层
ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ+/"
assert len(ALPHABET) == 64

TILE_PAYLOAD = 254          # 子涵：内部负载字节数
TILE_EXT     = 2            # 阴/阳：外部寄存字节数
TILE_SIZE    = 256          # 补足律：254 ⊎ 2 = 256 = 2^8
GROUP_TILES  = 3            # 三瓦片成组
GROUP_PAYLOAD = TILE_PAYLOAD * GROUP_TILES          # 762 B
GROUP_DIGITS  = GROUP_PAYLOAD * 8 // 6              # 1016 digits（整除，无残齿）

YIN_BYTE, YANG_BYTE = 254, 255   # 闲置码位外置命名：254号=阴，255号=阳

assert TILE_PAYLOAD + TILE_EXT == TILE_SIZE == 2 ** 8, "补足律不成立"
assert GROUP_PAYLOAD * 8 == GROUP_DIGITS * 6, "对齐律不成立"


def digits_to_tiles(digits):
    """64进制数字流 → 瓦片列表（每片 256B：254B 负载 + 阴/阳两字节）。"""
    ds = list(digits)
    pad = (-len(ds)) % GROUP_DIGITS
    ds += [0] * pad                      # 残差以 0 齿填充，计入填充纹
    payload = bytearray()
    bits = nbits = 0
    for d in ds:
        bits = (bits << 6) | d
        nbits += 6
        while nbits >= 8:
            nbits -= 8
            payload.append((bits >> nbits) & 0xFF)
    assert nbits == 0 and len(payload) % GROUP_PAYLOAD == 0
    tiles = []
    for g in range(len(payload) // GROUP_PAYLOAD):
        base = g * GROUP_PAYLOAD
        for t in range(GROUP_TILES):
            tile = bytearray(TILE_SIZE)
            tile[:TILE_PAYLOAD] = payload[base + t * TILE_PAYLOAD: base + (t + 1) * TILE_PAYLOAD]
            tile[TILE_PAYLOAD]     = YIN_BYTE    # 阴寄存器（外置，不参与内部进位）
            tile[TILE_PAYLOAD + 1] = YANG_BYTE   # 阳寄存器（外置，不参与内部进位）
            tiles.append(tile)
    return tiles, pad


def tiles_to_digits(tiles):
    """瓦片列表 → 64进制数字流（只读负载区，阴阳字节留在语义链之外）。"""
    payload = bytearray()
    for tile in tiles:
        payload += tile[:TILE_PAYLOAD]
    digits, bits, nbits = [], 0, 0
    for b in payload:
        bits = (bits << 8) | b
        nbits += 8
        while nbits >= 6:
            nbits -= 6
            digits.append((bits >> nbits) & 0x3F)
    return digits


def clone_fill(tiles, dims):
    """克隆填充律：瓦片自相似克隆，填满 3D 张量网格 I×J×K。"""
    gx, gy, gz = dims
    slots = gx * gy * gz
    grid = [tiles[i % len(tiles)] for i in range(slots)]
    report = {
        "网格": f"{gx}×{gy}×{gz} = {slots} 槽",
        "整组克隆": slots // len(tiles),
        "残差克隆": slots % len(tiles),          # 不足一组的部分由克隆体补满
        "内部单元": slots * TILE_PAYLOAD,
        "阴阳寄存": slots * TILE_EXT,
        "补足校验": f"254 ⊎ 2 = 256 = 2^8 ✓" if TILE_PAYLOAD + TILE_EXT == 2 ** 8 else "✗",
    }
    return grid, report


# ---------------------------------------------------------------- 指令层（拔插式操作码表）
#        操作码: (码值, 操作数位数)
OPS = {
    "HALT":  (0, 0),
    "PUSH":  (1, 1),   # 压入 1 位立即数 (0..63)
    "PUSH2": (2, 2),   # 压入 2 位立即数 (0..4095)
    "ADD":   (3, 0), "SUB": (4, 0), "MUL": (5, 0), "DIV": (6, 0), "MOD": (7, 0),
    "DUP":   (8, 0), "DROP": (9, 0), "SWAP": (10, 0), "OVER": (11, 0),
    "PRINT": (12, 0),
    "JMP":   (13, 2), "JZ": (14, 2), "JNZ": (15, 2),
    "STORE": (16, 2), "LOAD": (17, 2),       # 2 位地址 → 4096 个内存格
    "YIN":   (18, 0), "YANG": (19, 0),       # 弹栈 → 阴/阳寄存器（外部统计）
    "PUSH3": (21, 3),                        # 0..262143
    "PUSH4": (22, 4),                        # 0..16777215
}


def assemble(program):
    """两趟汇编：('LABEL',名) 声明标签，('OP', 操作数...) 发射数字流。"""
    addr, pos = {}, 0
    for item in program:
        if isinstance(item, str):
            item = (item,)
        if item[0] == "LABEL":
            addr[item[1]] = pos
        else:
            pos += 1 + OPS[item[0]][1]
    code = []
    for item in program:
        if isinstance(item, str):
            item = (item,)
        if item[0] == "LABEL":
            continue
        op, operands = item[0], item[1:]
        code.append(OPS[op][0])
        if op in ("JMP", "JZ", "JNZ"):
            a = addr[operands[0]]
            code += [a // 64, a % 64]
        elif op in ("STORE", "LOAD"):
            c = operands[0]
            code += [c // 64, c % 64]
        elif op == "PUSH":
            code.append(operands[0] & 0x3F)
        elif op == "PUSH2":
            v = operands[0]; code += [(v >> 6) & 0x3F, v & 0x3F]
        elif op == "PUSH3":
            v = operands[0]; code += [(v >> 12) & 0x3F, (v >> 6) & 0x3F, v & 0x3F]
        elif op == "PUSH4":
            v = operands[0]
            code += [(v >> 18) & 0x3F, (v >> 12) & 0x3F, (v >> 6) & 0x3F, v & 0x3F]
    return code


# ---------------------------------------------------------------- 求值层 ⟦·⟧_ours
def run(code, max_steps=300_000_000):
    """混元求值函子：语义权威只属于本函数（架空律）。"""
    stack, mem = [], [0] * 4096
    ip, n, steps = 0, len(code), 0
    out, yin, yang = [], 0, 0
    while ip < n:
        op = code[ip]; ip += 1; steps += 1
        if steps > max_steps:
            raise RuntimeError("步数超限")
        if op == 17:                                   # LOAD
            stack.append(mem[code[ip] * 64 + code[ip + 1]]); ip += 2
        elif op == 14:                                 # JZ
            a = code[ip] * 64 + code[ip + 1]; ip += 2
            if stack.pop() == 0:
                ip = a
        elif op == 16:                                 # STORE
            mem[code[ip] * 64 + code[ip + 1]] = stack.pop(); ip += 2
        elif op == 1:                                  # PUSH
            stack.append(code[ip]); ip += 1
        elif op == 2:                                  # PUSH2
            stack.append(code[ip] * 64 + code[ip + 1]); ip += 2
        elif op == 22:                                 # PUSH4
            stack.append(((code[ip] * 64 + code[ip + 1]) * 64 + code[ip + 2]) * 64 + code[ip + 3])
            ip += 4
        elif op == 3:                                  # ADD
            b = stack.pop(); stack.append(stack.pop() + b)
        elif op == 4:                                  # SUB
            b = stack.pop(); stack.append(stack.pop() - b)
        elif op == 5:                                  # MUL
            b = stack.pop(); stack.append(stack.pop() * b)
        elif op == 6:                                  # DIV
            b = stack.pop(); stack.append(stack.pop() // b)
        elif op == 7:                                  # MOD
            b = stack.pop(); stack.append(stack.pop() % b)
        elif op == 13:                                 # JMP
            ip = code[ip] * 64 + code[ip + 1]
        elif op == 15:                                 # JNZ
            a = code[ip] * 64 + code[ip + 1]; ip += 2
            if stack.pop() != 0:
                ip = a
        elif op == 8:                                  # DUP
            stack.append(stack[-1])
        elif op == 9:                                  # DROP
            stack.pop()
        elif op == 10:                                 # SWAP
            stack[-1], stack[-2] = stack[-2], stack[-1]
        elif op == 11:                                 # OVER
            stack.append(stack[-2])
        elif op == 12:                                 # PRINT
            out.append(stack.pop())
        elif op == 18:                                 # YIN
            yin = stack.pop()
        elif op == 19:                                 # YANG
            yang = stack.pop()
        elif op == 0:                                  # HALT
            break
        else:
            raise RuntimeError(f"未知操作码 {op} @ {ip - 1}")
    return {"steps": steps, "out": out, "yin": yin, "yang": yang, "stack": stack}


# ---------------------------------------------------------------- 演示程序
def program_sum(n):
    """累加 1..n，结束时把 254 存入阴、2 存入阳（里应外合统计）。"""
    return assemble([
        ("PUSH2", 0), ("STORE", 0),          # mem[0] = acc
        ("PUSH4", n), ("STORE", 1),          # mem[1] = 计数 c
        ("LABEL", "loop"),
        ("LOAD", 1), ("JZ", "end"),
        ("LOAD", 0), ("LOAD", 1), ("ADD"), ("STORE", 0),
        ("LOAD", 1), ("PUSH", 1), ("SUB"), ("STORE", 1),
        ("JMP", "loop"),
        ("LABEL", "end"),
        ("LOAD", 0), ("PRINT"),
        ("PUSH2", 254), ("YIN"),
        ("PUSH2", 2), ("YANG"),
        ("HALT",),
    ])


def native_sum(n):
    acc, c = 0, n
    while c:
        acc += c
        c -= 1
    return acc


# ---------------------------------------------------------------- 主流程
def main():
    print("=" * 60)
    print("混元解释器 v0.1 —— 64进制高维指令流 · 瓦片克隆填充 · 阴阳补足")
    print("=" * 60)

    # 1) 装载层：汇编 → 数字流 → 瓦片 → 3D 网格克隆填充
    code = program_sum(100)
    tiles, pad = digits_to_tiles(code)
    grid, rep = clone_fill(tiles, (2, 2, 2))
    print(f"\n[装载] 程序 {len(code)} 齿 → {len(tiles)} 瓦片（填充纹 {pad} 齿）")
    for k, v in rep.items():
        print(f"       {k}: {v}")

    # 2) 求值层：从网格读回数字流，由自有解释器执行
    code2 = tiles_to_digits(grid[0:0 + len(tiles)])[:len(code)]
    t0 = time.perf_counter()
    res = run(code2)
    t1 = time.perf_counter()
    ok = res["out"] == [5050] and res["yin"] == 254 and res["yang"] == 2
    print(f"\n[求值] Σ(1..100) = {res['out'][0]}  阴={res['yin']} 阳={res['yang']}  "
          f"步数={res['steps']}  耗时={(t1 - t0) * 1e3:.2f} ms  语义校验 {'✓' if ok else '✗'}")

    # 3) 基准测试：混元 VM vs 原生 Python
    N = 1_000_000
    bench = program_sum(N)
    t0 = time.perf_counter(); r1 = run(bench); t1 = time.perf_counter()
    vm_t = t1 - t0
    t0 = time.perf_counter(); r2 = native_sum(N); t1 = time.perf_counter()
    py_t = t1 - t0
    assert r1["out"][0] == r2, "结果不一致！"
    print(f"\n[基准] 任务: Σ(1..{N})，两侧结果一致 = {r2}")
    print(f"       混元VM : {vm_t:7.3f} s   {r1['steps'] / vm_t / 1e6:6.2f} M齿/s   ({r1['steps']:,} 齿)")
    print(f"       原生Py : {py_t:7.3f} s   {N * 2 / py_t / 1e6:6.2f} Mop/s")
    print(f"       速度比 : VM 约为原生 Python 的 {py_t / vm_t:.1%}（慢 {vm_t / py_t:.0f} 倍）")
    print(f"       参照   : 原生 C 约 1e9 op/s 量级 → 当前 VM 与芯片直跑差约 2~3 个数量级")
    print(f"       出路   : JIT 把热路径编译成原生码（WASM/HotSpot 路线），可追到接近原生")


if __name__ == "__main__":
    main()
