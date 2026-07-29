#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混元一体化入口 (HunYuan Unified)
===============================
并网四大模块，一个程序同时调度：

  解释器  hunyuan_vm03  运算主权  + 运行时关系查询（REL 指令族）
  转码器  hunyuan_codec  文字主权  + 声韵调混合进制 + 新字体
  齿轮核  hunyuan_gear   硬件主权（软件仿真）+ 64 进制齿轮啮合
  字典集  hunyuan_dict   判断主权  + 关系家族 + 评判引擎

全部本地、零依赖、零网络、零 token。
用法：
  python3 hunyuan.py           进入 REPL
  python3 hunyuan.py encode <文本>
  python3 hunyuan.py decode <文件.hy>
  python3 hunyuan.py run       运行关系自审演示
  python3 hunyuan.py judge <主体>
  python3 hunyuan.py family <成员>
  python3 hunyuan.py gear      齿轮核仿真
  python3 hunyuan.py all       一体化总演示
"""

import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- 导入四大模块 ----
sys.path.insert(0, HERE)
from hunyuan_dict import 字典集, 评判引擎  # noqa: E402
from hunyuan_vm03 import run as vm_run, build_fate_context as vm_context, OPS, REL_FLOW  # noqa: E402
from hunyuan_codec import encode_text, hunyuan_decode  # noqa: E402
from hunyuan_gear_hw import demo_gear  # noqa: E402


# =====================================================================
class 混元:
    """一体化外壳：持有字典上下文，对外提供四模块服务。"""

    def __init__(self):
        self.ctx = vm_context()                 # 关系上下文（命运场景 + 指令族）
        self.labels = ["净账", "信任", "注意力", "是否固态", "是否割点",
                       "是否目标", "分歧", "等效类大小", "能否回归初心",
                       "是否死胡同", "== 自审：{} ==", "== 关系家族 =="]

    # ---- 1. 运算 ----
    def 运算(self, n):
        """用 v0.1 风格累加 1..n，返回结果。"""
        from hunyuan_vm import program_sum, run
        return run(program_sum(n))["out"][0]

    # ---- 2. 关系查询 ----
    def 自审(self, subject="自己"):
        program = [
            ("REL_OUTSTR", 10),
            ("REL_SET", list(self.ctx.members).index(subject)),
            ("REL_OUTSTR", 0), ("REL_NET",), ("PRINT",),
            ("REL_OUTSTR", 1), ("REL_TRUST",), ("PRINT",),
            ("REL_OUTSTR", 2), ("REL_ATTEN",), ("PRINT",),
            ("REL_OUTSTR", 3), ("REL_SOLID",), ("PRINT",),
            ("REL_OUTSTR", 4), ("REL_CUT",), ("PRINT",),
            ("REL_OUTSTR", 5), ("REL_GOAL",), ("PRINT",),
            ("REL_OUTSTR", 6), ("REL_DIFF",), ("PRINT",),
            ("REL_OUTSTR", 7), ("REL_EQUIV",), ("PRINT",),
            ("REL_OUTSTR", 8), ("REL_CAN", list(self.ctx.members).index("初心目标")), ("PRINT",),
            ("REL_OUTSTR", 9), ("REL_DEAD",), ("PRINT",),
            ("REL_OUTSTR", 11),
            ("REL_FAMILY",),
            ("HALT",),
        ]
        labels = [l.format(subject) if "{}" in l else l for l in self.labels]
        return vm_run(program, self.ctx, labels, subject=subject)

    def 判断(self, subject):
        eng = 评判引擎(self.ctx)
        names = list(self.ctx.members)
        if subject not in names:
            return f"未知主体 {subject}，已知：{names}"
        idx = names.index(subject)
        program = [
            ("REL_SET", idx),
            ("REL_NET",), ("PRINT",),
            ("REL_TRUST",), ("PRINT",),
            ("REL_CUT",), ("PRINT",),
            ("REL_CAN", names.index("初心目标") if "初心目标" in names else 0), ("PRINT",),
            ("REL_DEAD",), ("PRINT",),
            ("HALT",),
        ]
        return vm_run(program, self.ctx, self.labels, subject=subject)

    def 家族(self, member):
        return self.ctx.关系族(member)

    # ---- 3. 编解码 ----
    def 编码(self, text):
        data, nbits, tab, rep = encode_text(text)
        out = os.path.join(HERE, "last_encode.hy")
        with open(out, "wb") as f:
            f.write(data)
        return {"报告": rep, "文件": out, "位数": nbits}

    def 解码(self, path):
        with open(path, "rb") as f:
            data = f.read()
        # 用最近一次编码的码表（简化：重新从文件旁的码表加载）
        tab_path = os.path.join(HERE, "hunyuan_font.hy2t")
        if not os.path.exists(tab_path):
            return "无码表，请先编码"
        with open(tab_path, encoding="utf-8") as f:
            tab = json.load(f)
        return hunyuan_decode(data, len(data) * 8 - ((-len(data) * 8) % 8) or len(data) * 8, tab)

    # ---- 4. 齿轮核 ----
    def 齿轮(self):
        return demo_gear()

    # ---- 总演示 ----
    def 总演示(self):
        print("=" * 60)
        print("混元一体化总演示 —— 四模块并网，本地零依赖")
        print("=" * 60)
        print("\n【1. 运算主权】Σ(1..100) =", self.运算(100))
        print("\n【2. 判断主权】自审：自己")
        for line in self.自审("自己"):
            print("  ", line)
        print("\n【3. 文字主权】编码：满全法爱刘楚恬")
        r = self.编码("满全法爱刘楚恬")
        print("    ", r["报告"])
        print("\n【4. 硬件主权】齿轮核仿真（前 4 行）")
        for line in self.齿轮()[:4]:
            print("   ", line)
        print("\n" + "=" * 60)
        print("四模块并网完成。数据全在本地，不依赖任何外部服务。")


# =====================================================================
def repl():
    print("混元 REPL —— 输入: 运算(n) / 自审(主体) / 判断(主体) / 家族(成员) / 编码(文本) / 齿轮 / 总演示 / 退出")
    y = 混元()
    while True:
        try:
            line = input("混元> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not line or line in ("退出", "quit", "exit"):
            break
        try:
            if line.startswith("总演示"):
                y.总演示()
            elif line.startswith("齿轮"):
                for l in y.齿轮():
                    print("  ", l)
            elif line.startswith("编码(") and line.endswith(")"):
                r = y.编码(line[3:-1])
                print("   ", r["报告"])
            elif line.startswith("家族(") and line.endswith(")"):
                for l in y.家族(line[3:-1]):
                    print("   ", l)
            elif line.startswith("判断(") and line.endswith(")"):
                for l in y.判断(line[3:-1]):
                    print("   ", l)
            elif line.startswith("自审(") and line.endswith(")"):
                for l in y.自审(line[3:-1]):
                    print("   ", l)
            elif line.startswith("运算(") and line.endswith(")"):
                print("   =", y.运算(int(line[3:-1])))
            else:
                print("   未知命令")
        except Exception as e:
            print("   错误:", e)


def main():
    if len(sys.argv) < 2:
        repl()
        return
    cmd, *args = sys.argv[1], sys.argv[2:]
    y = 混元()
    if cmd == "all":
        y.总演示()
    elif cmd == "run":
        for line in y.自审(args[0] if args else "自己"):
            print(line)
    elif cmd == "judge":
        for line in y.判断(args[0]):
            print(line)
    elif cmd == "family":
        for line in y.家族(args[0]):
            print(line)
    elif cmd == "encode":
        r = y.编码(" ".join(args))
        print(r["报告"])
    elif cmd == "gear":
        for line in y.齿轮():
            print(line)
    else:
        print(f"未知命令 {cmd}。可用: all / run / judge / family / encode / gear / (无参数进 REPL)")


if __name__ == "__main__":
    main()
