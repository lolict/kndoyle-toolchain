// ============================================================================
// 混元扩展外设 IP v1.2 — SPI + Ethernet + USB
// ============================================================================
// 新增外设:
//   SPI Master (4 线, 主模式, 可连接 flash / 传感器 / 屏幕)
//   Ethernet MAC (简化 L2, 10/100Mbps, MII/RMII 接口)
//   USB Device Controller (简化, 仅 Control/Bulk 端点)
// ============================================================================

`timescale 1ns / 1ps


// ---------------------------------------------------------------- SPI Master
// 4 线 SPI (SCLK, MOSI, MISO, CS[3:0]), 主模式
// CPOL/CPOL 可编程, 时钟分频, 单字节收发
module spi_master_regs #(
    parameter CS_N = 4
)(
    input  wire        clk,
    input  wire        rst_n,
    input  wire [7:0]  addr,
    input  wire        we,
    input  wire [31:0] wdata,
    output reg  [31:0] rdata,
    input  wire        stb,
    output reg         ack,

    // SPI 总线
    output reg         spi_sclk,
    output reg         spi_mosi,
    input  wire        spi_miso,
    output reg  [CS_N-1:0] spi_cs_n,

    output reg         spi_irq
);

    reg [7:0]  tx_buf;
    reg [7:0]  rx_buf;
    reg [7:0]  prescale;
    reg        start;
    reg        busy;
    reg        done_reg;
    reg [2:0]  bit_cnt;
    reg        cpol, cpha;

    // 简化: shift 寄存器方式, 8 bit 收发
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            tx_buf  <= 0; rx_buf  <= 0;
            prescale<= 8'd4;
            start   <= 0; busy    <= 0; done_reg <= 0;
            bit_cnt <= 0; cpol    <= 0; cpha     <= 0;
            spi_sclk<= 0; spi_mosi<= 0;
            spi_cs_n<= ~0; spi_irq <= 0;
            ack     <= 0;
        end else begin
            ack <= 0; done_reg <= 0;
            if (start && !busy) begin
                busy    <= 1;
                bit_cnt <= 0;
                spi_cs_n<= 4'b1110;  // 默认选中 device 0
                tx_buf  <= tx_buf;
                start   <= 0;
            end

            if (busy) begin
                // 模拟 bit 收发: 简化版假设 1 cycle/bit
                if (bit_cnt == 0 && !cpha) begin
                    spi_miso <= 0;
                end
                spi_mosi <= tx_buf[7 - bit_cnt];
                spi_sclk <= ~spi_sclk;
                if (spi_sclk == 1'b1) begin  // rising edge 采样
                    rx_buf <= {rx_buf[6:0], spi_miso};
                    if (bit_cnt == 3'd7) begin
                        busy     <= 0;
                        done_reg <= 1;
                        spi_cs_n <= ~0;
                    end else
                        bit_cnt <= bit_cnt + 1;
                end
            end

            if (done_reg) spi_irq <= 1;

            if (stb && we && !ack) begin
                ack <= 1;
                case (addr)
                    8'h00: tx_buf    <= wdata[7:0];
                    8'h04: prescale  <= wdata[7:0];
                    8'h08: {cpha, cpol} <= wdata[1:0];
                    8'h0C: start     <= wdata[0];
                endcase
            end else if (stb && !we && !ack) begin
                ack <= 1;
                case (addr)
                    8'h00: rdata <= {24'b0, tx_buf};
                    8'h04: rdata <= {24'b0, prescale};
                    8'h10: rdata <= {24'b0, rx_buf};
                    8'h14: rdata <= {30'b0, done_reg, busy};
                    default: rdata <= 0;
                endcase
            end
        end
    end
endmodule


// ---------------------------------------------------------------- Ethernet MAC
// 简化 L2, 仅收/发以太网帧, MII 接口
// 帧格式: 前导码 + 目的 MAC + 源 MAC + 长度/类型 + 数据 + FCS
module ethernet_mac_regs (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [7:0]  addr,
    input  wire        we,
    input  wire [31:0] wdata,
    output reg  [31:0] rdata,
    input  wire        stb,
    output reg         ack,

    // MII TX
    output reg  [3:0]  mii_txd,
    output reg         mii_tx_en,
    output reg         mii_tx_clk,
    input  wire        mii_tx_er,

    // MII RX
    input  wire [3:0]  mii_rxd,
    input  wire        mii_rx_dv,
    input  wire        mii_rx_clk,
    input  wire        mii_rx_er,

    output reg         mac_irq
);

    reg [47:0] mac_addr;     // 48-bit MAC
    reg [31:0] tx_pkt [0:15];// 64 字节发送缓冲
    reg [31:0] rx_pkt [0:15];// 接收缓冲
    reg [5:0]  tx_len, tx_idx;
    reg [5:0]  rx_len, rx_idx;
    reg        tx_start, rx_done;
    reg        tx_busy;

    localparam ST_IDLE = 0, ST_PREAMBLE = 1, ST_DATA = 2, ST_FCS = 3;
    reg [1:0] tx_state;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            mac_addr <= 48'h00_0A_35_00_00_01;
            tx_start <= 0; tx_busy <= 0; tx_len <= 0; tx_idx <= 0;
            rx_len   <= 0; rx_idx <= 0;   rx_done <= 0;
            tx_state <= ST_IDLE;
            mii_txd <= 0; mii_tx_en <= 0; mac_irq <= 0;
            ack      <= 0;
        end else begin
            ack <= 0; rx_done <= 0;

            // TX 状态机 (简化)
            case (tx_state)
            ST_IDLE: begin
                if (tx_start && !tx_busy) begin
                    tx_busy  <= 1;
                    tx_idx   <= 0;
                    tx_state <= ST_PREAMBLE;
                end
            end
            ST_PREAMBLE: begin
                mii_tx_en <= 1;
                mii_txd   <= 4'h5;
                tx_state  <= ST_DATA;
            end
            ST_DATA: begin
                mii_tx_en <= 1;
                mii_txd   <= tx_pkt[tx_idx][3:0];
                tx_idx    <= tx_idx + 1;
                if (tx_idx >= tx_len) begin
                    tx_state <= ST_IDLE;
                    tx_busy  <= 0;
                    tx_start <= 0;
                    mac_irq  <= 1;
                end
            end
            default: tx_state <= ST_IDLE;
            endcase

            // RX (简化: 收一个 frame 触发中断)
            if (mii_rx_dv && rx_idx < 16) begin
                rx_pkt[rx_idx] <= {24'h0, mii_rxd, 4'h0};
                rx_idx <= rx_idx + 1;
                rx_len <= rx_len + 1;
            end else if (rx_idx > 0) begin
                rx_done <= 1;
                rx_idx  <= 0;
                mac_irq <= 1;
            end

            if (stb && we && !ack) begin
                ack <= 1;
                case (addr)
                    8'h00: mac_addr[31:0] <= wdata;
                    8'h04: mac_addr[47:32]<= wdata[15:0];
                    8'h10: tx_pkt[0]      <= wdata;
                    8'h14: tx_pkt[1]      <= wdata;
                    8'h50: tx_start       <= wdata[0];
                    8'h54: tx_len         <= wdata[5:0];
                endcase
            end else if (stb && !we && !ack) begin
                ack <= 1;
                case (addr)
                    8'h00: rdata <= mac_addr[31:0];
                    8'h04: rdata <= {16'b0, mac_addr[47:32]};
                    8'h10: rdata <= tx_pkt[0];
                    8'h60: rdata <= rx_pkt[0];
                    8'h70: rdata <= {26'b0, rx_len, rx_done, tx_busy};
                    default: rdata <= 0;
                endcase
            end
        end
    end
endmodule


// ---------------------------------------------------------------- USB Device Controller
// 简化版设备控制器 (仅 Control + Bulk IN/OUT 端点)
// USB 1.1 (12Mbps), 内部有端点 FIFO
module usb_device_regs (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [7:0]  addr,
    input  wire        we,
    input  wire [31:0] wdata,
    output reg  [31:0] rdata,
    input  wire        stb,
    output reg         ack,

    // USB D+/D-
    inout  wire        usb_dp,
    inout  wire        usb_dm,

    output reg         usb_irq
);

    // 端点 FIFO (简化: 共用 256 字节环形缓冲)
    reg [7:0] fifo [0:255];
    reg [7:0] fifo_wptr, fifo_rptr;
    reg [7:0] pkt_len;
    reg       pkt_ready, rx_done, tx_done;
    reg [6:0] dev_addr;
    reg       usb_enable;

    // USB 差分线 (开漏, 1.5K 上拉在 dp)
    assign usb_dp = 1'bz;
    assign usb_dm = 1'bz;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            fifo_wptr <= 0; fifo_rptr <= 0;
            pkt_len   <= 0; pkt_ready <= 0;
            rx_done   <= 0; tx_done   <= 0;
            dev_addr  <= 0; usb_enable<= 0;
            usb_irq   <= 0; ack       <= 0;
        end else begin
            ack <= 0; rx_done <= 0; tx_done <= 0;

            if (stb && we && !ack) begin
                ack <= 1;
                case (addr)
                    8'h00: usb_enable <= wdata[0];
                    8'h04: dev_addr   <= wdata[6:0];
                    8'h10: begin
                        fifo[fifo_wptr] <= wdata[7:0];
                        fifo_wptr <= fifo_wptr + 1;
                    end
                    8'h14: pkt_len    <= wdata[7:0];
                    8'h18: tx_done    <= wdata[0];   // 触发发送
                endcase
            end else if (stb && !we && !ack) begin
                ack <= 1;
                case (addr)
                    8'h00: rdata <= {31'b0, usb_enable};
                    8'h04: rdata <= {25'b0, dev_addr};
                    8'h10: rdata <= {24'b0, fifo[fifo_rptr]};
                    8'h14: rdata <= {24'b0, pkt_len};
                    8'h20: rdata <= {24'b0, fifo_wptr - fifo_rptr};  // FIFO 计数
                    8'h24: rdata <= {29'b0, pkt_ready, rx_done, tx_done};
                    default: rdata <= 0;
                endcase
            end

            // 模拟 USB 事件
            if (tx_done && pkt_ready) begin
                fifo_rptr <= fifo_rptr + pkt_len;
                pkt_ready <= 0;
                usb_irq   <= 1;
            end
        end
    end
endmodule
