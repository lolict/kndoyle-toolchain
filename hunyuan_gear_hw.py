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


# ---- v0.6 FPGA 综合：Verilog 导出 + 顶层封装 ----

class Counter64(Elaboratable):
    """18 bit ↗ 64 进制个位/十位/百位百分之一秒计数器（用于 LED 闪烁演示）。"""

    def __init__(self):
        self.en = Signal()          # 使能（来自分频后的慢时钟）
        self.d0 = Signal(6)
        self.d1 = Signal(6)
        self.d2 = Signal(6)
        self.overflow = Signal()

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


class HunYuanTop(Elaboratable):
    """混元 FPGA 顶层：12 MHz 时钟 → 分频 → 64 进制计数器 → LED 显示。
    引脚:
      clk   — 板载晶振 (12 MHz，Tang Nano 系列)
      led0..led5 — 6 位 LED，显示个位齿轮 d0
      led6       — 溢出指示灯
      btn        — 复位按钮（低有效）
    """

    def __init__(self):
        self.clk = Signal()
        self.rst = Signal()
        self.led = Signal(7)        # 7 路 LED：6 路数据 + 1 路溢出
        self.counter = Counter64()

    def elaborate(self, platform):
        m = Module()
        # 12 MHz → ~1 Hz 使能脉冲（26 位分频，12M ≈ 2^23.5，多加几位保慢）
        div = Signal(26)
        en = Signal()
        m.d.comb += en.eq(div.all())
        m.d.sync += div.eq(div + 1)

        m.submodules.counter = self.counter
        m.d.comb += self.counter.en.eq(en)
        # 输出到 LED：d0 占 6 位；第 7 位 = 溢出
        m.d.comb += self.led.eq(Mux(self.counter.overflow, 0x40,
                                     self.counter.d0))
        return m


