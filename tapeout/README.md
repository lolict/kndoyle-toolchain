# 混元 CPU 流片指引 v1.0

## 概述

本目录含混元 RISC CPU 的 ASIC 流片必备文件：

| 文件 | 作用 |
|------|------|
| `caravel_wrapper.v` | Caravel 用户项目顶层（SoC + GPIO） |
| `../cpu/hunyuan_cpu.v` | CPU 核心 |
| `../cpu/hunyuan_soc.v` | SoC 顶层（CPU + ROM + SRAM + UART） |
| `sram_2kbyte.v` | SkyWater 2KB SRAM 行为模型 |

## 流片路径

### 方案 A: Efabless Caravel + OpenMPW（推荐，免费流片）

OpenMPW 计划由 Google/SkyWater 赞助，**零费用**流片 SkyWater 130nm。

1. **注册 Efabless Caravel**: https://efabless.com
2. **克隆 Caravel 用户项目模板**:
   ```bash
   git clone https://github.com/efabless/caravel_user_project.git
   cd caravel_user_project
   ```
3. **替换 Verilog**:
   ```bash
   cp rtl/user_project_wrapper.v rtl/user_project_wrapper.v.bak
   cp caravel_wrapper.v rtl/user_project_wrapper.v
   mkdir rtl/hunyuan
   cp ../cpu/*.v rtl/hunyuan/
   ```
4. **更新 config.tcl**, 设置 CLOCK/CLOCK_PORT。
5. **OpenLane 综合 + APR**: `make user_project_wrapper`
6. **提交 Shuttle**: 通过 Efabless MPW 页面提交 GDS。

### 方案 B: 自建合成（学习用）

```bash
yosys -p "synth_ice40 -top hunyuan_cpu -json cpu.json" \
    ../cpu/hunyuan_cpu.v
nextpnr-ice40 --json cpu.json --asc cpu.asc
icepack cpu.asc cpu.bin
# → 烧录到 iCE40 FPGA 验证
```

## 综合约束

```
Clock:   100 MHz (10 ns)
Reset:   低有效
GPIO:    32 路 (使用 ~20 路)
面积:    < 1.2 mm^2 (SkyWater 130nm)
功耗:    估计 < 50 mW
```

## 指令格式 (32 bit RISC)

```
[31:26] opcode   (6 bit = 64 码位, 补足律)
[25:22] rd
[21:18] rs1
[17:14] rs2
[13:0]  imm14    (14 bit 立即数)
```

## 内存映射

```
0x00000000  ROM  (4 KB)
0x00001000  SRAM (16 KB)
0x20000000  UART 数据
0x20000004  UART 状态
0x20000008  GPIO 输出
0x2000000C  GPIO 输入
```

## 本地验证

```bash
iverilog -o sim.vvp ../cpu/hunyuan_cpu.v ../cpu/tb_hunyuan_cpu.v
vvp sim.vvp
# 预期: TEST PASSED: Sigma(1..100) = 5050
```

## 已知折中

- 多周期: 牺牲单周期吞吐, 追求最低面积 (~15K gates)
- 无流水: 无 hazard 逻辑
- 固定地址解码: 简化总线矩阵

---

*HunYuan v1.0 — from software to silicon.*