#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混元关联态射字典集 + 评判引擎 v0.1
====================================
指令集是孤寡原子，字典集是它的关系族。纯本地、零依赖的符号智能：
不连服务器、不接大模型——内部的态射就是模型，字典家族自己知道
自己的范畴与关联方式（自带智能律）。

概念映射（你的判断语言 → 图论算法）：

  上层逻辑如何被关联   字典 = 类型化关系图；上层逻辑 = 图生成的自由范畴（路径）
  谁能回归命运回归线   可达性：存在回到目标的路径（失误纠正 = 回归边存在）
  谁是死胡同/不可逆    无任何通向目标的路径（吸收态）
  截断性/不可截断性    割点：删掉它就断流的咽喉节点（渠道垄断的位置）
  分歧性/不能分歧性    出度 ≥ 2 可分歧；= 1 单轨；= 0 绝路
  等效性/非等效性      关系签名相同 → 等效类（观察等价）
  谁垄断信任/注意力    信任边入度份额 + 是否占据割点
  正存在/负存在计算    净流量账本：助力流入为正，被消耗流出为负
  谁是目标/谁是手段    意图边的终点 = 目标；处于他人目标路径上 = 手段
"""

import json
from collections import defaultdict, deque

# 价值流方向表：助力/资助 = 沿边流出（源减、宿加）；消耗/抽取 = 逆边回流（源加、宿减）
FLOW = {"助力": -1, "资助": -1, "消耗": +1, "抽取": +1}


class 字典集:
    """关联态射字典：每个成员有范畴、层级、属性；成员之间是带类型的态射边。"""

    def __init__(self):
        self.members = {}          # 名 → {范畴, 层级, 态, 时空}
        self.edges = []            # (源, 关系, 宿, 权重)

    def 入驻(self, name, 范畴="未分", 层级=0, 态="流动", 时空=(0, 0)):
        self.members[name] = {"范畴": 范畴, "层级": 层级, "态": 态, "时空": 时空}

    def 关联(self, a, rel, b, w=1.0):
        assert a in self.members and b in self.members, f"未知成员 {a}/{b}"
        self.edges.append((a, rel, b, w))

    def 关系族(self, name, depth=2):
        """谁跟我有关系：沿边走 depth 层，返回整片关系家族。"""
        adj = defaultdict(list)
        for a, rel, b, w in self.edges:
            adj[a].append((rel, b))
            adj[b].append(("←" + rel, a))
        seen, out, q = {name}, [], deque([(name, 0)])
        while q:
            u, d = q.popleft()
            if d == depth:
                continue
            for rel, v in adj[u]:
                out.append(f"{u} —{rel}→ {v}" if not rel.startswith("←") else f"{u} {rel} {v}")
                if v not in seen:
                    seen.add(v)
                    q.append((v, d + 1))
        return out


class 评判引擎:
    """对字典集行使判断：本地符号智能，不需要任何外部模型。"""

    def __init__(self, dic):
        self.d = dic
        self.nodes = list(dic.members)
        self.adj = defaultdict(list)           # 有向（可达性用）
        self.und = defaultdict(list)           # 无向（割点用）
        for a, rel, b, w in dic.edges:
            self.adj[a].append(b)
            self.und[a].append(b)
            self.und[b].append(a)

    # ---- 可达性 ----
    def 可达集(self, src):
        seen = {src}
        q = deque([src])
        while q:
            u = q.popleft()
            for v in self.adj[u]:
                if v not in seen:
                    seen.add(v)
                    q.append(v)
        return seen

    def 能回归(self, 目标):
        """命运回归线：谁存在回到目标的路径。"""
        return {n for n in self.nodes if 目标 in self.可达集(n) and n != 目标}

    def 死胡同(self, 目标):
        return {n for n in self.nodes if 目标 not in self.可达集(n) and n != 目标}

    # ---- 割点（截断性：渠道咽喉）----
    def 割点(self):
        idx, low, cut = {}, {}, set()
        t = [0]

        def dfs(u, parent):
            idx[u] = low[u] = t[0]
            t[0] += 1
            children = 0
            for v in self.und[u]:
                if v not in idx:
                    children += 1
                    dfs(v, u)
                    low[u] = min(low[u], low[v])
                    if parent is not None and low[v] >= idx[u]:
                        cut.add(u)
                elif v != parent:
                    low[u] = min(low[u], idx[v])
            if parent is None and children > 1:
                cut.add(u)

        for n in self.nodes:
            if n not in idx:
                dfs(n, None)
        return cut

    # ---- 分歧性 ----
    def 分歧(self):
        return {n: ("可分歧" if len(set(self.adj[n])) >= 2 else
                    "单轨" if len(set(self.adj[n])) == 1 else "绝路")
                for n in self.nodes}

    # ---- 等效性（关系签名 → 观察等价类）----
    def 等效类(self):
        sig = defaultdict(list)
        for n in self.nodes:
            outs = tuple(sorted(rel for a, rel, b, _ in self.d.edges if a == n))
            ins = tuple(sorted("←" + rel for a, rel, b, _ in self.d.edges if b == n))
            sig[(outs, ins)].append(n)
        return [tuple(v) for v in sig.values() if len(v) > 1]

    # ---- 注意力 ----
    def 注意力(self):
        score = defaultdict(float)
        for a, rel, b, w in self.d.edges:
            if rel == "注意":
                score[b] += w
        return dict(sorted(score.items(), key=lambda kv: -kv[1]))

    # ---- 信任与垄断 ----
    def 信任(self):
        inn = defaultdict(float)
        for a, rel, b, w in self.d.edges:
            if rel == "信任":
                inn[b] += w
        return dict(sorted(inn.items(), key=lambda kv: -kv[1]))

    def 垄断者(self):
        """信任高度集中 + 占据割点咽喉 = 垄断。"""
        trust = self.信任()
        total = sum(trust.values()) or 1
        cuts = self.割点()
        return {n: round(s / total, 2) for n, s in trust.items()
                if s / total >= 0.5 or n in cuts}

    # ---- 正存在 / 负存在账本 ----
    def 净账(self):
        acc = defaultdict(float)
        for a, rel, b, w in self.d.edges:
            if rel in FLOW:
                acc[a] += FLOW[rel] * w      # 消耗:源得正；助力:源付正
                acc[b] -= FLOW[rel] * w      # 消耗:宿失正；助力:宿得正
        return dict(sorted(acc.items(), key=lambda kv: -kv[1]))

    # ---- 目标与手段 ----
    def 目标集(self):
        return {b for a, rel, b, _ in self.d.edges if rel == "意图"}

    def 手段(self, agent):
        """处于某人目标路径上的节点 = 被ta使用的手段。"""
        out = set()
        for g in self.目标集():
            reach_g = self.能回归(g)
            out |= {n for n in reach_g if n in self.可达集(agent) and n != agent}
        return out


# =====================================================================
def demo_指令关系族():
    print("=" * 64)
    print("一、指令关系族：孤寡指令不再孤寡")
    print("=" * 64)
    d = 字典集()
    for op, cat, lv in [("PUSH", "栈", 0), ("ADD", "算逻", 1), ("SUB", "算逻", 1),
                        ("MUL", "算逻", 1), ("DIV", "算逻", 1),
                        ("LOAD", "内存", 1), ("STORE", "内存", 1),
                        ("JZ", "控制", 2), ("JMP", "控制", 2),
                        ("YIN", "阴阳", 3), ("YANG", "阴阳", 3), ("HALT", "终结", 4)]:
        d.入驻(op, 范畴=cat, 层级=lv)
    d.关联("PUSH", "组合", "ADD");   d.关联("ADD", "互逆", "SUB")
    d.关联("MUL", "互逆", "DIV");    d.关联("LOAD", "互逆", "STORE")
    d.关联("JZ", "关联", "JMP");     d.关联("YIN", "镜像", "YANG")
    d.关联("JZ", "依赖", "LOAD");    d.关联("HALT", "归属", "YIN")
    print("PUSH 的关系家族（两层）:")
    for line in d.关系族("PUSH"):
        print("   " + line)
    eng = 评判引擎(d)
    print("层级分布:", {lv: [n for n, m in d.members.items() if m["层级"] == lv]
                       for lv in sorted({m["层级"] for m in d.members.values()})})


def demo_命运场景():
    print("\n" + "=" * 64)
    print("二、命运场景：判断家族集体作答")
    print("=" * 64)
    d = 字典集()
    for n, cat, tai in [("自己", "主体", "流动"), ("初心目标", "目标", "固态"),
                        ("正轨", "路径", "固态"), ("误区", "歧途", "流动"),
                        ("旧轨道", "歧途", "固态"), ("不可逆渊", "绝域", "固态"),
                        ("助力者", "他者", "流动"), ("消耗者", "他者", "流动"),
                        ("垄断者", "他者", "固态"), ("旁观者", "他者", "流动"),
                        ("资源渠道", "渠道", "固态")]:
        d.入驻(n, 范畴=cat, 态=tai)
    # 路径与命运
    d.关联("自己", "意图", "初心目标")
    d.关联("自己", "行走", "正轨");      d.关联("正轨", "通达", "初心目标")
    d.关联("自己", "失误", "误区");      d.关联("误区", "纠正", "正轨")     # 可回归
    d.关联("旧轨道", "惯性", "不可逆渊")                                        # 无回路
    # 能量账（正负存在）
    d.关联("助力者", "助力", "自己", w=3.0)
    d.关联("消耗者", "消耗", "自己", w=5.0)
    d.关联("消耗者", "消耗", "旁观者", w=2.0)
    # 信任与渠道
    d.关联("自己", "信任", "垄断者");    d.关联("旁观者", "信任", "垄断者", w=2.0)
    d.关联("助力者", "信任", "自己", w=2.0)
    d.关联("垄断者", "把持", "资源渠道")   # 资源只经垄断者 → 它是渠道割点
    # 注意力
    d.关联("旁观者", "注意", "垄断者", w=4.0)
    d.关联("助力者", "注意", "自己", w=1.0)

    eng = 评判引擎(d)
    目标 = "初心目标"
    print(f"谁能走到命运回归线（可达{目标}）: {sorted(eng.能回归(目标))}")
    print(f"谁是死胡同/不可逆（不可达{目标}）: {sorted(eng.死胡同(目标))}")
    print(f"截断性咽喉（割点，渠道垄断位）: {sorted(eng.割点())}")
    print(f"分歧性: {eng.分歧()}")
    print(f"注意力排行: {eng.注意力()}")
    print(f"信任排行: {eng.信任()}")
    print(f"谁垄断信任与渠道: {eng.垄断者()}")
    print(f"正负存在净账（正=盈余，负=被消耗）: {eng.净账()}")
    print(f"谁是目标: {sorted(eng.目标集())}")
    print(f"自己路径上的手段: {sorted(eng.手段('自己'))}")
    print(f"固态者: {[n for n, m in d.members.items() if m['态'] == '固态']}")
    print(f"流动者: {[n for n, m in d.members.items() if m['态'] == '流动']}")


if __name__ == "__main__":
    demo_指令关系族()
    demo_命运场景()
