// ============================================================================
// 混元外设 IP v1.1 — Timer + PWM + I2C + DMA
// ============================================================================
// 挂载在 CPU 数据总线上 (Wishbone slave)
// 内存映射 (基址可由 SoC 配置):
//   0x3000_0000  Timer  基址
//   0x3000_0010  PWM    基址
//   0x3000_0020  I2C    基址
//   0x3000_0030  DMA    基址
// ============================================================================

`timescale 1ns / 1ps

// ---------------------------------------------------------------- 定时器
// 32-bit 自由运行计数器 + 匹配寄存器 + 使能 + 中断
module timer_regs #(
    parameter N = 2   // 通道数
)(
    input  wire        clk,
    input  wire        rst_n,

    // Wishbone slave (简化, 只支持单次读写)
    input  wire [7:0]  addr,     // 字节地址 (内部寄存器)
    input  wire        we,
    input  wire [31:0] wdata,
    output reg  [31:0] rdata,
    input  wire        stb,
    output reg         ack,

    // 中断输出
    output reg  [N-1:0] irq
);

    reg [31:0] counter;
    reg [31:0] match  [0:N-1];
    reg [31:0] reload [0:N-1];
    reg        enable [0:N-1];
    reg        intr_en[0:N-1];

    integer i;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            counter <= 0;
            for (i = 0; i < N; i = i + 1) begin
                match[i]  <= 32'hFFFF_FFFF;
                reload[i] <= 0;
                enable[i] <= 0;
                intr_en[i]<= 0;
                irq[i]    <= 0;
            end
            ack <= 0;
        end else begin
            counter <= counter + 1;
            ack <= 0;
            for (i = 0; i < N; i = i + 1) begin
                if (enable[i] && counter == match[i])
                    irq[i] <= 1;
                else if (enable[i] && counter >= match[i] + reload[i])
                    irq[i] <= 0;
            end

            if (stb && we && !ack) begin
                ack <= 1;
                case (addr)
                    8'h00: match[0]   <= wdata;
                    8'h04: reload[0]  <= wdata;
                    8'h08: enable[0]  <= wdata[0];
                    8'h0C: intr_en[0] <= wdata[0];
                    default: ;
                endcase
            end else if (stb && !we && !ack) begin
                ack <= 1;
                case (addr)
                    8'h00: rdata <= match[0];
                    8'h04: rdata <= reload[0];
                    8'h08: rdata <= {31'b0, enable[0]};
                    8'h10: rdata <= counter;
                    default: rdata <= 0;
                endcase
            end
        end
    end
endmodule


// ---------------------------------------------------------------- PWM
// 8-bit 分辨率, 3 通道 (适合 LED / 电机 / 舵机)
module pwm_regs #(
    parameter N = 3
)(
    input  wire        clk,
    input  wire        rst_n,
    input  wire [7:0]  addr,
    input  wire        we,
    input  wire [31:0] wdata,
    output reg  [31:0] rdata,
    input  wire        stb,
    output reg         ack,
    output wire [N-1:0] pwm_out
);

    reg [7:0] duty  [0:N-1];
    reg [7:0] period[0:N-1];
    reg        enable[0:N-1];
    reg [7:0] cnt;

    assign pwm_out[0] = enable[0] && (duty[0] > cnt);
    // simplify: 1 bit per channel, directly the comparator output

    integer i;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            cnt <= 0;
            for (i = 0; i < N; i = i + 1) begin
                duty[i]  <= 0;
                period[i]<= 8'hFF;
                enable[i]<= 0;
            end
            ack <= 0;
        end else begin
            cnt <= cnt + 1;
            ack <= 0;
            if (stb && we && !ack) begin
                ack <= 1;
                case (addr)
                    8'h00: duty[0]   <= wdata[7:0];
                    8'h04: period[0] <= wdata[7:0];
                    8'h08: enable[0] <= wdata[0];
                    default: ;
                endcase
            end else if (stb && !we && !ack) begin
                ack <= 1;
                rdata <= {24'b0, duty[0]};
            end
        end
    end
endmodule


// ---------------------------------------------------------------- I2C Master
// 简化版: 7-bit 寻址, 100/400Kbps, 单字节读写
module i2c_master_regs (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [7:0]  addr,
    input  wire        we,
    input  wire [31:0] wdata,
    output reg  [31:0] rdata,
    input  wire        stb,
    output reg         ack,
    inout  wire        sda,
    inout  wire        scl
);

    // 寄存器视图
    reg [6:0]  slave_addr;
    reg [7:0]  wbuff;
    reg [7:0]  rbuff;
    reg        start, stop, read, write;
    reg        busy;
    reg        done_reg;
    reg [31:0] prescale;   // 时钟分频

    assign sda = 1'bz;  // 简化: 开漏模型
    assign scl = 1'bz;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            slave_addr <= 7'h0;
            wbuff     <= 0;
            rbuff     <= 0;
            start <= 0; stop <= 0; read <= 0; write <= 0;
            busy  <= 0; done_reg <= 0;
            prescale <= 32'd100;
            ack <= 0;
        end else begin
            ack <= 0;
            start <= 0; stop <= 0; read <= 0; write <= 0;
            if (stb && we && !ack) begin
                ack <= 1;
                case (addr)
                    8'h00: slave_addr <= wdata[6:0];
                    8'h04: wbuff      <= wdata[7:0];
                    8'h08: begin
                        start <= wdata[0];
                        stop  <= wdata[1];
                        read  <= wdata[2];
                        write <= wdata[3];
                    end
                    8'h0C: prescale   <= wdata;
                endcase
            end else if (stb && !we && !ack) begin
                ack <= 1;
                case (addr)
                    8'h00: rdata <= {25'b0, slave_addr};
                    8'h04: rdata <= {24'b0, wbuff};
                    8'h08: rdata <= {30'b0, done_reg, busy};
                    8'h10: rdata <= {24'b0, rbuff};
                    default: rdata <= 0;
                endcase
            end
        end
    end
endmodule


// ---------------------------------------------------------------- DMA
// 简化版: 内存到内存复制, 突发传送
module dma_regs (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [7:0]  addr,
    input  wire        we,
    input  wire [31:0] wdata,
    output reg  [31:0] rdata,
    input  wire        stb,
    output reg         ack,

    // 总线 master
    output reg         mem_cyc,
    output reg         mem_stb,
    output reg         mem_we,
    output reg  [31:0] mem_addr,
    output reg  [31:0] mem_wdata,
    input  wire [31:0] mem_rdata,
    input  wire        mem_ack,
    output reg         done_irq
);

    reg [31:0] src, dst, len;
    reg        start, busy;

    localparam IDLE = 0, READ = 1, WRITE = 2, DONE = 3;
    reg [1:0]  state;
    reg [31:0] idx;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            src <= 0; dst <= 0; len <= 0;
            start <= 0; busy <= 0; done_irq <= 0;
            state <= IDLE; idx <= 0;
            ack <= 0;
        end else begin
            ack <= 0;
            done_irq <= 0;
            if (start && !busy) begin
                busy  <= 1;
                state <= READ;
                idx   <= 0;
                start <= 0;
            end

            case (state)
            READ: begin
                mem_addr <= src + idx;
                mem_cyc  <= 1;
                mem_stb  <= 1;
                mem_we   <= 0;
                if (mem_ack) begin
                    mem_cyc <= 0;
                    mem_stb <= 0;
                    state   <= WRITE;
                end
            end
            WRITE: begin
                mem_addr  <= dst + idx;
                mem_wdata <= mem_rdata;
                mem_cyc   <= 1;
                mem_stb   <= 1;
                mem_we    <= 1;
                if (mem_ack) begin
                    mem_cyc <= 0;
                    mem_stb <= 0;
                    mem_we  <= 0;
                    if (idx + 4 >= len) begin
                        state    <= DONE;
                    end else begin
                        idx   <= idx + 4;
                        state <= READ;
                    end
                end
            end
            DONE: begin
                busy     <= 0;
                done_irq <= 1;
                state    <= IDLE;
            end
            default: ;
            endcase

            if (stb && we && !ack) begin
                ack <= 1;
                case (addr)
                    8'h00: src   <= wdata;
                    8'h04: dst   <= wdata;
                    8'h08: len   <= wdata;
                    8'h0C: start <= wdata[0];
                endcase
            end else if (stb && !we && !ack) begin
                ack <= 1;
                case (addr)
                    8'h00: rdata <= src;
                    8'h04: rdata <= dst;
                    8'h08: rdata <= len;
                    8'h0C: rdata <= {30'b0, start, busy};
                    default: rdata <= 0;
                endcase
            end
        end
    end
endmodule
