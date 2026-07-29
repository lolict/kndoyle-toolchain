// ============================================================================
// 混元 RISC CPU v1.1 — 5 级流水线
// ============================================================================
// 基于 v1.0 多周期版本，升级为经典 5-stage RISC pipeline。
//
// 流水线阶段:
//   F (Fetch)    — 从 I-cache 取指
//   D (Decode)   — 读寄存器、译码、hazard 检测
//   E (Execute)  — ALU、分支目标、前递多路选择
//   M (Memory)   — D-cache 读/写
//   W (Writeback)— 结果写回寄存器
//
// 旁路转发 (Forwarding):
//   EX → EX: ALU 结果直接前递给下一指令的 EX 源
//   MEM → EX: Load 结果前递给 EX 源
//   WB → EX: 前递来自 MEM+WB 两路
//
// Hazard 处理:
//   Load-use: 插入1个气泡 (stall)
//   Branch:  静态预测 not-taken；若 taken 则 flush F + D
//
// ============================================================================

`timescale 1ns / 1ps

module hunyuan_cpu_pipelined (
    input  wire        clk,
    input  wire        rst_n,

    // 指令 memory (Wishbone)
    output reg         ibus_cyc,
    output reg         ibus_stb,
    output reg  [31:0] ibus_adr,
    input  wire [31:0] ibus_dat,
    input  wire        ibus_ack,

    // 数据 memory (Wishbone)
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
    // 操作码
    // =====================================================================
    localparam [5:0] OP_NOP  = 6'h00, OP_PUSH  = 6'h01, OP_MOV   = 6'h02,
                     OP_ADD   = 6'h03, OP_SUB   = 6'h04, OP_MUL   = 6'h05,
                     OP_AND   = 6'h06, OP_OR    = 6'h07, OP_XOR   = 6'h08,
                     OP_SHL   = 6'h09, OP_SHR   = 6'h0A, OP_CMP   = 6'h0B,
                     OP_STORE = 6'h10, OP_LOAD  = 6'h11, OP_ADDI  = 6'h13,
                     OP_SUBI  = 6'h14, OP_JAL   = 6'h15, OP_JMP   = 6'h0D,
                     OP_JZ    = 6'h0E, OP_JNZ   = 6'h0F, OP_SENSE = 6'h24,
                     OP_EMIT  = 6'h25, OP_CALL  = 6'h26, OP_RET   = 6'h27;

    // =====================================================================
    // 寄存器文件 (16 个 32-bit)
    // =====================================================================
    reg [31:0] rf [0:15];

    // =====================================================================
    // 流水线寄存器
    // =====================================================================
    reg [31:0] FD_pc, FD_instr;
    reg [31:0] DE_pc, DE_instr, DE_rs1, DE_rs2, DE_imm;
    reg  [5:0] DE_opcode;
    reg  [3:0] DE_rd, DE_rs1_idx, DE_rs2_idx;
    reg [31:0] EM_pc, EM_alu_out, EM_rs2;
    reg  [5:0] EM_opcode;
    reg  [3:0] EM_rd;
    reg        EM_br_taken;
    reg [31:0] MW_alu_out, MW_mem_out, MW_pc;
    reg  [5:0] MW_opcode;
    reg  [3:0] MW_rd;
    reg        MW_rf_wen;

    // =====================================================================
    // 流水线控制
    // =====================================================================
    reg        FE_stall, FE_flush;
    reg        FD_stall, FD_flush;
    reg        DE_flush;

    // Hazard 检测
    reg        stall_load_use;       // 完全 stall F + D
    reg        branch_flush;          // taken → flush FD+DE

    // 前递
    reg [31:0] forward_a, forward_b;
    reg  [1:0] fa_sel, fb_sel;       // 00=reg, 01=EX_fwd, 10=MEM_fwd, 11=WB_fwd

    // ALU
    reg [31:0] alu_out;
    reg        alu_zero;

    // Branch
    reg [31:0] branch_target;
    reg        br_taken;
    reg [31:0] pc_next, pc_reg;
    reg [31:0] link_pc;              // PC+8 (用于 JAL/CALL)
    reg        halt_reg;
    integer i;

    assign pc_show = pc_reg;
    assign halt    = halt_reg;

    always @(posedge clk) begin : rst_blk
        if (!rst_n) begin
            FD_pc <= 0; FD_instr <= 0;
            DE_pc <= 0; DE_opcode <= 0; DE_rd <= 0;
            EM_opcode <= 0; EM_rd <= 0; EM_br_taken <= 0;
            MW_opcode <= 0; MW_rd <= 0; MW_rf_wen <= 0;
            FE_stall <= 0; FE_flush <= 0;
            FD_stall <= 0; FD_flush <= 0;
            DE_flush <= 0;
            stall_load_use <= 0;
            branch_flush <= 0;
            pc_reg <= 0;
            halt_reg <= 0;
            emit <= 0; irq <= 0;
            ibus_cyc <= 0; ibus_stb <= 0;
            dbus_cyc <= 0; dbus_stb <= 0; dbus_we <= 0;
            for (i = 0; i < 16; i = i + 1) rf[i] <= 0;
        end
    end

    // =====================================================================
    // 前递单元
    // =====================================================================
    always @(*) begin
        // forward A (rs1)
        if (DE_rs1_idx != 0 && DE_rd != 0) begin
            if (EM_rd == DE_rs1_idx && inside_op_arith_mem(EM_opcode))
                fa_sel = 2'b01;                      // EX→EX
            else if (MW_rd == DE_rs1_idx && inside_op_arith(MW_opcode))
                fa_sel = 2'b10;                      // MEM→EX
            else
                fa_sel = 2'b00;
        end else
            fa_sel = 2'b00;

        // forward B (rs2)
        if (DE_rs2_idx != 0 && DE_rd != 0) begin
            if (EM_rd == DE_rs2_idx && inside_op_arith_mem(EM_opcode))
                fb_sel = 2'b01;
            else if (MW_rd == DE_rs2_idx && inside_op_arith(MW_opcode))
                fb_sel = 2'b10;
            else
                fb_sel = 2'b00;
        end else
            fb_sel = 2'b00;

        forward_a = (fa_sel == 2'b01) ? EM_alu_out :
                    (fa_sel == 2'b10) ? (MW_opcode == OP_LOAD ? MW_mem_out : MW_alu_out) :
                    DE_rs1;
        forward_b = (fb_sel == 2'b01) ? EM_alu_out :
                    (fb_sel == 2'b10) ? (MW_opcode == OP_LOAD ? MW_mem_out : MW_alu_out) :
                    DE_rs2;
    end

    function inside_op_arith(input [5:0] op);
        inside_op_arith = (op == OP_ADD || op == OP_SUB || op == OP_AND ||
                           op == OP_OR  || op == OP_XOR || op == OP_SHL ||
                           op == OP_SHR || op == OP_ADDI || op == OP_SUBI ||
                           op == OP_CMP || op == OP_LOAD || op == OP_JAL ||
                           op == OP_PUSH || op == OP_MOV || op == OP_SENSE ||
                           op == OP_CALL);
    endfunction

    function inside_op_arith_mem(input [5:0] op);
        inside_op_arith_mem = inside_op_arith(op);
    endfunction

    // =====================================================================
    // F — 取指
    // =====================================================================
    always @(posedge clk) begin
        if (!FE_stall && !FE_flush) begin
            ibus_adr <= pc_reg;
            ibus_cyc <= 1;
            ibus_stb <= 1;
            if (ibus_ack) begin
                FD_pc   <= pc_reg;
                FD_instr<= ibus_dat;
                pc_reg  <= pc_reg + 4;
                ibus_cyc<= 0;
                ibus_stb<= 0;
            end
        end else if (FE_flush) begin
            FD_instr <= 0;           // NOP
            FD_pc    <= pc_reg;
        end
    end

    // =====================================================================
    // D — 译码
    // =====================================================================
    always @(posedge clk) begin
        if (!FD_stall) begin
            if (FD_flush || DE_flush) begin
                DE_opcode <= OP_NOP;
                DE_rd     <= 0;
            end else begin
                DE_pc     <= FD_pc;
                DE_instr  <= FD_instr;
                DE_opcode <= FD_instr[31:26];
                DE_rd     <= FD_instr[25:22];
                DE_rs1_idx<= FD_instr[21:18];
                DE_rs2_idx<= FD_instr[17:14];
                DE_imm    <= {{18{FD_instr[13]}}, FD_instr[13:0]};
                DE_rs1    <= rf[FD_instr[21:18]];
                DE_rs2    <= rf[FD_instr[17:14]];
            end
        end
    end

    // =====================================================================
    // E — 执行
    // =====================================================================
    always @(*) begin
        // ALU
        case (DE_opcode)
            OP_ADD:   alu_out = forward_a + forward_b;
            OP_SUB,OP_CMP: alu_out = forward_a - forward_b;
            OP_AND:   alu_out = forward_a & forward_b;
            OP_OR:    alu_out = forward_a | forward_b;
            OP_XOR:   alu_out = forward_a ^ forward_b;
            OP_SHL:   alu_out = forward_a << forward_b[4:0];
            OP_SHR:   alu_out = forward_a >> forward_b[4:0];
            OP_ADDI:  alu_out = forward_a + DE_imm;
            OP_SUBI:  alu_out = forward_a - DE_imm;
            OP_LOAD:  alu_out = forward_a + DE_imm;
            OP_STORE: alu_out = forward_a + DE_imm;
            OP_PUSH:  alu_out = DE_imm;
            OP_MOV:   alu_out = forward_a;
            OP_JAL:   alu_out = DE_imm;
            OP_CALL:  alu_out = DE_pc + 8;
            OP_SENSE: alu_out = {26'b0, sense};
            OP_JZ:    alu_out = forward_a;
            OP_JNZ:   alu_out = forward_a;
            OP_RET:   alu_out = forward_a;
            default:  alu_out = 0;
        endcase
        alu_zero = (alu_out == 0);

        // Branch
        case (DE_opcode)
            OP_JMP:   begin branch_target = forward_a;       br_taken = 1; end
            OP_JZ:    begin branch_target = (alu_zero)? forward_a : DE_pc+8; br_taken = alu_zero; end
            OP_JNZ:   begin branch_target = (!alu_zero)? forward_a : DE_pc+8; br_taken = !alu_zero; end
            OP_JAL:   begin branch_target = DE_imm;           br_taken = 1; link_pc = DE_pc+8; end
            OP_CALL:  begin branch_target = DE_imm;           br_taken = 1; link_pc = DE_pc+8; end
            OP_RET:   begin branch_target = forward_a;        br_taken = 1; end
            default:  begin branch_target = 0;                 br_taken = 0; end
        endcase
    end

    always @(posedge clk) begin
        EM_pc       <= DE_pc;
        EM_alu_out  <= alu_out;
        EM_rs2      <= forward_b;
        EM_opcode   <= DE_opcode;
        EM_rd       <= DE_opcode == OP_JAL ? 1 :
                       DE_opcode == OP_CALL ? 1 : DE_rd;
        EM_br_taken <= br_taken;
        if (br_taken) pc_reg <= branch_target;
        if (DE_opcode == OP_EMIT) emit <= forward_a[5:0];
    end

    // =====================================================================
    // M — 访存
    // =====================================================================
    always @(posedge clk) begin
        if (EM_opcode == OP_LOAD) begin
            dbus_adr   <= EM_alu_out;
            dbus_sel   <= 4'hF;
            dbus_cyc   <= 1;
            dbus_stb   <= 1;
            dbus_we    <= 0;
            if (dbus_ack) begin
                MW_mem_out <= dbus_dat_r;
                dbus_cyc   <= 0;
                dbus_stb   <= 0;
                MW_alu_out <= EM_alu_out;
                MW_pc      <= EM_pc;
                MW_opcode  <= EM_opcode;
                MW_rd      <= EM_rd;
                MW_rf_wen  <= 1;
            end
        end else if (EM_opcode == OP_STORE) begin
            dbus_adr   <= EM_alu_out;
            dbus_dat_w <= EM_rs2;
            dbus_sel   <= 4'hF;
            dbus_cyc   <= 1;
            dbus_stb   <= 1;
            dbus_we    <= 1;
            if (dbus_ack) begin
                dbus_cyc   <= 0;
                dbus_stb   <= 0;
                dbus_we    <= 0;
                MW_mem_out <= 0;
                MW_alu_out <= EM_alu_out;
                MW_pc      <= EM_pc;
                MW_opcode  <= OP_NOP;   // 不写寄存器
                MW_rd      <= 0;
                MW_rf_wen  <= 0;
            end
        end else begin
            MW_mem_out  <= 0;
            MW_alu_out  <= EM_alu_out;
            MW_pc       <= EM_pc;
            MW_opcode   <= EM_opcode;
            MW_rd       <= EM_rd;
            MW_rf_wen   <= (EM_opcode != OP_STORE && EM_opcode != OP_NOP &&
                            EM_opcode != OP_EMIT && EM_rd != 0);
        end
    end

    // =====================================================================
    // W — 写回
    // =====================================================================
    always @(posedge clk) begin
        if (MW_rf_wen && MW_rd != 0) begin
            if (MW_opcode == OP_LOAD)
                rf[MW_rd] <= MW_mem_out;
            else if (MW_opcode == OP_JAL || MW_opcode == OP_CALL)
                rf[MW_rd] <= link_pc;
            else
                rf[MW_rd] <= MW_alu_out;
        end
    end

    // =====================================================================
    // Hazard 检测
    // =====================================================================
    always @(*) begin
        // Load-use: DE 用 rs1/rs2，EM 正在 LOAD
        stall_load_use = (DE_rs1_idx != 0 && EM_opcode == OP_LOAD && EM_rd == DE_rs1_idx) ||
                         (DE_rs2_idx != 0 && EM_opcode == OP_LOAD && EM_rd == DE_rs2_idx);
        branch_flush = EM_br_taken;

        FE_stall = stall_load_use;
        FE_flush = branch_flush;
        FD_stall = stall_load_use;
        FD_flush = branch_flush;
        DE_flush = stall_load_use || branch_flush;
    end

endmodule
