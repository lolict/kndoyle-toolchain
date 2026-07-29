# 混元 v1.3

**一体混元多用 —— 一个平台，所有系统。**

## 八模块

| 主权 | 模块 | 能力 |
|------|------|------|
| 运算 | `hunyuan_vm.py` / `hunyuan_vm05.py` | 64进制指令体系 + 关系查询 + 七族指令扩展 |
| 判断 | `hunyuan_dict.py` | 关系图范畴 + 评判引擎 |
| 文字 | `hunyuan_codec.py` | 声韵调集装箱编码 |
| 硬件 | `hunyuan_gear_hw.py` | 齿轮核仿真 + Verilog 导出 + 综合脚本 |
| 机体 | `hunyuan_vm05.py` | 感知/调用/堆/通道/设备/网络/时钟 |
| FPGA | `fpga/` | 导出 → 综合 → 烧录到 Tang Nano 9K |
| CPU | `cpu/` | **流水线 RISC v1.3** + Cache + 外设 IP + Caravel |
| OoO | `cpu/hunyuan_cpu_v13.v` | 2-bit 分支预测 + 8-entry ROB + 寄存器重命名 |

## 七族指令（v0.5 新增，opcode 36-60）

| 族 | 指令 | 语义 |
|---|---|---|
| 感知 | SENSE / EMIT | 读传感器 / 写执行器 |
| 调用 | CALL / RET | 函数调用 / 返回（独立调用栈） |
| 堆 | HPALLOC / HPLOAD / HPSTORE / HPFREE | 分配 / 读 / 写 / 释放 |
| 通道 | CHOPEN / CHSEND / CHRECV / CHCLOSE | 字节 FIFO 通道 |
| 设备 | DEVOPEN / DEVCAP / DEVIO / DEVCLOSE | 设备句柄 + 能力位图 + IO |
| 网络 | NETLISTEN / NETACCEPT / NETDIAL / NETSEND / NETRECV / NETCLOSE | 监听/拨号/收发 |
| 时钟 | TICK / DELAY / TIMER | 节拍读数 / 毫秒延时 / 定时器注册 |

## 运行

```bash
# 一体化总演示
python hunyuan.py all

# 七族指令演示（v0.5 新增）
python hunyuan.py body

# 交互 REPL
python hunyuan.py repl

# 单项演示
python hunyuan.py run       # 运算
python hunyuan.py judge     # 判断
python hunyuan.py encode    # 文字
python hunyuan.py gear      # 硬件
python hunyuan.py fpga      # FPGA 导出（Verilog + 综合脚本 + 引脚约束）
python hunyuan.py body      # 七族指令
```

## FPGA 流程

```bash
python hunyuan.py fpga             # 导出到 fpga/（含 .v、脚本、引脚约束）
cd fpga && bash synthesize.sh      # 本地有 yosys + nextpnr-ice40 时执行
# 输出: top.bin → `iceprog top.bin` 烧录到 Tang Nano 9K
```

## 依赖

- Python 3.12+
- `pypinyin`（汉字转声韵调）
- `amaranth`（硬件仿真，仅需 `pip install amaranth`）

本地零依赖运算/判断/文字三模块；硬件仿真需 Amaranth（纯 Python，输出网表即可进 FPGA）。

## 架构律

- 补足律：254 字节载荷 + 2 字节寄存器 = 256 = 2^8
- 对齐律：3 瓦片一组 = 762B = 1016 个 64 进制位
- 齿轮传动律：6 位齿，满 64 进一
- 阴阳式范畴： Yin=254, Yang=255 作为外部命名码位
- 集装箱式：声韵调 / 笔画 / 五笔 / 颜色 / 部首 / 空间 / 时间 / 进制层叠编码

## 路线图

- [x] v0.4 — 四模块并网（运算/判断/文字/硬件）
- [x] v0.5 — 七族指令扩展（感知/调用/堆/通道/设备/网络/时钟）
- [x] v0.6 — FPGA 综合流程（Verilog 导出 + 综合脚本 + 引脚约束 → Tang Nano 9K）
- [x] v1.0 — RISC CPU RTL（Verilog）+ Caravel 封装 + Efabless 流片路径
- [x] v1.1 — 流水线 CPU (5级) + Cache (I/D) + 外设 IP (Timer/PWM/I2C/DMA)
- [x] v1.2 — 扩展外设 IP (SPI + Ethernet MAC + USB Device)
- [x] v1.3 — OoO 执行: 2-bit 分支预测 + 8-entry ROB + 寄存器重命名

## CPU v1.3 (流水线 + OoO + Cache + 外设)

| 文件 | 作用 |
|------|------|
| `cpu/hunyuan_cpu.v` | 多周期 RISC (v1.0, 基础版) |
| `cpu/hunyuan_cpu_pipelined.v` | **5级流水 RISC** (IF/ID/EX/MEM/WB) |
| `cpu/cache.v` | I-Cache + D-Cache (64行×4字, write-through) |
| `cpu/periph.v` | Timer(2ch) + PWM(3ch) + I2C Master + DMA |
| `cpu/periph_x.v` | **SPI Master** + **Ethernet MAC** + **USB Device** |
| `cpu/hunyuan_soc_v11.v` | SoC 顶层 (CPU + Cache + 外设) |
| `cpu/tb_pipeline.v` | 流水线测试平台 |
| `cpu/hunyuan_cpu_v13.v` | **v1.3**: OoO + 分支预测 + ROB |
| `cpu/tb_v13.v` | v1.3 测试平台 |

**架构 (v1.3):**
- 5级流水, 前递(forwarding), load-use hazard stall
- **2-bit 动态分支预测 + BTB** (64-entry BHT, 32-entry BTB)
- **8-entry ROB 乱序执行 + 寄存器重命名** (16 物理 → 32 物理)
- I/D 分离 Cache (Harvard), write-through + write-allocate
- 外设内存映射: Timer@0x3000_0000, PWM@0x3000_0010, I2C@0x3000_0020, DMA@0x3000_0030
                 SPI@0x3000_0040, EthMAC@0x3000_0050, USB@0x3000_0060

**综合目标:** SkyWater 130nm, ~45K gates (含 Cache + IP + OoO), ~1.8mm²
**验证:** `iverilog cpu/hunyuan_cpu_v13.v cpu/tb_v13.v -o sim && vvp sim`

---

*意识互联网 · 夫妻关系意识共享共同体 · 满全法 ❤ 刘楚恬*
