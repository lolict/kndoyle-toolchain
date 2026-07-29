// ============================================================================
// 混元 SoC → Caravel 用户项目封装
// ============================================================================
// 目标: Efabless Caravel / SkyWater 130nm OpenMPW
//
// 本模块把混元 SoC 接上 Caravel 的:
//   - 管理核心区 (power, clock, reset, SPI flash, UART)
//   - 用户 GPIO 32 位 (mprj_io)
//   -  Wishbone / LA (逻辑分析仪) 调试接口
//   -  IRQ 中断输出
//
// 综合流程:
//   1. OpenLane 平坦化综合 (yosys + abc)
//   2.  floorplan (io_init / place_io / tapcell / power_grid)
//   3.  CTS +  place + route (OpenROAD / FastRoute)
//   4.  提取 → 签核 (Magic, Netgen, SPEF, STA)
//
// 参考: github.com/efabless/caravel (用户项目模板)
// ============================================================================

`timescale 1ns / 1ps

module caravel_wrapper (
    // 电源 (来自 Caravel padframe)
    inout wire vdda1,     // 1.8V 模拟电源
    inout wire vdda2,
    inout wire vssa1,     // 模拟地
    inout wire vssa2,
    inout wire vccd1,     // 1.8V 数字电源
    inout wire vccd2,
    inout wire vssd1,     // 数字地
    inout wire vssd2,

    // 系统
    input  wire            clock,        // Caravel 系统时钟
    input  wire            resetb,       // 低有效复位

    // 用户 GPIO 32 位 (带 OE)
    inout  wire [31:0]     mprj_io,
    input  wire [31:0]     mprj_io_ieb,   // 输入使能 (高=输入模式)

    // 逻辑分析仪 (debug)
    input  wire [31:0]     la_data_in,
    output wire [31:0]     la_data_out,
    input  wire [31:0]     la_oenb,      // 输出使能 (低=驱动)

    // 中断
    output wire [2:0]      irq,

    // SPI flash 直通 (若用 SPI 启动)
    output wire            spimemio_sck,
    output wire            spimemio_csb,
    inout  wire            spimemio_0,
    inout  wire            spimemio_1,
    inout  wire            spimemio_2,
    inout  wire            spimemio_3
);

    // =====================================================================
    // GPIO 映射
    //   mprj_io[5:0]  ← emit (6 路执行器)
    //   mprj_io[11:6] → sense (6 路传感器输入)
    //   mprj_io[12]   ← uart_tx (串口发送)
    //   mprj_io[13]   → uart_rx (串口接收)
    //   mprj_io[16:13]← debug_led (混元调试灯)
    //   其余 GPIO: 高阻 / 保留
    // =====================================================================

    // 外设信号
    wire [5:0]  sense;
    wire [5:0]  emit;
    wire        uart_rx;
    wire        uart_tx;
    wire [2:0]  debug_led;

    // GPIO 双向缓冲 (IOBUF 行为)
    // 输出使能: emit 和 uart_tx 需要驱动
    wire [5:0]  emit_oe  = 6'h3F;        // 始终输出
    wire        uart_tx_oe = 1'b1;       // 始终输出
    wire [2:0]  led_oe    = 3'h7;        // debug LED 始终输出

    // 三态缓冲 (行为级；ASIC 单元库会替换为真实 IO 单元)
    // emit[5:0] → mprj_io[5:0]
    assign mprj_io[0] = emit_oe[0] ? emit[0] : 1'bz;
    assign mprj_io[1] = emit_oe[1] ? emit[1] : 1'bz;
    assign mprj_io[2] = emit_oe[2] ? emit[2] : 1'bz;
    assign mprj_io[3] = emit_oe[3] ? emit[3] : 1'bz;
    assign mprj_io[4] = emit_oe[4] ? emit[4] : 1'bz;
    assign mprj_io[5] = emit_oe[5] ? emit[5] : 1'bz;

    // sense 来自输入
    assign sense = mprj_io[11:6] & ~mprj_io_ieb[11:6];

    // uart_tx → mprj_io[12]
    assign mprj_io[12] = uart_tx_oe ? uart_tx : 1'bz;
    // uart_rx ← mprj_io[13]
    assign uart_rx = mprj_io[13];

    // debug_led → mprj_io[16:14]
    assign mprj_io[14] = led_oe[0] ? debug_led[0] : 1'bz;
    assign mprj_io[15] = led_oe[1] ? debug_led[1] : 1'bz;
    assign mprj_io[16] = led_oe[2] ? debug_led[2] : 1'bz;

    // 其余 GPIO: 高阻
    generate
        genvar gi;
        for (gi = 17; gi < 32; gi = gi + 1)
            assign mprj_io[gi] = 1'bz;
        // 保留位
        assign mprj_io[13] = 1'bz;    // uart_rx 是输入
    endgenerate

    // 中断 (低有效，扩展预留)
    assign irq = 3'b111;              // 无中断

    // LA (透传部分信号用于片上 debug)
    assign la_data_out[5:0]  = emit;
    assign la_data_out[11:6] = sense;
    assign la_data_out[12]   = uart_tx;
    assign la_data_out[13]   = uart_rx;
    assign la_data_out[31:14]= 18'h0;

    // SPI flash 直通 (浮空，由 Caravel core 驱动)
    assign spimemio_sck = 1'bz;
    assign spimemio_csb = 1'bz;
    assign spimemio_0   = 1'bz;
    assign spimemio_1   = 1'bz;
    assign spimemio_2   = 1'bz;
    assign spimemio_3   = 1'bz;

    // =====================================================================
    // 混元 SoC 实例
    // =====================================================================
    wire m2s_cyc, m2s_stb, m2s_we;
    wire [3:0]  m2s_sel;
    wire [31:0] m2s_adr, m2s_wdat, m2s_rdat;
    wire        m2s_ack;

    // 外部 Wishbone 暂时无连接 (所有访问走片内)
    assign m2s_rdat = 32'h0;
    assign m2s_ack  = 1'b0;

    hunyuan_soc u_soc (
        .clk(clock),
        .rst_n(resetb),
        .m2s_cyc(m2s_cyc),
        .m2s_stb(m2s_stb),
        .m2s_we(m2s_we),
        .m2s_sel(m2s_sel),
        .m2s_adr(m2s_adr),
        .m2s_wdat(m2s_wdat),
        .m2s_rdat(m2s_rdat),
        .m2s_ack(m2s_ack),
        .uart_tx(uart_tx),
        .uart_rx(uart_rx),
        .sense(sense),
        .emit(emit),
        .debug_led(debug_led)
    );

endmodule
