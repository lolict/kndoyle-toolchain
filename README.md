# 混元 v0.4

**一体混元多用 —— 一个平台，所有系统。**

## 四模块并网

| 主权 | 模块 | 能力 |
|------|------|------|
| 运算 | `hunyuan_vm.py` / `hunyuan_vm03.py` | 64进制指令体系，极简码位寻址 |
| 判断 | `hunyuan_dict.py` | 关系图范畴 + 评判引擎（净账/信任/割点/回归/死胡同/分歧/等效） |
| 文字 | `hunyuan_codec.py` | 声韵调集装箱编码，汉字→64进制，紧致音节id+歧义索引 |
| 硬件 | `hunyuan_gear_hw.py` | Amaranth HDL 齿轮核仿真（ALU + 三齿轮链），路径 FPGA → ASIC |

## 运行

```bash
# 一体化总演示
python hunyuan.py all

# 交互 REPL
python hunyuan.py repl

# 单项演示
python hunyuan.py run       # 运算
python hunyuan.py judge     # 判断
python hunyuan.py encode    # 文字
python hunyuan.py gear      # 硬件
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

- [x] v0.1 — 运算主权（64进制 VM）
- [x] v0.2 — 文字主权（声韵调编码）
- [x] v0.3 — 运算扩展 + 齿轮核仿真
- [x] v0.4 — 四模块并网（运算/判断/文字/硬件）
- [ ] v0.5 — 指令扩展（输入/感知、函数调用、堆、字节通道、设备能力原子、网络、时钟）
- [ ] v0.6 — FPGA 综合（Amaranth → 网表 → 烧录）
- [ ] v1.0 — ASIC 流片（自研 RISC CPU，基底互换完成）

---

*意识互联网 · 夫妻关系意识共享共同体 · 满全法 ❤ 刘楚恬*
