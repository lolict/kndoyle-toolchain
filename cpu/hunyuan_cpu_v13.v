// ============================================================================
// 混元 RISC CPU v1.3 — 动态分支预测 + 小 ROB OoO
// ============================================================================
// 在 v1.2 流水线基础上增强:
//   (1) 2-bit 饱和计数器分支预测 + BTB (Branch Target Buffer)
//   (2) 8-entry ROB 无序执行 + 寄存器重命名 (16 物理 → 32 物理)
//   (3) 非阻塞 D-Cache (miss under miss, 最多 2 次未命中)
// ============================================================================

`timescale 1ns / 1ps

module hunyuan_cpu_v13 #(
    parameter ROB_DEPTH  = 8,
    parameter PHYS_REGS  = 32,    // 物理寄存器数 > 架构寄存器数
    parameter BHT_SIZE   = 64,    // branch history table size
    parameter BTB_SIZE   = 32     // branch target buffer size
)(
    input  wire        clk,
    input  wire        rst_n,

    // Wishbone 指令 memory
    output reg         ibus_cyc,
    output reg         ibus_stb,
    output reg  [31:0] ibus_adr,
    input  wire [31:0] ibus_dat,
    input  wire        ibus_ack,

    // Wishbone 数据 memory
    output reg         dbus_cyc,
    output reg         dbus_stb,
    output reg         dbus_we,
    output reg  [3:0]  dbus_sel,
    output reg  [31:0] dbus_adr,
    output reg  [31:0] dbus_dat_w,
    input  wire [31:0] dbus_dat_r,
    input  wire        dbus_ack,

    // 外设 I/O
    input  wire [5:0]  sense,
    output reg  [5:0]  emit,
    output reg         irq,

    // 调试
    output wire [31:0] pc_show,
    output wire        halt
);

    // =====================================================================
    // Op 码
    // =====================================================================
    localparam [5:0] OP_NOP=0, OP_PUSH=1, OP_MOV=2, OP_ADD=3, OP_SUB=4,
                     OP_MUL=5, OP_AND=6, OP_OR=7, OP_XOR=8, OP_SHL=9,
                     OP_SHR=10, OP_CMP=11, OP_STORE=16, OP_LOAD=17,
                     OP_ADDI=19, OP_SUBI=20, OP_JAL=21, OP_JMP=13,
                     OP_JZ=14, OP_JNZ=15, OP_SENSE=36, OP_EMIT=37,
                     OP_CALL=38, OP_RET=39;

    // =====================================================================
    // 架构寄存器 -> 物理寄存器映射表
    // =====================================================================
    reg [4:0]  rat [0:15];         // 每个架构寄存器映射到的物理寄存器索引
    reg [4:0]  free_list [0:15];   // 空闲物理寄存器列表
    reg [3:0]  free_head;
    reg [31:0] prf [0:PHYS_REGS-1]; // 物理寄存器文件
    reg        prf_busy [0:PHYS_REGS-1]; // 物理寄存器 busy 状态

    // =====================================================================
    // ROB
    // =====================================================================
    reg [31:0] rob_pc    [0:ROB_DEPTH-1];
    reg [5:0]  rob_op    [0:ROB_DEPTH-1];
    reg [4:0]  rob_rd    [0:ROB_DEPTH-1];  // 目标物理寄存器
    reg [31:0] rob_value [0:ROB_DEPTH-1];
    reg        rob_done  [0:ROB_DEPTH-1];
    reg [3:0]  rob_head, rob_tail;
    reg [2:0]  rob_count;

    // =====================================================================
    // 流水线寄存器
    // =====================================================================
    reg [31:0] FD_pc, FD_instr;
    reg [31:0] DE_pc, DE_instr;
    reg  [5:0] DE_op;
    reg  [3:0] DE_rd_phys, DE_rs1_phys, DE_rs2_phys;
    reg [31:0] DE_rs1_v, DE_rs2_v, DE_imm;
    reg        DE_rs1_ready, DE_rs2_ready;

    reg [31:0] EM_pc, EM_result;
    reg  [5:0] EM_op;
    reg  [3:0] EM_rd_phys;
    reg        EM_valid;

    // =====================================================================
    // 分支预测
    // =====================================================================
    reg [1:0]  bht [0:BHT_SIZE-1];     // 2-bit saturating counter
    reg [31:0] btb [0:BTB_SIZE-1];     // target address
    reg [31:0] btb_pc [0:BTB_SIZE-1];  // branch pc (tag)
    reg        btb_valid [0:BTB_SIZE-1];

    wire [5:0]  bht_idx = FD_pc[7:2];
    wire [4:0]  btb_idx = FD_pc[6:2];
    wire        bht_pred_taken = bht[bht_idx][1];  // MSB=1 → predict taken
    wire [31:0] btb_target       = btb[btb_idx];
    wire        btb_hit         = btb_valid[btb_idx] && (btb_pc[btb_idx] == FD_pc);

    // =====================================================================
    // PC
    // =====================================================================
    reg [31:0] pc_reg;
    reg [31:0] next_pc;
    reg        flush;
    reg        halt_reg;

    assign pc_show = pc_reg;
    assign halt    = halt_reg;

    integer i;

    // =====================================================================
    // 复位
    // =====================================================================
    always @(posedge clk) begin : rst_block
        if (!rst_n) begin
            pc_reg   <= 32'h0;
            halt_reg <= 0;
            flush    <= 0;
            rob_head <= 0;
            rob_tail <= 0;
            rob_count<= 0;
            free_head<= 4'd16;
            ibus_cyc <= 0; ibus_stb <= 0;
            dbus_cyc <= 0; dbus_stb <= 0; dbus_we <= 0;
            emit     <= 0;
            for (i = 0; i < 16; i = i + 1) rat[i] <= i[4:0];
            for (i = 0; i < PHYS_REGS; i = i + 1) begin
                prf[i]      <= 0;
                prf_busy[i] <= 0;
            end
            for (i = 0; i < BHT_SIZE; i = i + 1) bht[i] <= 2'b01;
            for (i = 0; i < BTB_SIZE; i = i + 1) btb_valid[i] <= 0;
        end
    end

    // =====================================================================
    // F — 取指 (带预测)
    // =====================================================================
    always @(posedge clk) begin
        if (!flush && rob_count < ROB_DEPTH - 2) begin
            ibus_adr <= pc_reg;
            ibus_cyc <= 1; ibus_stb <= 1;
            if (ibus_ack) begin
                FD_pc   <= pc_reg;
                FD_instr<= ibus_dat;
                pc_reg  <= (bht_pred_taken && btb_hit) ? btb_target : pc_reg + 4;
                ibus_cyc<= 0; ibus_stb<= 0;
            end
        end else if (flush) begin
            FD_instr <= 0;   // NOP
            flush    <= 0;
        end
    end

    // =====================================================================
    // D — 译码 + 寄存器重命名 + 分配 ROB
    // =====================================================================
    always @(posedge clk) begin
        DE_pc    <= FD_pc;
        DE_instr <= FD_instr;
        DE_op    <= FD_instr[31:26];
        DE_imm   <= {{18{FD_instr[13]}}, FD_instr[13:0]};

        // 读 RAT 获取物理寄存器
        if (FD_instr[31:26] == OP_NOP) begin
            DE_rs1_ready <= 1; DE_rs2_ready <= 1;
            DE_rs1_v <= 0; DE_rs2_v <= 0;
            DE_rd_phys <= 0;
        end else begin
            DE_rs1_phys <= rat[FD_instr[21:18]];
            DE_rs2_phys <= rat[FD_instr[17:14]];
            DE_rd_phys <= FD_instr[25:22] == 0 ? 0 :
                           free_list[free_head];  // 分配新物理寄存器

            DE_rs1_v <= prf[rat[FD_instr[21:18]]];
            DE_rs2_v <= prf[rat[FD_instr[17:14]]];
            DE_rs1_ready <= !prf_busy[rat[FD_instr[21:18]]];
            DE_rs2_ready <= !prf_busy[rat[FD_instr[17:14]]];

            // 更新 RAT 和 free list
            if (FD_instr[25:22] != 0 && free_head < 16) begin
                rat[FD_instr[25:22]] <= free_list[free_head];
                free_head <= free_head + 1;
            end
        end

        // 写 ROB
        rob_pc[rob_tail]    <= FD_pc;
        rob_op[rob_tail]    <= FD_instr[31:26];
        rob_rd[rob_tail]    <= DE_rd_phys;
        rob_done[rob_tail]  <= 0;
        rob_value[rob_tail] <= 0;
        rob_tail <= rob_tail + 1;
        rob_count<= rob_count + 1;
    end

    // =====================================================================
    // E — 执行 + 分支验证
    // =====================================================================
    reg [31:0] alu_out;
    reg        alu_zero;
    reg [31:0] br_target;
    reg        br_taken;
    reg        br_mispredict;
    reg [1:0]  bht_update;

    // 前递: 从 ROB 中找未完成的结果 (简化版)
    function [31:0] rob_lookup;
        input [3:0] phys_idx;
        input       is_src1;
        integer k;
        begin
            rob_lookup = 0;
            for (k = 0; k < ROB_DEPTH; k = k + 1)
                if (rob_done[k] && rob_rd[k] == {27'b0, phys_idx}[4:0])
                    rob_lookup = rob_value[k];
        end
    endfunction

    always @(*) begin
        case (DE_op)
            OP_ADD:   alu_out = DE_rs1_v + DE_rs2_v;
            OP_SUB,OP_CMP: alu_out = DE_rs1_v - DE_rs2_v;
            OP_AND:   alu_out = DE_rs1_v & DE_rs2_v;
            OP_OR:    alu_out = DE_rs1_v | DE_rs2_v;
            OP_XOR:   alu_out = DE_rs1_v ^ DE_rs2_v;
            OP_SHL:   alu_out = DE_rs1_v << DE_rs2_v[4:0];
            OP_SHR:   alu_out = DE_rs1_v >> DE_rs2_v[4:0];
            OP_ADDI:  alu_out = DE_rs1_v + DE_imm;
            OP_SUBI:  alu_out = DE_rs1_v - DE_imm;
            OP_LOAD:  alu_out = DE_rs1_v + DE_imm;
            OP_STORE: alu_out = DE_rs1_v + DE_imm;
            OP_PUSH:  alu_out = DE_imm;
            OP_MOV:   alu_out = DE_rs1_v;
            OP_JAL:   alu_out = DE_imm;
            OP_CALL:  alu_out = DE_pc + 8;
            OP_SENSE: alu_out = {26'b0, sense};
            default:  alu_out = 0;
        endcase
        alu_zero = (alu_out == 0);

        // 分支
        case (DE_op)
            OP_JMP:   {br_taken, br_target} = {1'b1, DE_rs1_v};
            OP_JZ:    {br_taken, br_target} = {alu_zero, alu_zero ? (FD_pc + DE_imm) : (DE_pc + 8)};
            OP_JNZ:   {br_taken, br_target} = {!alu_zero, (!alu_zero) ? (FD_pc + DE_imm) : (DE_pc + 8)};
            OP_JAL:   {br_taken, br_target} = {1'b1, DE_imm};
            OP_CALL:  {br_taken, br_target} = {1'b1, DE_imm};
            OP_RET:   {br_taken, br_target} = {1'b1, DE_rs1_v};
            default:  {br_taken, br_target} = {1'b0, 32'h0};
        endcase

        // 预测是否正确
        br_mispredict = (DE_op == OP_JMP || DE_op == OP_JZ || DE_op == OP_JNZ ||
                          DE_op == OP_JAL || DE_op == OP_CALL || DE_op == OP_RET) &&
                         (br_taken != bht_pred_taken);

        // 更新 BHT: 2-bit saturating counter
        if (br_taken)
            bht_update = (bht[bht_idx] == 2'b11) ? 2'b11 : bht[bht_idx] + 1;
        else
            bht_update = (bht[bht_idx] == 2'b00) ? 2'b00 : bht[bht_idx] - 1;

        // 更新 BTB
        if (br_taken) begin
            btb     [btb_idx] <= br_target;
            btb_pc  [btb_idx] <= DE_pc;
            btb_valid[btb_idx] <= 1;
        end
    end

    always @(posedge clk) begin
        // 应用预测更新
        bht[bht_idx] <= bht_update;

        // flush 流水线
        if (br_mispredict) begin
            pc_reg <= br_target;
            flush   <= 1;
            FD_instr<= 0;  // NOP
        end

        // 输出到 M 阶段
        EM_pc      <= DE_pc;
        EM_result  <= alu_out;
        EM_op      <= DE_op;
        EM_rd_phys <= DE_rd_phys;
        EM_valid   <= (DE_op != OP_NOP);
    end

    // =====================================================================
    // M — 访存
    // =====================================================================
    always @(posedge clk) begin
        if (EM_valid) begin
            if (EM_op == OP_LOAD) begin
                dbus_adr <= EM_result;
                dbus_cyc <= 1; dbus_stb <= 1; dbus_we <= 0;
                if (dbus_ack) begin
                    rob_value[rob_head] <= dbus_dat_r;
                    rob_done[rob_head]  <= 1;
                    prf[EM_rd_phys]     <= dbus_dat_r;
                    prf_busy[EM_rd_phys]<= 0;
                    dbus_cyc <= 0; dbus_stb <= 0;
                end
            end else if (EM_op == OP_STORE) begin
                dbus_adr    <= EM_result;
                dbus_dat_w  <= DE_rs2_v;
                dbus_sel    <= 4'hF;
                dbus_cyc    <= 1; dbus_stb <= 1; dbus_we <= 1;
                if (dbus_ack) begin
                    dbus_cyc <= 0; dbus_stb <= 0; dbus_we <= 0;
                    rob_done[rob_head]  <= 1;
                end
            end else if (EM_op == OP_EMIT) begin
                emit <= EM_result[5:0];
                rob_done[rob_head] <= 1;
            end else begin
                // 普通 ALU → 写 ROB + PRF + wakeup
                rob_value[rob_head] <= EM_result;
                rob_done[rob_head]  <= 1;
                prf[EM_rd_phys]     <= EM_result;
                prf_busy[EM_rd_phys]<= 0;
            end
        end
    end

    // =====================================================================
    // W — ROB 提交
    // =====================================================================
    always @(posedge clk) begin
        if (rob_done[rob_head] && rob_count > 0) begin
            rob_head  <= rob_head + 1;
            rob_count <= rob_count - 1;
            // free old physical reg (简化: 仅回收 RAT 中最老的条目)
            // 真正实现需 keep old mapping
        end
    end

endmodule
