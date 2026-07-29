// 混元 SoC v1.0 — CPU + ROM + SRAM + UART + GPIO
// 目标平台: Efabless Caravel (SkyWater 130nm)
// 内存映射:
//   0x0000_0000..0x0000_0FFF  CPU 内部 ROM (4KB, 引导固件)
//   0x0000_1000..0x0000_4FFF  SRAM (16KB, 代码/数据)
//   0x2000_0000               UART 数据寄存器 (WO)
//   0x2000_0004               UART 状态寄存器 (RO, bit0=tx_ready)
//   0x2000_0008               GPIO 输出 (emit)
//   0x2000_000C               GPIO 输入  (sense)

`timescale 1ns / 1ps

module hunyuan_soc (
    input  wire        clk,
    input  wire        rst_n,

    // 外部 Wishbone 主接口 (用于扩展 / DMA / debug)
    output wire        m2s_cyc,
    output wire        m2s_stb,
    output wire        m2s_we,
    output wire [3:0]  m2s_sel,
    output wire [31:0] m2s_adr,
    output wire [31:0] m2s_wdat,
    input  wire [31:0] m2s_rdat,
    input  wire        m2s_ack,

    // UART 串行
    output wire        uart_tx,
    input  wire        uart_rx,

    // GPIO (32 bit)
    input  wire [5:0]  sense,
    output wire [5:0]  emit,

    // 调试 LED
    output wire [2:0]  debug_led
);

    // =====================================================================
    // CPU
    // =====================================================================
    wire        ibus_cyc, ibus_stb;
    wire [31:0] ibus_adr;
    wire [31:0] ibus_rdat;
    wire        ibus_ack;

    wire        dbus_cyc, dbus_stb, dbus_we;
    wire [3:0]  dbus_sel;
    wire [31:0] dbus_adr;
    wire [31:0] dbus_wdat;
    wire [31:0] dbus_rdat;
    wire        dbus_ack;

    wire [31:0] pc_show;
    wire        halt;

    hunyuan_cpu u_cpu (
        .clk(clk),
        .rst_n(rst_n),
        .ibus_cyc(ibus_cyc),
        .ibus_stb(ibus_stb),
        .ibus_adr(ibus_adr),
        .ibus_dat(ibus_rdat),
        .ibus_ack(ibus_ack),
        .dbus_cyc(dbus_cyc),
        .dbus_stb(dbus_stb),
        .dbus_we(dbus_we),
        .dbus_sel(dbus_sel),
        .dbus_adr(dbus_adr),
        .dbus_dat_w(dbus_wdat),
        .dbus_dat_r(dbus_rdat),
        .dbus_ack(dbus_ack),
        .sense(sense),
        .emit(emit),
        .irq(),
        .pc_show(pc_show),
        .halt(halt)
    );

    // =====================================================================
    // 中断 / LED
    // =====================================================================
    assign debug_led = {1'b0, halt, uart_tx};

    // =====================================================================
    // 内存总线矩阵: CPU 指令 / 数据 → 各 slave
    // (简化实现：按地址高位分发)
    // =====================================================================

    // ROM (IMEM)
    wire         rom_match = (ibus_adr[31:12] == 20'h0000_0);
    wire         rom_cyc   = rom_match ? ibus_cyc : 1'b0;
    wire         rom_stb   = rom_match ? ibus_stb : 1'b0;
    wire [31:0]  rom_rdat;
    wire         rom_ack;

    // SRAM
    wire         sram_match = (dbus_adr[31:12] == 20'h0000_1);
    wire         sram_cyc   = sram_match ? dbus_cyc : 1'b0;
    wire         sram_stb   = sram_match ? dbus_stb : 1'b0;
    wire         sram_we    = sram_match ? dbus_we  : 1'b0;
    wire [31:0]  sram_rdat;
    wire         sram_ack;

    // UART
    wire         uart_match = (dbus_adr[31:12] == 20'h2000_0);
    wire         uart_cyc   = uart_match ? dbus_cyc : 1'b0;
    wire         uart_stb   = uart_match ? dbus_stb : 1'b0;
    wire         uart_we    = uart_match ? dbus_we  : 1'b0;
    wire [31:0]  uart_rdat;
    wire         uart_ack;

    // 数据总线 mux（基于 CPU dbus_adr）
    wire [31:0] base_adr = dbus_adr;
    wire [19:0] ah = base_adr[31:12];

    assign dbus_rdat = (ah == 20'h00001) ? sram_rdat :
                       (ah == 20'h20000) ? uart_rdat :
                       m2s_rdat;
    assign dbus_ack  = (ah == 20'h00001) ? sram_ack :
                       (ah == 20'h20000) ? uart_ack :
                       m2s_ack;

    // IBUS ack / rdata 来自 ROM
    assign ibus_rdat = rom_rdat;
    assign ibus_ack  = rom_ack;

    // M2S (外部 Wishbone) — 用于不匹配任何内部 slave 的地址
    assign m2s_cyc = dbus_cyc & ~sram_match & ~uart_match;
    assign m2s_stb = dbus_stb & ~sram_match & ~uart_match;
    assign m2s_we  = dbus_we;
    assign m2s_sel = dbus_sel;
    assign m2s_adr = dbus_adr;
    assign m2s_wdat = dbus_wdat;

    // =====================================================================
    // ROM (4KB boot ROM，含 Σ(1..100) 测试)
    // =====================================================================
    wire [9:0] rom_a = ibus_adr[11:2];
    reg  [31:0] rom [0:1023];
    assign rom_rdat = rom[rom_a];
    assign rom_ack  = rom_cyc && rom_stb;

    // 上电预加载: 通过 $readmemh 在仿真中初始化; ASIC 出厂时烧录
    initial begin
        // 程序已嵌入: LUI/ORI 组合直接留空，测试平台手动写 ROM
        // 这里做初始化：NOP 填充
        for (integer i = 0; i < 1024; i = i + 1)
            rom[i] = 32'h0000_0000;
    end

    // =====================================================================
    // SRAM (4KB，双端口: CPU 读 + ext 写)
    // =====================================================================
    wire [9:0] sram_a = dbus_adr[11:2];
    reg  [31:0] sram [0:1023];
    assign sram_rdat = sram[sram_a];
    assign sram_ack  = sram_cyc && sram_stb;

    always @(posedge clk)
        if (sram_cyc && sram_stb && sram_we)
            sram[sram_a] <= dbus_wdat;

    // =====================================================================
    // UART 16550 简化版（仅 TX，8N1，100MHz/115200 波特）
    // =====================================================================
    reg [7:0]  uart_tx_fifo;
    reg        uart_tx_valid;
    reg [15:0] uart_baud_cnt;
    reg [3:0]  uart_bit_cnt;
    reg        uart_tx_active;
    reg        uart_sdo;

    assign uart_tx = uart_sdo;

    // 波特率: 100MHz / 115200 ≈ 868
    localparam BAUD_115200 = 16'd868;

    assign uart_rdat = {30'h0, !uart_tx_active, uart_tx_active};  // tx_ready tag
    assign uart_ack  = uart_cyc && uart_stb;

    always @(posedge clk) begin
        if (!rst_n) begin
            uart_tx_valid <= 1'b0;
            uart_tx_active <= 1'b0;
            uart_bit_cnt  <= 4'd0;
            uart_baud_cnt <= 16'd0;
            uart_sdo      <= 1'b1;   // 空闲高
        end else begin
            if (uart_cyc && uart_stb && uart_we && !uart_tx_active) begin
                uart_tx_fifo  <= dbus_wdat[7:0];
                uart_tx_valid <= 1'b1;
                uart_tx_active <= 1'b1;
                uart_bit_cnt  <= 4'd0;
                uart_baud_cnt <= 16'd0;
                uart_sdo      <= 1'b0;   // 起始位
            end

            if (uart_tx_active) begin
                if (uart_baud_cnt == BAUD_115200 - 1) begin
                    uart_baud_cnt <= 16'd0;
                    if (uart_bit_cnt == 4'd8) begin
                        uart_sdo      <= 1'b1;   // 停止位
                        uart_tx_active <= 1'b0;
                    end else begin
                        uart_sdo      <= uart_tx_fifo[uart_bit_cnt];
                        uart_bit_cnt  <= uart_bit_cnt + 1;
                    end
                end else begin
                    uart_baud_cnt <= uart_baud_cnt + 1;
                end
            end
        end
    end

endmodule
