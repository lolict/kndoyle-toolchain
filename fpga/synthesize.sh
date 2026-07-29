#!/usr/bin/env bash
# 混元齿轮核综合脚本（本地安装 yosys + nextpnr-ice40 + icepack 后执行）
set -e
cd "$(dirname "$0")"
echo "=== 综合单齿 ALU ==="
yosys -p "read_verilog gear_alu.v; synth_ice40 -top GearALU -json alu.json; stat"
echo "=== 综合顶层 ==="
yosys -p "read_verilog gear_alu.v; read_verilog gear_chain.v; read_verilog hunyuan_top.v; synth_ice40 -top HunYuanTop -json top.json; stat"
echo "=== 布局布线（Tang Nano 9K，iCE40UP5K）==="
nextpnr-ice40 --json top.json --asc top.asc --freq 12 --package sg48 --pcf pins.pcf
icepack top.asc top.bin
echo "=== 完成: top.bin 已生成。烧录: iceprog top.bin ==="
