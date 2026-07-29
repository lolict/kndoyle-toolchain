// ============================================================================
// 混元 SoC v1.1 — 流水线 CPU + Cache + 外设
// ============================================================================
// 内存映射:
//   0x0000_0000..0x0000_0FFF  ROM (4KB)
//   0x0000_1000..0x0000_4FFF  SRAM (16KB)
//   0x2000_0000               Wishbone 主接口 (扩展)
//   0x3000_0000               Timer
//   0x3000_0010               PWM
//   0x3000_0020               I2C
//   0x3000_0030               DMA
// ============================================================================

`timescale 1ns / 1ps

module hunyuan_soc_v11 (
    input  wire        clk,
    input  wire        rst_n,

    // 外部 Wishbone 主接口
    output wire        m2s_cyc,
    output wire        m2s_stb,
    output wire        m2s_we,
    output wire [3:0]  m2s_sel,
    output wire [31:0] m2s_adr,
    output wire [31:0] m2s_wdat,
    input  wire [31:0] m2s_rdat,
    input  wire        m2s_ack,

    // UART
    output wire        uart_tx,
    input  wire        uart_rx,

    // GPIO
    input  wire [5:0]  sense,
    output wire [5:0]  emit,

    // 外设引脚
    inout  wire        i2c_sda,
    inout  wire        i2c_scl,
    output wire [2:0]  pwm_out,

    // 中断
    input  wire        timer_irq,
    input  wire        dma_irq,

    // 调试
    output wire [2:0]  debug_led
);

    // =====================================================================
    // CPU (流水线)
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

    hunyuan_cpu_pipelined u_cpu (
        .clk(clk), .rst_n(rst_n),
        .ibus_cyc(ibus_cyc), .ibus_stb(ibus_stb), .ibus_adr(ibus_adr),
        .ibus_dat(ibus_rdat), .ibus_ack(ibus_ack),
        .dbus_cyc(dbus_cyc), .dbus_stb(dbus_stb), .dbus_we(dbus_we),
        .dbus_sel(dbus_sel), .dbus_adr(dbus_adr),
        .dbus_dat_w(dbus_wdat), .dbus_dat_r(dbus_rdat), .dbus_ack(dbus_ack),
        .sense(sense), .emit(emit), .irq(),
        .pc_show(pc_show), .halt(halt)
    );

    // =====================================================================
    // I-Cache
    // =====================================================================
    wire        ic_req;
    wire [31:0] ic_addr;
    wire [31:0] ic_rdata;
    wire        ic_ready;
    wire        ic_miss;

    wire        ic_mem_cyc, ic_mem_stb;
    wire [31:0] ic_mem_addr;
    wire [31:0] ic_mem_rdata;
    wire        ic_mem_ack;

    icache u_icache (
        .clk(clk), .rst_n(rst_n),
        .cpu_addr(ibus_adr), .cpu_req(ibus_cyc & ibus_stb),
        .cpu_rdata(ibus_rdat), .cpu_ready(ibus_ack), .cpu_miss(ic_miss),
        .mem_cyc(ic_mem_cyc), .mem_stb(ic_mem_stb), .mem_addr(ic_mem_addr),
        .mem_rdata(ic_mem_rdata), .mem_ack(ic_mem_ack)
    );

    // =====================================================================
    // D-Cache
    // =====================================================================
    wire        dc_ready;
    wire [31:0] dc_rdata;

    wire        dc_mem_cyc, dc_mem_stb, dc_mem_we;
    wire [31:0] dc_mem_addr, dc_mem_wdata;
    wire [31:0] dc_mem_rdata;
    wire        dc_mem_ack;

    dcache u_dcache (
        .clk(clk), .rst_n(rst_n),
        .cpu_addr(dbus_adr), .cpu_req(dbus_cyc & dbus_stb),
        .cpu_we(dbus_we), .cpu_sel(dbus_sel), .cpu_wdata(dbus_wdat),
        .cpu_rdata(dbus_rdat), .cpu_ready(dbus_ack),
        .mem_cyc(dc_mem_cyc), .mem_stb(dc_mem_stb), .mem_we(dc_mem_we),
        .mem_addr(dc_mem_addr), .mem_wdata(dc_mem_wdata),
        .mem_rdata(dc_mem_rdata), .mem_ack(dc_mem_ack)
    );

    // =====================================================================
    // 总线矩阵: 缓存 miss → 内存/外设
    // =====================================================================
    wire        mem_cyc  = ic_mem_cyc | dc_mem_cyc;
    wire        mem_stb  = ic_mem_stb | dc_mem_stb;
    wire        mem_we   = dc_mem_we;
    wire [31:0] mem_addr = ic_mem_cyc ? ic_mem_addr : dc_mem_addr;
    wire [31:0] mem_wdat = dc_mem_wdata;

    // 地址解码
    wire        rom_hit   = (mem_addr[31:12] == 20'h0000_0);
    wire        sram_hit  = (mem_addr[31:12] == 20'h0000_1);
    wire        timer_hit = (mem_addr[31:12] == 20'h3000_0) && (mem_addr[7:4] == 4'h0);
    wire        pwm_hit   = (mem_addr[31:12] == 20'h3000_0) && (mem_addr[7:4] == 4'h1);
    wire        i2c_hit   = (mem_addr[31:12] == 20'h3000_0) && (mem_addr[7:4] == 4'h2);
    wire        dma_hit   = (mem_addr[31:12] == 20'h3000_0) && (mem_addr[7:4] == 4'h3);
    wire        ext_hit   = !(rom_hit | sram_hit | timer_hit | pwm_hit | i2c_hit | dma_hit);

    // 内存模型
    reg [31:0] rom  [0:1023];
    reg [31:0] sram [0:4095];

    wire [9:0]  rom_a  = mem_addr[11:2];
    wire [11:0] sram_a = mem_addr[13:2];

    wire [31:0] rom_rdata  = rom[rom_a];
    wire [31:0] sram_rdata = sram[sram_a];

    // 外设 ack
    wire timer_ack, pwm_ack, i2c_ack, dma_ack;

    wire        periph_stb = mem_stb & (timer_hit | pwm_hit | i2c_hit | dma_hit);
    wire [7:0]  periph_addr= mem_addr[7:0];

    // 外设读数据
    wire [31:0] timer_rdata, pwm_rdata, i2c_rdata, dma_rdata;

    // 总线 ack
    wire        mem_ack = (rom_hit | sram_hit) ? (mem_cyc & mem_stb) :
                          timer_ack | pwm_ack | i2c_ack | dma_ack |
                          (ext_hit ? m2s_ack : 0);

    wire [31:0] mem_rdata = rom_hit  ? rom_rdata :
                            sram_hit ? sram_rdata :
                            timer_hit? timer_rdata :
                            pwm_hit  ? pwm_rdata :
                            i2c_hit  ? i2c_rdata :
                            dma_hit  ? dma_rdata :
                            m2s_rdat;

    // 写 SRAM
    always @(posedge clk)
        if (mem_cyc && mem_stb && mem_we && sram_hit)
            sram[sram_a] <= mem_wdat;

    // 返回给 cache
    assign ic_mem_rdata = mem_rdata;
    assign ic_mem_ack   = mem_ack & ic_mem_cyc;
    assign dc_mem_rdata = mem_rdata;
    assign dc_mem_ack   = mem_ack & dc_mem_cyc;

    // 外部总线
    assign m2s_cyc = mem_cyc & ext_hit;
    assign m2s_stb = mem_stb & ext_hit;
    assign m2s_we  = mem_we;
    assign m2s_sel = 4'hF;
    assign m2s_adr = mem_addr;
    assign m2s_wdat= mem_wdat;

    // =====================================================================
    // 外设实例
    // =====================================================================
    timer_regs #(.N(2)) u_timer (
        .clk(clk), .rst_n(rst_n),
        .addr(periph_addr), .we(mem_we), .wdata(mem_wdat),
        .rdata(timer_rdata), .stb(periph_stb & timer_hit), .ack(timer_ack),
        .irq(/* to cpu irq */)
    );

    pwm_regs #(.N(3)) u_pwm (
        .clk(clk), .rst_n(rst_n),
        .addr(periph_addr), .we(mem_we), .wdata(mem_wdat),
        .rdata(pwm_rdata), .stb(periph_stb & pwm_hit), .ack(pwm_ack),
        .pwm_out(pwm_out)
    );

    i2c_master_regs u_i2c (
        .clk(clk), .rst_n(rst_n),
        .addr(periph_addr), .we(mem_we), .wdata(mem_wdat),
        .rdata(i2c_rdata), .stb(periph_stb & i2c_hit), .ack(i2c_ack),
        .sda(i2c_sda), .scl(i2c_scl)
    );

    dma_regs u_dma (
        .clk(clk), .rst_n(rst_n),
        .addr(periph_addr), .we(mem_we), .wdata(mem_wdat),
        .rdata(dma_rdata), .stb(periph_stb & dma_hit), .ack(dma_ack),
        .mem_cyc(), .mem_stb(), .mem_we(), .mem_addr(), .mem_wdata(),
        .mem_rdata(0), .mem_ack(0), .done_irq(dma_irq)
    );

    // =====================================================================
    // UART (简化)
    // =====================================================================
    assign uart_tx = 1'b1;   // 默认高

    // 调试 LED
    assign debug_led = {halt, ibus_cyc, timer_ack};

endmodule
