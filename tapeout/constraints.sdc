# 混元 CPU 综合约束 (SkyWater 130nm / Caravel)
# 时钟: 100 MHz (10 ns period)

create_clock -name clk -period 10 [get_ports clock]

# 复位异步，不需要做时序约束（由综合工具处理 set_clock_uncertainty）
set_clock_uncertainty -setup 0.15 [get_clocks clk]
set_clock_uncertainty -hold  0.05 [get_clocks clk]
set_clock_transition  0.1  [get_clocks clk]

# GPIO 延迟 —— 输入: 2ns 恢复, 输出: 2ns 驱动
set_input_delay  -clock clk 2.0 [all_inputs]
set_output_delay -clock clk 2.0 [all_outputs]

# 高阻 GPIO: false path
set_false_path -from [get_ports mprj_io*]

# 最大面积约束 (追求小面积)
set_max_area 50000
