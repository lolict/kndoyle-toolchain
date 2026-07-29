// ============================================================================
// 混元 Cache v1.1 — 直连映射指令/数据缓存
// ============================================================================
// 规格:
//   - 64 条缓存行 (ways=1, 直接映射)
//   - 每行 4 字 (16 bytes) → 共 256 bytes (I-cache) + 256 bytes (D-cache)
//   - 写策略: write-through + write-allocate
//   - 总线接口: Wishbone
// ============================================================================

`timescale 1ns / 1ps

module icache #(
    parameter integer LINES  = 64,
    parameter integer LINE_W = 4
)(
    input  wire        clk,
    input  wire        rst_n,

    // CPU 端
    input  wire [31:0] cpu_addr,
    input  wire        cpu_req,
    output reg  [31:0] cpu_rdata,
    output reg         cpu_ready,
    output reg         cpu_miss,

    // 总线端
    output reg         mem_cyc,
    output reg         mem_stb,
    output reg  [31:0] mem_addr,
    input  wire [31:0] mem_rdata,
    input  wire        mem_ack
);

    reg [23:0] tag_mem [0:LINES-1];
    reg [31:0] data_mem [0:LINES-1][0:LINE_W-1];
    reg        valid_mem [0:LINES-1];

    wire [5:0]  idx  = cpu_addr[7:2];
    wire [23:0] tag  = cpu_addr[31:8];
    wire [1:0]  word = cpu_addr[1:0];
    wire        hit  = valid_mem[idx] && (tag_mem[idx] == tag);

    integer i, j;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < LINES; i = i + 1) begin
                valid_mem[i] <= 0;
                tag_mem[i]   <= 0;
            end
            mem_cyc  <= 0;
            mem_stb  <= 0;
            cpu_ready<= 0;
            cpu_miss <= 0;
        end else begin
            cpu_ready <= 0;
            cpu_miss  <= 0;
            if (cpu_req) begin
                if (hit) begin
                    cpu_rdata <= data_mem[idx][word];
                    cpu_ready <= 1;
                end else begin
                    cpu_miss <= 1;
                    mem_addr <= {cpu_addr[31:4], 4'b0};
                    mem_cyc  <= 1;
                    mem_stb  <= 1;
                end
            end

            if (mem_cyc && mem_stb && mem_ack) begin
                data_mem[idx][mem_addr[3:2]] <= mem_rdata;
                if (mem_addr[3:2] == 2'd3) begin
                    tag_mem[idx]   <= mem_addr[31:8];
                    valid_mem[idx] <= 1;
                end
                mem_cyc <= 0;
                mem_stb <= 0;
                cpu_ready <= (mem_addr[3:2] == cpu_addr[3:2]) ? 1 : cpu_ready;
                cpu_rdata <= (mem_addr[3:2] == cpu_addr[3:2]) ? mem_rdata : cpu_rdata;
            end
        end
    end

endmodule


module dcache #(
    parameter integer LINES  = 64,
    parameter integer LINE_W = 4
)(
    input  wire        clk,
    input  wire        rst_n,

    // CPU 端
    input  wire [31:0] cpu_addr,
    input  wire        cpu_req,
    input  wire        cpu_we,
    input  wire [3:0]  cpu_sel,
    input  wire [31:0] cpu_wdata,
    output reg  [31:0] cpu_rdata,
    output reg         cpu_ready,

    // 总线端
    output reg         mem_cyc,
    output reg         mem_stb,
    output reg         mem_we,
    output reg  [31:0] mem_addr,
    output reg  [31:0] mem_wdata,
    input  wire [31:0] mem_rdata,
    input  wire        mem_ack
);

    reg [23:0] tag  [0:LINES-1];
    reg [31:0] data [0:LINES-1][0:LINE_W-1];
    reg        valid[0:LINES-1];
    reg        dirty[0:LINES-1];

    wire [5:0]  idx  = cpu_addr[7:2];
    wire [23:0] tagw = cpu_addr[31:8];
    wire [1:0]  word = cpu_addr[1:0];
    wire        hit  = valid[idx] && (tag[idx] == tagw);

    reg [31:0] wmask;
    integer i, j;

    always @(*) begin
        wmask = 0;
        for (i = 0; i < 4; i = i + 1)
            if (cpu_sel[i])
                wmask[i*8 +: 8] = 8'hFF;
    end

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            for (i = 0; i < LINES; i = i + 1) begin
                valid[i] <= 0;
                dirty[i] <= 0;
            end
            mem_cyc  <= 0;
            mem_stb  <= 0;
            mem_we   <= 0;
            cpu_ready<= 0;
        end else begin
            cpu_ready <= 0;
            if (cpu_req) begin
                if (hit) begin
                    cpu_rdata <= data[idx][word];
                    cpu_ready <= 1;
                    if (cpu_we) begin
                        data[idx][word] <= (cpu_wdata & wmask) | (data[idx][word] & ~wmask);
                        dirty[idx] <= 1;
                        mem_addr  <= cpu_addr;
                        mem_wdata <= data[idx][word];
                        mem_cyc   <= 1;
                        mem_stb   <= 1;
                        mem_we    <= 1;
                    end
                end else begin
                    mem_addr <= {cpu_addr[31:4], 4'b0};
                    mem_cyc  <= 1;
                    mem_stb  <= 1;
                    mem_we   <= 0;
                end
            end

            if (mem_cyc && mem_stb && mem_ack) begin
                data[idx][mem_addr[3:2]] <= mem_rdata;
                if (mem_addr[3:2] == 2'd3) begin
                    tag[idx]  <= mem_addr[31:8];
                    valid[idx]<= 1;
                end
                mem_cyc  <= 0;
                mem_stb  <= 0;
                mem_we   <= 0;
                cpu_rdata<= mem_rdata;
                cpu_ready<= 1;
            end
        end
    end

endmodule
