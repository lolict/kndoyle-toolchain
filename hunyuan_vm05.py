#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混元虚拟机 v0.5 (HunYuan VM) —— 可栖居的机体
===========================================================
v0.3 有运算 + 关系查询；v0.5 给 VM 装上"身体"：

新增指令族（op 36..60）：
  感知族：36 SENSE  37 EMIT
  调用族：38 CALL   39 RET
  堆族：  40 HPALLOC  41 HPLOAD  42 HPSTORE  43 HPFREE
  通道族：44 CHOPEN  45 CHSEND  46 CHRECV  47 CHCLOSE
  设备族：48 DEVOPEN  49 DEVCAP  50 DEVIO  51 DEVCLOSE
  网络族：52 NETLISTEN  53 NETACCEPT  54 NETDIAL  55 NETSEND  56 NETRECV  57 NETCLOSE
  时钟族：58 TICK  59 DELAY  60 TIMER

机器状态（run 返回的完整状态）：
  out       输出行列表
  steps     执行步数
  stack     数据栈终态
  yin/yang  阴阳寄存器
  perception 感知总线 {sensors, actuators}
  heap      堆 {mem, next}
  channels  通道表
  devices   设备表
  net       网络 {listeners, connections, next_conn}
  clock     时钟 {tick, timers}
