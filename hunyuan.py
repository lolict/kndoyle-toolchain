#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混元一体化入口 (HunYuan Unified) v1.4
=====================================
并网六大模块 + FPGA 流片：

  解释器  hunyuan_vm05  运算主权  +  运行时关系查询（REL 指令族）
                           +  七族指令扩展（感知/调用/堆/通道/设备/网络/时钟）
  转码器  hunyuan_codec  文字主权  +  声韵调混合进制 + 新字体
  齿轮核  hunyuan_gear   硬件主权（软件仿真）+ 64 进制齿轮啮合
  字典集  hunyuan_dict   判断主权  +  关系家族 +  评判引擎
  FPGA    hunyuan_gear   Verilog 导出 + 综合脚本 + 引脚约束（Tang Nano 9K）
  CPU     cpu/           超标量双发射 RISC v1.4 + Cache + Caravel 封装
  外设IP  cpu/periph.v + periph_x.v  Timer + PWM + I2C + DMA + SPI + ETH + USB
  OoO      cpu/hunyuan_cpu_v13.v  2-bit 分支预测 + 8-entry ROB + 寄存器重命名
  双发射   cpu/hunyuan_cpu_v14.v  超标量双发射 + 硬件乘除法 + 配对感知汇编器

全部本地、零依赖、零网络、零 token。

用法：
  python3 hunyuan.py           进入 REPL
  python3 hunyuan.py encode <文本>
  python3 hunyuan.py decode <文件.hy>
  python3 hunyuan.py run       运行关系自审演示
  python3 hunyuan.py judge <主体>
  python3 hunyuan.py family <成员>
  python3 hunyuan.py gear      齿轮核仿真
  python3 hunyuan.py fpga      Verilog 导出 + 综合脚本
  python3 hunyuan.py body      七族指令演示（v0.5 新增）
  python3 hunyuan.py all       一体化总演示
