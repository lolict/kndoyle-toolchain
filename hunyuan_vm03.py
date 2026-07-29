#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混元虚拟机 v0.3 (HunYuan VM) —— 运行时拥有关系查询与判断能力
===========================================================
v0.1 解释器能算算术；v0.2 转码器能编解码；v0.3 给程序装上"字典直觉"：
程序在运行中能查询自己的关系家族、判断谁能回归、谁是死胡同、
谁垄断信任、谁被截断、正负几何——且不依赖任何外部模型。

新增关系指令族（op 23..35）：
  23 REL_SET   设置当前主体（操作数 = 成员序号）
  24 REL_CAN   当前主体能否到达目标（操作数 = 目标序号）→ 压 0/1
  25 REL_CUT   当前主体是不是割点（咽喉）→ 压 0/1
  26 REL_NET   当前主体净账 ×10（整数，正=盈余 负=被消耗）
  27 REL_TRUST 当前主体信任值 ×10
  28 REL_ATTEN 当前主体注意力 ×10
  29 REL_SOLID 当前主体是否固态 → 压 0/1
  30 REL_DEAD  当前主体是否死胡同 → 压 0/1
  31 REL_GOAL  当前主体是否为目标 → 压 0/1
  32 REL_DIFF  当前主体分歧性（0绝路 1单轨 2可分歧）
  33 REL_EQUIV 当前主体所在等效类大小
  34 REL_FAMILY 输出当前主体的整片关系家族
  35 REL_OUTSTR 输出一条预设文本标签（操作数 = 序号）
"""

import sys
from collections import defaultdict, deque

# ---- 关系引擎（从字典集搬来，避免在本文件重复维护）----
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


OPS = {
    "HALT": (0, 0), "PUSH": (1, 1), "PUSH2": (2, 2),
    "ADD": (3, 0), "SUB": (4, 0), "MUL": (5, 0), "DIV": (6, 0),
    "LOAD": (17, 2), "STORE": (16, 2), "JZ": (14, 2), "JMP": (13, 2),
    "YIN": (18, 0), "YANG": (19, 0), "PRINT": (12, 0),
    "REL_SET": (23, 1), "REL_CAN": (24, 1), "REL_CUT": (25, 0),
    "REL_NET": (26, 0), "REL_TRUST": (27, 0), "REL_ATTEN": (28, 0),
    "REL_SOLID": (29, 0), "REL_DEAD": (30, 0), "REL_GOAL": (31, 0),
    "REL_DIFF": (32, 0), "REL_EQUIV": (33, 0), "REL_FAMILY": (34, 0),
    "REL_OUTSTR": (35, 1),
}


def assemble(program):
    addr, pos = {}, 0
    for item in program:
        if isinstance(item, str): item = (item,)
        if item[0] == "LABEL": addr[item[1]] = pos
        else: pos += 1 + OPS[item[0]][1]
    code = []
    for item in program:
        if isinstance(item, str): item = (item,)
        if item[0] == "LABEL": continue
        op, ops = item[0], item[1:]
        code.append(OPS[op][0])
        if op in ("JMP", "JZ"):
            a = addr[ops[0]]; code += [a // 64, a % 64]
        elif op in ("STORE", "LOAD"):
            code += [ops[0] // 64, ops[0] % 64]
        elif op == "PUSH": code.append(ops[0] & 0x3F)
        elif op == "REL_SET" or op == "REL_CAN" or op == "REL_OUTSTR":
            code.append(ops[0])
    return code


def run(program, context, labels, subject="自己"):
    code = assemble(program)
    engine = 评判引擎(context)
    names = list(context.members)        # 成员序号 → 名称
    name2idx = {n: i for i, n in enumerate(names)}
    subj = subject                       # 当前主体（字符串）
    cut_set = engine.割点()
    net = engine.净账()
    trust = engine.信任()
    atten = engine.注意力()
    equiv = engine.等效类()
    goals = engine.目标集()
    adj = engine.adj
    member = context.members

    stack, mem, out = [], [0]*4096, []
    ip, n, steps = 0, len(code), 0

    def cur(name):
        return {
            "net": int(round(net.get(name, 0) * 10)),
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
        if op == 17: stack.append(mem[code[ip]*64+code[ip+1]]); ip += 2
        elif op == 16: mem[code[ip]*64+code[ip+1]] = stack.pop(); ip += 2
        elif op == 14:
            a = code[ip]*64+code[ip+1]; ip += 2
            if stack.pop() == 0: ip = a
        elif op == 1: stack.append(code[ip]); ip += 1
        elif op == 2: stack.append(code[ip]*64+code[ip+1]); ip += 2
        elif op == 3: b=stack.pop(); stack.append(stack.pop()+b)
        elif op == 4: b=stack.pop(); stack.append(stack.pop()-b)
        elif op == 5: b=stack.pop(); stack.append(stack.pop()*b)
        elif op == 6: b=stack.pop(); stack.append(stack.pop()//b)
        elif op == 13: ip = code[ip]*64+code[ip+1]
        elif op == 12: out.append(str(stack.pop()))
        elif op == 18: pass
        elif op == 19: pass
        # ---- 关系指令族 ----
        elif op == 23: subj = names[code[ip]]; ip += 1                 # REL_SET
        elif op == 24:                                                  # REL_CAN
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
        elif op == 34:                                                  # REL_FAMILY
            for line in context.关系族(subj):
                out.append(line)
        elif op == 35: out.append(labels[code[ip]]); ip += 1           # REL_OUTSTR
        elif op == 0: break
        else: raise RuntimeError(f"未知操作码 {op}")
    return out


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
    labels = ["净账","信任","注意力","是否固态","是否割点","是否目标","分歧","等效类大小",
              "能否回归初心","是否死胡同","== 自审：自己 ==","== 关系家族 =="]

    program = [
        ("REL_OUTSTR", 10),
        ("REL_SET", 0),           # 主体 = 自己 (序号0)
        ("REL_OUTSTR", 0), ("REL_NET",),   ("PRINT",),
        ("REL_OUTSTR", 1), ("REL_TRUST",), ("PRINT",),
        ("REL_OUTSTR", 2), ("REL_ATTEN",), ("PRINT",),
        ("REL_OUTSTR", 3), ("REL_SOLID",), ("PRINT",),
        ("REL_OUTSTR", 4), ("REL_CUT",),   ("PRINT",),
        ("REL_OUTSTR", 5), ("REL_GOAL",),  ("PRINT",),
        ("REL_OUTSTR", 6), ("REL_DIFF",),  ("PRINT",),
        ("REL_OUTSTR", 7), ("REL_EQUIV",), ("PRINT",),
        ("REL_OUTSTR", 8), ("REL_CAN", 1), ("PRINT",),     # 能否到达初心目标
        ("REL_OUTSTR", 9), ("REL_DEAD",),  ("PRINT",),
        ("REL_OUTSTR", 11),
        ("REL_FAMILY",),
        ("HALT",),
    ]

    print("=" * 60)
    print("混元虚拟机 v0.3 —— 运行时关系查询与判断（本地、零依赖）")
    print("=" * 60)
    out = run(program, ctx, labels, subject="自己")
    for line in out:
        print(line)


if __name__ == "__main__":
    main()