"""

import sys
from collections import defaultdict, deque

# ---- 关系引擎 ----
REL_FLOW = {"助力": -1, "资助": -1, "消耗": +1, "抽取": +1}


class 字典集:
    def __init__(self):
        self.members = {}
        self.edges = []

    def 入驻(self, name, 范畴="未分", 层级=0, 态="流动"):
        self.members[name] = {"范畴": 范畴, "层级": 层级, "态": 态}

    def 关联(self, a, rel, b, w=1.0):
        self.edges.append((a, rel, b, w))

    def 关系族(self, name, depth=2):
        adj = defaultdict(list)
        for a, rel, b, w in self.edges:
            adj[a].append((rel, b))
        seen, out, q = {name}, [], deque([(name, 0)])
        while q:
            u, d = q.popleft()
            if d >= depth:
                continue
            for rel, v in adj[u]:
                out.append(f"{u} —{rel}→ {v}")
                if v not in seen:
                    seen.add(v)
                    q.append((v, d + 1))
        return out


class 评判引擎:
    def __init__(self, dic):
        self.dic, self.nodes = dic, list(dic.members)
        self.adj, self.und = defaultdict(list), defaultdict(list)
        for a, rel, b, w in dic.edges:
            self.adj[a].append(b)
            self.und[a].append(b); self.und[b].append(a)

    def 可达集(self, s):
        seen, q = {s}, deque([s])
        while q:
            u = q.popleft()
            for v in self.adj[u]:
                if v not in seen: seen.add(v); q.append(v)
        return seen

    def 能回归(self, g): return {n for n in self.nodes if g in self.可达集(n) and n != g}
    def 死胡同(self, g): return {n for n in self.nodes if g not in self.可达集(n) and n != g}
    def 目标集(self): return {b for a, r, b, _ in self.dic.edges if r == "意图"}
    def 是目标(self, n): return n in self.目标集()

    def 割点(self):
        idx, low, cut, t = {}, {}, set(), [0]
        def dfs(u, p):
            idx[u] = low[u] = t[0]; t[0] += 1; ch = 0
            for v in self.und[u]:
                if v not in idx:
                    ch += 1; dfs(v, u); low[u] = min(low[u], low[v])
                    if p is not None and low[v] >= idx[u]: cut.add(u)
                elif v != p: low[u] = min(low[u], idx[v])
            if p is None and ch > 1: cut.add(u)
        for n in self.nodes:
            if n not in idx: dfs(n, None)
        return cut

    def 注意力(self):
        s = defaultdict(float)
        for a, r, b, w in self.dic.edges:
            if r == "注意": s[b] += w
        return s

    def 信任(self):
        s = defaultdict(float)
        for a, r, b, w in self.dic.edges:
            if r == "信任": s[b] += w
        return s

    def 净账(self):
        a = defaultdict(float)
        for x, r, y, w in self.dic.edges:
            if r in REL_FLOW: a[x] += REL_FLOW[r]*w; a[y] -= REL_FLOW[r]*w
        return a

    def 分歧(self, n):
        d = len(set(self.adj[n]))
        return 2 if d >= 2 else (1 if d == 1 else 0)

    def 等效类(self):
        s = defaultdict(list)
        for n in self.nodes:
            o = tuple(sorted(r for a, r, b, _ in self.dic.edges if a == n))
            i = tuple(sorted("←"+r for a, r, b, _ in self.dic.edges if b == n))
            s[(o, i)].append(n)
        classes = {n: len(c) for c in s.values() if len(c) > 1 for n in c}
        return classes


# ---- 操作码表 ----
OPS = {
    # 基础运算 (v0.1)
    "HALT": (0, 0), "PUSH": (1, 1), "PUSH2": (2, 2),
    "ADD": (3, 0), "SUB": (4, 0), "MUL": (5, 0), "DIV": (6, 0),
    "DUP": (7, 0), "DROP": (8, 0), "SWAP": (9, 0), "OVER": (10, 0),
    "LOAD": (17, 2), "STORE": (16, 2), "JZ": (14, 2), "JMP": (13, 2),
    "YIN": (18, 0), "YANG": (19, 0), "PRINT": (12, 0),
    # 关系族 (v0.3)
    "REL_SET": (23, 1), "REL_CAN": (24, 1), "REL_CUT": (25, 0),
    "REL_NET": (26, 0), "REL_TRUST": (27, 0), "REL_ATTEN": (28, 0),
    "REL_SOLID": (29, 0), "REL_DEAD": (30, 0), "REL_GOAL": (31, 0),
    "REL_DIFF": (32, 0), "REL_EQUIV": (33, 0), "REL_FAMILY": (34, 0),
    "REL_OUTSTR": (35, 1),
    # 感知族 (v0.5)
    "SENSE": (36, 1), "EMIT": (37, 1),
    # 调用族 (v0.5)
    "CALL": (38, 2), "RET": (39, 0),
    # 堆族 (v0.5)
    "HPALLOC": (40, 1), "HPLOAD": (41, 0), "HPSTORE": (42, 0), "HPFREE": (43, 0),
    # 通道族 (v0.5)
    "CHOPEN": (44, 1), "CHSEND": (45, 0), "CHRECV": (46, 0), "CHCLOSE": (47, 0),
    # 设备族 (v0.5)
    "DEVOPEN": (48, 1), "DEVCAP": (49, 0), "DEVIO": (50, 0), "DEVCLOSE": (51, 0),
    # 网络族 (v0.5)
    "NETLISTEN": (52, 1), "NETACCEPT": (53, 0), "NETDIAL": (54, 1),
    "NETSEND": (55, 0), "NETRECV": (56, 0), "NETCLOSE": (57, 0),
    # 时钟族 (v0.5)
    "TICK": (58, 0), "DELAY": (59, 0), "TIMER": (60, 0),
}


def assemble(program):
    """汇编：程序（含 LABEL）→ 字节码。"""
    addr, pos = {}, 0
    for item in program:
        if isinstance(item, str): item = (item,)
        if item[0] == "LABEL":
            addr[item[1]] = pos
        else:
            pos += 1 + OPS[item[0]][1]
    code = []
    for item in program:
        if isinstance(item, str): item = (item,)
        if item[0] == "LABEL": continue
        op, ops = item[0], item[1:]
        code.append(OPS[op][0])
        if op in ("JMP", "JZ", "CALL"):
            a = addr[ops[0]]; code += [a // 64, a % 64]
        elif op in ("STORE", "LOAD"):
            code += [ops[0] // 64, ops[0] % 64]
        elif op == "PUSH":
            code.append(ops[0] & 0x3F)
        elif op == "PUSH2":
            v = ops[0]; code += [(v >> 6) & 0x3F, v & 0x3F]
        elif op in ("REL_SET", "REL_CAN", "REL_OUTSTR",
                     "SENSE", "EMIT", "HPALLOC", "CHOPEN",
                     "DEVOPEN", "NETLISTEN", "NETDIAL"):
            code.append(ops[0] & 0x3F)
    return code


def run(program, context, labels, subject="自己",
        perception=None, heap=None, channels=None,
        devices=None, net=None, clock=None):
    """
    混元 v0.5 求值器。

    参数:
      program     汇编程序（元组/字符串列表）
      context     字典集（关系上下文）
      labels      文本标签列表
      subject     当前主体名称
      perception  感知总线 {"sensors": {id: value}, "actuators": {id: value}}
      heap        堆 {"mem": {ptr: value}, "next": int}
      channels    通道表 {ch_id: {"buf": [...]}}
      devices     设备表 {dev_id: {"caps": int, "open": bool, "state": any}}
      net         网络 {"listeners": {}, "connections": {}, "next_conn": int}
      clock       时钟 {"tick": int, "timers": [(cb_addr, interval, last_fire)]}

    返回:
      dict 含 out, steps, stack, yin, yang, 以及所有机器状态。
    """
    code = assemble(program)
    engine = 评判引擎(context)
    names = list(context.members)
    subj = subject
    cut_set = engine.割点()
    net_balance = engine.净账()
    trust = engine.信任()
    atten = engine.注意力()
    equiv = engine.等效类()
    goals = engine.目标集()
    member = context.members

    # ---- 初始化机器状态 ----
    if perception is None: perception = {"sensors": {}, "actuators": {}}
    if heap is None: heap = {"mem": {}, "next": 0}
    if channels is None: channels = {}
    if devices is None: devices = {}
    if net is None: net = {"listeners": {}, "connections": {}, "next_conn": 1000}
    if clock is None: clock = {"tick": 0, "timers": []}

    stack, mem, out = [], [0] * 4096, []
    call_stack = []
    ip, n, steps = 0, len(code), 0
    yin, yang = 0, 0

    def cur(name):
        return {
            "net": int(round(net_balance.get(name, 0) * 10)),
            "trust": int(round(trust.get(name, 0) * 10)),
            "atten": int(round(atten.get(name, 0) * 10)),
            "solid": 1 if member[name]["态"] == "固态" else 0,
            "cut": 1 if name in cut_set else 0,
            "goal": 1 if engine.是目标(name) else 0,
            "diff": engine.分歧(name),
            "equiv": equiv.get(name, 1),
        }

    while ip < n:
        op = code[ip]; ip += 1; steps += 1
        clock["tick"] += 1

        # ---- 基础运算 ----
        if op == 0: break
        elif op == 1: stack.append(code[ip]); ip += 1
        elif op == 7: stack.append(stack[-1])                           # DUP
        elif op == 8: stack.pop()                                        # DROP
        elif op == 9: stack[-1], stack[-2] = stack[-2], stack[-1]        # SWAP
        elif op == 10: stack.append(stack[-2])                           # OVER
        elif op == 2: stack.append(code[ip]*64+code[ip+1]); ip += 2      # PUSH2
        elif op == 3: b=stack.pop(); stack.append(stack.pop()+b)
        elif op == 4: b=stack.pop(); stack.append(stack.pop()-b)
        elif op == 5: b=stack.pop(); stack.append(stack.pop()*b)
        elif op == 6: b=stack.pop(); stack.append(stack.pop()//b)
        elif op == 12: out.append(str(stack.pop()))
        elif op == 13: ip = code[ip]*64+code[ip+1]
        elif op == 14:
            a = code[ip]*64+code[ip+1]; ip += 2
            if stack.pop() == 0: ip = a
        elif op == 16: mem[code[ip]*64+code[ip+1]] = stack.pop(); ip += 2
        elif op == 17: stack.append(mem[code[ip]*64+code[ip+1]]); ip += 2
        elif op == 18: yin = stack.pop()
        elif op == 19: yang = stack.pop()

        # ---- 关系族 ----
        elif op == 23: subj = names[code[ip]]; ip += 1
        elif op == 24:
            tgt = names[code[ip]]; ip += 1
            stack.append(1 if tgt in engine.可达集(subj) else 0)
        elif op == 25: stack.append(cur(subj)["cut"])
        elif op == 26: stack.append(cur(subj)["net"])
        elif op == 27: stack.append(cur(subj)["trust"])
        elif op == 28: stack.append(cur(subj)["atten"])
        elif op == 29: stack.append(cur(subj)["solid"])
        elif op == 30: stack.append(1 if subj in engine.死胡同(list(goals)[0] if goals else "") else 0)
        elif op == 31: stack.append(cur(subj)["goal"])
        elif op == 32: stack.append(cur(subj)["diff"])
        elif op == 33: stack.append(cur(subj)["equiv"])
        elif op == 34:
            for line in context.关系族(subj):
                out.append(line)
        elif op == 35: out.append(labels[code[ip]]); ip += 1

        # ---- 感知族 v0.5 ----
        elif op == 36:  # SENSE
            sid = code[ip]; ip += 1
            stack.append(perception["sensors"].get(sid, 0))
        elif op == 37:  # EMIT
            aid = code[ip]; ip += 1
            perception["actuators"][aid] = stack.pop()

        # ---- 调用族 v0.5 ----
        elif op == 38:  # CALL
            a = code[ip]*64+code[ip+1]; ip += 2
            call_stack.append(ip)
            ip = a
        elif op == 39:  # RET
            ip = call_stack.pop()

        # ---- 堆族 v0.5 ----
        elif op == 40:  # HPALLOC
            size = code[ip]; ip += 1
            ptr = heap["next"]
            for i in range(size):
                heap["mem"][ptr + i] = 0
            heap["next"] += size
            stack.append(ptr)
        elif op == 41:  # HPLOAD
            ptr = stack.pop()
            stack.append(heap["mem"].get(ptr, 0))
        elif op == 42:  # HPSTORE
            val = stack.pop(); ptr = stack.pop()
            heap["mem"][ptr] = val
        elif op == 43:  # HPFREE
            ptr = stack.pop()
            if ptr in heap["mem"]: heap["mem"][ptr] = 0

        # ---- 通道族 v0.5 ----
        elif op == 44:  # CHOPEN
            ch_id = code[ip]; ip += 1
            channels[ch_id] = {"buf": []}
            stack.append(ch_id)
        elif op == 45:  # CHSEND（不消耗句柄：val 在顶，句柄在次）
            val = stack.pop(); ch_id = stack[-1]
            if ch_id in channels: channels[ch_id]["buf"].append(val)
        elif op == 46:  # CHRECV（不消耗句柄）
            ch_id = stack[-1]
            if ch_id in channels and channels[ch_id]["buf"]:
                stack.append(channels[ch_id]["buf"].pop(0))
            else:
                stack.append(0)
        elif op == 47:  # CHCLOSE
            ch_id = stack.pop()
            channels.pop(ch_id, None)

        # ---- 设备族 v0.5 ----
        elif op == 48:  # DEVOPEN
            dev_id = code[ip]; ip += 1
            devices[dev_id] = {"caps": 0x3F, "open": True, "state": 0}
            stack.append(dev_id)
        elif op == 49:  # DEVCAP
            dev_id = stack.pop()
            stack.append(devices.get(dev_id, {}).get("caps", 0))
        elif op == 50:  # DEVIO（不消耗句柄：data 在顶，句柄在次）
            data = stack.pop(); dev_id = stack[-1]
            if devices.get(dev_id, {}).get("open"):
                devices[dev_id]["state"] = data
                stack.append(data & 0x3F)
            else:
                stack.append(0)
        elif op == 51:  # DEVCLOSE
            dev_id = stack.pop()
            if dev_id in devices: devices[dev_id]["open"] = False

        # ---- 网络族 v0.5 ----
        elif op == 52:  # NETLISTEN
            port = code[ip]; ip += 1
            net["listeners"][port] = {"buf": []}
            stack.append(port)
        elif op == 53:  # NETACCEPT
            handle = stack.pop()
            if handle in net["listeners"] and net["listeners"][handle]["buf"]:
                conn_id = net["next_conn"]; net["next_conn"] += 1
                net["connections"][conn_id] = net["listeners"][handle]["buf"].pop(0)
                stack.append(conn_id)
            else:
                stack.append(0)
        elif op == 54:  # NETDIAL
            addr = code[ip]; ip += 1
            conn_id = net["next_conn"]; net["next_conn"] += 1
            net["connections"][conn_id] = {"peer": addr, "rx_buf": [], "tx_buf": []}
            stack.append(conn_id)
        elif op == 55:  # NETSEND
            conn_id = stack.pop(); data = stack.pop()
            if conn_id in net["connections"]:
                net["connections"][conn_id]["tx_buf"].append(data)
        elif op == 56:  # NETRECV
            conn_id = stack.pop()
            conn = net["connections"].get(conn_id)
            if conn and conn["rx_buf"]:
                stack.append(conn["rx_buf"].pop(0))
            else:
                stack.append(0)
        elif op == 57:  # NETCLOSE
            conn_id = stack.pop()
            net["connections"].pop(conn_id, None)

        # ---- 时钟族 v0.5 ----
        elif op == 58:  # TICK
            stack.append(clock["tick"])
        elif op == 59:  # DELAY
            ms = stack.pop()
            clock["tick"] += ms
        elif op == 60:  # TIMER
            interval = stack.pop(); cb_addr = stack.pop()
            clock["timers"].append((cb_addr, interval, clock["tick"]))

        else:
            raise RuntimeError(f"未知操作码 {op} @ {ip - 1}")

    return {
        "out": out,
        "steps": steps,
        "stack": stack,
        "yin": yin,
        "yang": yang,
        "perception": perception,
        "heap": heap,
        "channels": channels,
        "devices": devices,
        "net": net,
        "clock": clock,
    }


# ---- 命运场景 ----
def build_fate_context():
    d = 字典集()
    for n, cat, tai in [("自己","主体","流动"),("初心目标","目标","固态"),("正轨","路径","固态"),
                        ("误区","歧途","流动"),("旧轨道","歧途","固态"),("不可逆渊","绝域","固态"),
                        ("助力者","他者","流动"),("消耗者","他者","流动"),("垄断者","他者","固态"),
                        ("旁观者","他者","流动"),("资源渠道","渠道","固态")]:
        d.入驻(n, 范畴=cat, 态=tai)
    d.关联("自己","意图","初心目标"); d.关联("自己","行走","正轨")
    d.关联("正轨","通达","初心目标"); d.关联("自己","失误","误区")
    d.关联("误区","纠正","正轨");    d.关联("旧轨道","惯性","不可逆渊")
    d.关联("助力者","助力","自己",w=3.0); d.关联("消耗者","消耗","自己",w=5.0)
    d.关联("消耗者","消耗","旁观者",w=2.0); d.关联("自己","信任","垄断者")
    d.关联("旁观者","信任","垄断者",w=2.0); d.关联("助力者","信任","自己",w=2.0)
    d.关联("垄断者","把持","资源渠道"); d.关联("旁观者","注意","垄断者",w=4.0)
    d.关联("助力者","注意","自己",w=1.0)
    return d


def main():
    ctx = build_fate_context()
    # 标题标签追加在关系标签之后
    titles = ["== 感知 ==", "== 函数调用 ==", "== 堆 ==", "== 通道 ==",
              "== 设备 ==", "== 网络 ==", "== 时钟 =="]
    labels = ["净账","信任","注意力","是否固态","是否割点","是否目标","分歧","等效类大小",
              "能否回归初心","是否死胡同","== 自审：自己 ==","== 关系家族 =="] + titles
    base = 12  # titles 在 labels 中的起始下标

    # ---- 感知总线初始状态 ----
    perception = {
        "sensors": {0: 42, 1: 100, 2: 255},
        "actuators": {}
    }
    # ---- 网络初始状态（预置一个连接，含接收数据）----
    net = {
        "listeners": {},
        "connections": {
            100: {"peer": 1, "rx_buf": [99, 88, 77], "tx_buf": []}
        },
        "next_conn": 101
    }

    program = [
        # 1. 感知
        ("REL_OUTSTR", base + 0),
        ("SENSE", 0), ("PRINT",),

        # 2. 函数调用：double(3) = 6
        ("REL_OUTSTR", base + 1),
        ("PUSH", 3), ("CALL", "double"), ("PRINT",),

        # 3. 堆（存前 DUP 指针，存完后指针仍留栈上供后续读取）
        ("REL_OUTSTR", base + 2),
        ("HPALLOC", 4), ("DUP",), ("PUSH2", 77), ("HPSTORE",), ("HPLOAD",), ("PRINT",),

        # 4. 通道
        ("REL_OUTSTR", base + 3),
        ("CHOPEN", 1), ("PUSH2", 88), ("CHSEND",), ("CHRECV",), ("PRINT",),

        # 5. 设备（能力 → 另开一个句柄做 IO）
        ("REL_OUTSTR", base + 4),
        ("DEVOPEN", 0), ("DEVCAP",), ("PRINT",),
        ("DEVOPEN", 0), ("PUSH", 55), ("DEVIO",), ("PRINT",),

        # 6. 网络（conn_id=100 超 63，需 PUSH2）
        ("REL_OUTSTR", base + 5),
        ("PUSH2", 100), ("NETRECV",), ("PRINT",),

        # 7. 时钟
        ("REL_OUTSTR", base + 6),
        ("TICK",), ("PRINT",), ("PUSH2", 100), ("DELAY",), ("TICK",), ("PRINT",),

        ("HALT",),
        ("LABEL", "double"), ("DUP",), ("ADD",), ("RET",),
    ]

    print("=" * 60)
    print("混元虚拟机 v0.5 —— 可栖居的机体（七族指令扩展）")
    print("=" * 60)

    result = run(program, ctx, labels, subject="自己",
                  perception=perception, net=net)
    for line in result["out"]:
        print(line)

    print("\n[机器状态摘要]")
    print(f"  执行步数: {result['steps']}")
    print(f"  时钟 tick: {result['clock']['tick']}")
    print(f"  感知 actuators: {result['perception']['actuators']}")
    print(f"  堆 next: {result['heap']['next']}")
    print(f"  通道: {list(result['channels'].keys())}")
    print(f"  设备: {list(result['devices'].keys())}")
    print(f"  网络连接: {list(result['net']['connections'].keys())}")
    print(f"  数据栈终态: {result['stack']}")


if __name__ == "__main__":
    main()