"""

import os
import sys
import json

HERE = os.path.dirname(os.path.abspath(__file__))

# ---- 导入五大模块 ----
sys.path.insert(0, HERE)
from hunyuan_dict import 字典集, 评判引擎  # noqa: E402
from hunyuan_vm05 import run as vm_run, build_fate_context as vm_context, OPS, REL_FLOW  # noqa: E402
from hunyuan_codec import encode_text, hunyuan_decode  # noqa: E402
from hunyuan_gear_hw import demo_gear, export_verilog  # noqa: E402


# =====================================================================
class 混元:
    """一体化外壳：持有字典上下文，对外提供五模块服务。"""

    def __init__(self):
        self.ctx = vm_context()
        self.labels = ["净账", "信任", "注意力", "是否固态", "是否割点",
                       "是否目标", "分歧", "等效类大小", "能否回归初心",
                       "是否死胡同", "== 自审：{} ==", "== 关系家族 =="]

    # ---- 1. 运算 ----
    def 运算(self, n):
        """用 v0.1 风格累加 1..n。"""
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
        result = vm_run(program, self.ctx, labels, subject=subject)
        return result["out"]

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
        result = vm_run(program, self.ctx, self.labels, subject=subject)
        return result["out"]

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
        tab_path = os.path.join(HERE, "hunyuan_font.hy2t")
        if not os.path.exists(tab_path):
            return "无码表，请先编码"
        with open(tab_path, encoding="utf-8") as f:
            tab = json.load(f)
        return hunyuan_decode(data, len(data) * 8 - ((-len(data) * 8) % 8) or len(data) * 8, tab)

    # ---- 4. 齿轮核 ----
    def 齿轮(self):
        return demo_gear()

    # ---- 6. FPGA (v0.6 新增) ----
    def fpga(self):
        """导出 Verilog + 写综合脚本，返回导出报告。"""
        files = export_verilog()
        return {"导出文件": files, "目录": "fpga/",
                "下一步": "本地装 yosys + nextpnr-ice40，然后 fpga/synthesize.sh"}

    # ---- 5. 七族指令 (v0.5 新增) ----
    def 机体(self):
        """七族指令v0.5 演示：感知/调用/堆/通道/设备/网络/时钟。"""
        titles = ["== 感知 ==", "== 函数调用 ==", "== 堆 ==", "== 通道 ==",
                  "== 设备 ==", "== 网络 ==", "== 时钟 =="]
        labels = self.labels + titles
        base = len(self.labels)

        perception = {"sensors": {0: 42, 1: 100}, "actuators": {}}
        net = {
            "listeners": {},
            "connections": {100: {"peer": 1, "rx_buf": [99, 88, 77], "tx_buf": []}},
            "next_conn": 101,
        }

        program = [
            # 感知
            ("REL_OUTSTR", base + 0),
            ("SENSE", 0), ("PRINT",),
            # 函数调用
            ("REL_OUTSTR", base + 1),
            ("PUSH", 3), ("CALL", "double"), ("PRINT",),
            # 堆
            ("REL_OUTSTR", base + 2),
            ("HPALLOC", 4), ("DUP",), ("PUSH2", 77), ("HPSTORE",), ("HPLOAD",), ("PRINT",),
            # 通道
            ("REL_OUTSTR", base + 3),
            ("CHOPEN", 1), ("PUSH2", 88), ("CHSEND",), ("CHRECV",), ("PRINT",),
            # 设备
            ("REL_OUTSTR", base + 4),
            ("DEVOPEN", 0), ("DEVCAP",), ("PRINT",),
            ("DEVOPEN", 0), ("PUSH", 55), ("DEVIO",), ("PRINT",),
            # 网络
            ("REL_OUTSTR", base + 5),
            ("PUSH2", 100), ("NETRECV",), ("PRINT",),
            # 时钟
            ("REL_OUTSTR", base + 6),
            ("TICK",), ("PRINT",), ("PUSH2", 100), ("DELAY",), ("TICK",), ("PRINT",),
            ("HALT",),
            ("LABEL", "double"), ("DUP",), ("ADD",), ("RET",),
        ]

        result = vm_run(program, self.ctx, labels, subject="自己",
                        perception=perception, net=net)
        return result

    # ---- 总演示 ----
    def 总演示(self):
        print("=" * 60)
        print("混元一体化总演示 v1.4 —— 七族指令 + FPGA + 双发射 CPU + Cache + IP")
        print("=" * 60)
        print("\n【1. 运算主权】Σ(1..100) =", self.运算(100))
        print("\n【2. 判断主权】净账/信任/割点/回归/死胡同:")
        for line in self.自审("自己")[:6]:
            print("  ", line)
        print("\n【3. 文字主权】编码：满全法爱刘楚恬")
        r = self.编码("满全法爱刘楚恬")
        print("    ", r["报告"])
        print("\n【4. 硬件主权】齿轮核仿真（前 3 行）")
        for line in self.齿轮()[:3]:
            print("   ", line)
        print("\n【5. 机体主权】七族指令（感知/调用/堆/通道/设备/网络/时钟）")
        body = self.机体()
        for line in body["out"]:
            print("  ", line)
        print("\n【6. FPGA 主权】Verilog 导出（零依赖）")
        fpga = self.fpga()
        for fn in fpga["导出文件"]:
            print("   ", fn)
        print("    目录:", fpga["目录"])
        print("    下一步:", fpga["下一步"])
        print("\n【7. CPU 主权】超标量双发射 v1.4 (MUL/DIV + BHT/BTB) + Cache + 外设 IP")
        cpu_files = ["cpu/hunyuan_cpu.v", "cpu/hunyuan_cpu_pipelined.v",
                     "cpu/hunyuan_cpu_v13.v",
                     "cpu/cache.v", "cpu/periph.v", "cpu/periph_x.v",
                     "cpu/hunyuan_soc_v11.v",
                     "cpu/tb_pipeline.v", "cpu/tb_v13.v",
                     "cpu/hunyuan_cpu_v14.v", "cpu/tb_v14.v",
                     "cpu/gen_progs_v14.py",
                     "tapeout/caravel_wrapper.v"]
        for fn in cpu_files:
            print("   ", fn)
        print("   v1.4 新特性 (双发射超标量):")
        print("   64-bit fetch bundle → 双 lane 译码/EX/WB")
        print("   硬件 Booth 乘法 (4 周期) + 非恢复除法 (8 周期)")
        print("   静态配对: ALU+ALU, ALU+MEM, ALU+MUL; 禁 双MEM/双分支/双MUL/RAW/WAW")
        print("   2-bit 动态分支预测 + BTB (64-entry BHT, 32-entry BTB)")
        print("   配对感知汇编器 (gen_progs_v14.py) + 自动 NOP 填充")
        print("   v1.3 继承: 8-entry ROB OoO + 寄存器重命名")
        print("   5级流水 + 前递 + load-under-miss D-Cache")
        print("   Caravel 封装路径: tapeout/caravel_wrapper.v")
        print("\n" + "=" * 60)
        print("混元 v1.4 完成。超标量双发射 + 硬件乘除法 + 分支预测 + 配对感知汇编器，全部本地。")


# =====================================================================
def repl():
    print("混元 REPL —— 输入: 运算(n) / 自审(主体) / 判断(主体) / 家族(成员) / 编码(文本) / 齿轮 / 机体 / 总演示 / 退出")
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
            elif line.startswith("机体"):
                body = y.机体()
                for l in body["out"]:
                    print("  ", l)
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
    elif cmd == "body":
        body = y.机体()
        for line in body["out"]:
            print(line)
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
    elif cmd == "fpga":
        r = y.fpga()
        print(r)
    else:
        print(f"未知命令 {cmd}。可用: all / body / run / judge / family / encode / gear / fpga / (无参数进 REPL)")


if __name__ == "__main__":
    main()
