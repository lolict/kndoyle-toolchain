#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
混元齿轮核 v0.1 (HunYuan Gear Core) —— 软件仿真的硬件
======================================================
这一步回答一个问题：软件能不能模拟硬件？能。本文件用硬件描述语言
（Amaranth HDL）描述真正的数字电路，然后在纯软件仿真器里驱动它。

概念映射（形式化框架 → 硬件实现）：

  齿轮传动律   每齿 6 bit；满 64 进一 = 啮合点（carry 沿齿轮链逐级传递）
  分布式大齿轮 个位/十位/百位三枚 64 进制齿轮组成啮合链
  同一语义两个投影 这份代码：仿真器里跑 = 软件；综合成网表烧进 FPGA = 硬件
                   语义不变，基底互换 —— 软硬件一体化（H ≅ 硬件视图 ≅ 软件视图）
  架空律的硬件版 混元核不必兼容任何现有指令集，语义权威在我们的解释器

下一步路线：本模块 → amaranth 导出 Verilog（需 yosys）→ 烧进 FPGA 开发板
（如 Tang Nano，百元级）→ 第一枚摸得到的混元芯片。
"""

from amaranth import Elaboratable, Module, Signal, Mux
from amaranth.sim import Simulator, Settle, Tick


class GearALU(Elaboratable):
    """单齿算术单元：6 bit 一齿，加/减，进位（借位）= 啮合点。"""

    def __init__(self):
        self.a = Signal(6)
        self.b = Signal(6)
        self.sub = Signal()          # 0=加 1=减
        self.result = Signal(6)
        self.carry = Signal()        # 加法=进位；减法取反即借位

    def elaborate(self, platform):
        m = Module()
        full = Signal(8)
        b2 = Signal(6)
        m.d.comb += b2.eq(Mux(self.sub, self.b ^ 0x3F, self.b))      # 减法取补码
        m.d.comb += full.eq(self.a + b2 + self.sub)
        m.d.comb += self.result.eq(full[:6])
        m.d.comb += self.carry.eq(full[6])
        return m


class GearChain(Elaboratable):
    """三齿轮啮合链：64 进制计数器，进位逐级啮合，满 64^3 溢出。"""

    def __init__(self):
        self.en = Signal()                       # 小齿轮脉冲输入
        self.d0 = Signal(6)                      # 个位齿轮
        self.d1 = Signal(6)                      # 十位齿轮
        self.d2 = Signal(6)                      # 百位齿轮
        self.overflow = Signal()                 # 满 64³ 溢出标志

    def elaborate(self, platform):
        m = Module()
        with m.If(self.en):
            with m.If(self.d0 == 63):
                m.d.sync += self.d0.eq(0)
                with m.If(self.d1 == 63):
                    m.d.sync += self.d1.eq(0)
                    with m.If(self.d2 == 63):
                        m.d.sync += self.d2.eq(0)
                        m.d.sync += self.overflow.eq(1)
                    with m.Else():
                        m.d.sync += self.d2.eq(self.d2 + 1)
                with m.Else():
                    m.d.sync += self.d1.eq(self.d1 + 1)
            with m.Else():
                m.d.sync += self.d0.eq(self.d0 + 1)
        return m


def check(name, got, want):
    ok = got == want
    print(f"  [{name}] 实测 {got} 期望 {want}  {'✓' if ok else '✗'}")
    assert ok, name


def main():
    print("=" * 64)
    print("混元齿轮核 v0.1 —— 软件仿真中的硬件电路")
    print("=" * 64)

    # ---- 单齿 ALU：验证齿轮律（满 64 进一）
    alu = GearALU()
    sim = Simulator(alu)

    def test_alu():
        cases = [
            # (a, b, sub, 期望result, 期望carry)
            (63, 1, 0, 0, 1),    # 满 64 进一：啮合点 ✓
            (32, 31, 0, 63, 0),  # 未满月，不进位
            (40, 24, 0, 0, 1),   # 恰好 64，归零进一
            (5, 3, 1, 2, 1),     # 减：够减，无借位
            (1, 2, 1, 63, 0),    # 减：不够减，绕回 63，借位
        ]
        for a, b, s, er, ec in cases:
            yield alu.a.eq(a)
            yield alu.b.eq(b)
            yield alu.sub.eq(s)
            yield Settle()
            r = yield alu.result
            c = yield alu.carry
            check(f"ALU {a}{'-' if s else '+'}{b}", (r, c), (er, ec))

    sim.add_process(test_alu)
    sim.run()
    print("单齿 ALU：齿轮律（满 64 进一 / 借位绕回）全部成立 ✓\n")

    # ---- 三齿轮链：验证分布式啮合
    chain = GearChain()
    sim = Simulator(chain)
    sim.add_clock(1e-6)

    def test_chain():
        yield chain.en.eq(1)
        for _ in range(64):                      # 小齿轮拧 64 齿
            yield Tick()
        yield Settle()
        d0 = yield chain.d0
        d1 = yield chain.d1
        check("拧64齿后(个,十)", (d0, d1), (0, 1))     # 个位满 64 → 十位进一

        for _ in range(64 * 63):                 # 再拧到 64×64
            yield Tick()
        yield Settle()
        d1 = yield chain.d1
        d2 = yield chain.d2
        check("拧64×64齿后(十,百)", (d1, d2), (0, 1))  # 十位满 64 → 百位进一

        # 灌满 (63,63,63) 再拧一齿 → 全体归零 + 溢出
        yield chain.en.eq(0)
        yield chain.d0.eq(63)
        yield chain.d1.eq(63)
        yield chain.d2.eq(63)
        yield Settle()
        yield chain.en.eq(1)
        yield Tick()
        yield Settle()
        d0 = yield chain.d0
        d2 = yield chain.d2
        ov = yield chain.overflow
        check("满链再拧一齿(个,百,溢出)", (d0, d2, ov), (0, 0, 1))

    sim.add_process(test_chain)
    sim.run()
    print("三齿轮链：逐级啮合、满链溢出全部成立 ✓")

    print("\n[结论] 以上每一条 ✓ 都是软件在仿真硬件：电路是真的，基底是虚的。")
    print("       同一份代码明天综合成网表烧进 FPGA，虚的就变成实的——")
    print("       语义不变，基底互换，这就是软硬件一体化的第一步。")


if __name__ == "__main__":
    main()