def export_verilog():
    """导出混元顶层 + 单齿 ALU + 齿轮链 三份 Verilog。
    手写生成器，零依赖（不调用 amaranth.backends.verilog / yosys）。输出到 ./fpga/。"""
    import os
    out_dir = os.path.join(os.path.dirname(__file__), "fpga")
    os.makedirs(out_dir, exist_ok=True)

    # ---- 单齿 ALU ----
    alu_v = """// 混元齿轮核 v0.6 — 单齿 ALU（6 bit 加减，啮合点 = 进位/借位）
// 齿轮传动律：满 64 进一，借位绕回
module GearALU (
    input  wire [5:0] a, b,
    input  wire       sub,          // 0 = 加, 1 = 减
    output wire [5:0] result,
    output wire       carry         // 加法=进位; 减法=取反即借位
);
    wire [7:0] full;
    wire [5:0] b2;
    assign b2    = sub ? (b ^ 6'h3F) : b;      // 减法取 1 的补码
    assign full  = {2'b0, a} + {2'b0, b2} + {7'b0, sub};
    assign result = full[5:0];
    assign carry  = full[6];
endmodule
"""
    with open(os.path.join(out_dir, "gear_alu.v"), "w") as f:
        f.write(alu_v)

    # ---- 三齿轮链 ----
    chain_v = """// 混元齿轮核 v0.6 — 三齿轮啮合链（64 进制计数器）
// 逐级啮合：个位满 64 → 十位进一；十位满 64 → 百位进一；满链溢出
module GearChain (
    input  wire       clk,
    input  wire       en,            // 小齿轮脉冲
    output reg  [5:0] d0,            // 个位
    output reg  [5:0] d1,            // 十位
    output reg  [5:0] d2,            // 百位
    output reg        overflow       // 满 64^3 溢出
);
    always @(posedge clk) begin
        if (en) begin
            if (d0 == 6'd63) begin
                d0 <= 6'd0;
                if (d1 == 6'd63) begin
                    d1 <= 6'd0;
                    if (d2 == 6'd63) begin
                        d2 <= 6'd0;
                        overflow <= 1'b1;
                    end else begin
                        d2 <= d2 + 6'd1;
                    end
                end else begin
                    d1 <= d1 + 6'd1;
                end
            end else begin
                d0 <= d0 + 6'd1;
            end
        end
    end
endmodule
"""
    with open(os.path.join(out_dir, "gear_chain.v"), "w") as f:
        f.write(chain_v)

    # ---- 顶层（12 MHz 分频 → 64 进制计数 → LED）----
    top_v = """// 混元 FPGA 顶层 v0.6 — 12 MHz ↗ 慢闪 LED 演示
// Tang Nano 9K / iCE40UP5K: 12 MHz 晶振 → 26 位分频 → 1Hz 使能 → 64 进制计数 → 7 路 LED
module HunYuanTop (
    input  wire       clk,           // 12 MHz
    input  wire       rst,           // 按键复位（低有效）
    output wire [6:0] led            // [5:0] = 个位齿轮, [6] = 溢出
);
    reg [25: 0] div;
    wire        en;
    wire [5:0]  d0;

    assign en = &div;                // div 全 1 时产生一个使能脉冲

    always @(posedge clk) begin
        if (!rst) div <= 26'd0;
        else      div <= div + 26'd1;
    end

    GearChain u_counter (
        .clk(clk),
        .en(en),
        .d0(d0),
        .d1(),
        .d2(),
        .overflow(/* unused */)
    );

    assign led = d0;

endmodule
"""
    with open(os.path.join(out_dir, "hunyuan_top.v"), "w") as f:
        f.write(top_v)

    # 综合脚本
    synth_sh = """#!/usr/bin/env bash
# 混元齿轮核综合脚本（本地安装 yosys + nextpnr-ice40 + icepack 后执行）
set -e
cd \"$(dirname \"$0\")\"
echo \"=== 综合单齿 ALU ===\"
yosys -p \"read_verilog gear_alu.v; synth_ice40 -top GearALU -json alu.json; stat\"
echo \"=== 综合顶层 ===\"
yosys -p \"read_verilog gear_alu.v; read_verilog gear_chain.v; read_verilog hunyuan_top.v; synth_ice40 -top HunYuanTop -json top.json; stat\"
echo \"=== 布局布线（Tang Nano 9K，iCE40UP5K）===\"
nextpnr-ice40 --json top.json --asc top.asc --freq 12 --package sg48 --pcf pins.pcf
icepack top.asc top.bin
echo \"=== 完成: top.bin 已生成。烧录: iceprog top.bin ===\"
"""
    sh_path = os.path.join(out_dir, "synthesize.sh")
    with open(sh_path, "w") as f:
        f.write(synth_sh)
    os.chmod(sh_path, 0o755)

    # 引脚约束
    pcf = """# 混元顶层引脚约束（Tang Nano 9K / iCE40UP5K）
set_io clk    52
set_io rst     2
set_io led[0] 10
set_io led[1] 11
set_io led[2] 12
set_io led[3] 13
set_io led[4] 14
set_io led[5] 15
set_io led[6] 16
"""
    with open(os.path.join(out_dir, "pins.pcf"), "w") as f:
        f.write(pcf)

    return ["gear_alu.v", "gear_chain.v", "hunyuan_top.v", "synthesize.sh", "pins.pcf"]


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


# ---------------------------------------------------------------- 公共 API（供统一入口调用）
def demo_gear():
    """运行齿轮核仿真 + 导出 Verilog，返回输出行列表。"""
    import io, contextlib
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main()
    lines = buf.getvalue().splitlines()
    # v0.6: 导出 Verilog（无需外部工具）
    try:
        files = export_verilog()
        lines.append("")
        lines.append("[v0.6] Verilog 已导出到 fpga/（" + ", ".join(files) + "）")
        lines.append("       综合脚本: fpga/synthesize.sh（本地有 yosys + nextpnr 时执行）")
        lines.append("       引脚约束: fpga/pins.pcf")
    except Exception as e:
        lines.append(f"[v0.6] Verilog 导出失败: {e}")
    return lines


if __name__ == "__main__":
    main()
