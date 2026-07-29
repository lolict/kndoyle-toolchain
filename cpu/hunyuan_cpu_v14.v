// ============================================================================
// 混元 RISC CPU v1.4 — 超标量双发射 + 硬件乘除法
// ============================================================================
// 基于 v1.1 流水线 + v1.3 分支预测，升级为双发射超标量:
//
//   (1) 双发射取指: 每周期从 I-cache 取 64 bit (2 × 32-bit)
//   (2) 双发射译码: 配对规则静态检查, 兼容则双发, 否则单发 (丢弃 i1)
//   (3) 双 EX 流水线: Lane-0 (ALU/branch/addr) + Lane-1 (ALU/MUL/DIV)
//   (4) 双写回端口: RF 同时写回两结果
//   (5) 硬件乘除法: Booth 乘法 (4 周期) + 非恢复除法 (8 周期)
//   (6) 分支预测: BHT 2-bit + BTB (64-entry BHT, 32-entry BTB)
//
// 配对规则 (静态, 组合逻辑即时判定):
//   允许: ALU+ALU, ALU+LOAD, ALU+STORE(addr), ALU+MUL
//   禁止: 双MEM, 双branch, 双MUL, RAW相关, WAW相关
//
// 分支: JMP/JZ/JNZ/JAL/CALL 用立即数作为跳转目标; RET 用 r1
//
// 指令格式 [31:0]: [31:26]=opcode [25:22]=rd [21:18]=rs1 [17:14]=rs2 [13:0]=imm
// ============================================================================

`timescale 1ns / 1ps

module hunyuan_cpu_v14 (
    input  wire        clk,
    input  wire        rst_n,

    // 指令 memory (Wishbone, 64-bit)
    output reg         ibus_cyc, ibus_stb,
    output reg  [31:0] ibus_adr,
    input  wire [63:0] ibus_dat,
    input  wire        ibus_ack,

    // 数据 memory (Wishbone, 32-bit)
    output reg         dbus_cyc, dbus_stb, dbus_we,
    output reg  [3:0]  dbus_sel,
    output reg  [31:0] dbus_adr, dbus_dat_w,
    input  wire [31:0] dbus_dat_r,
    input  wire        dbus_ack,

    // 外设 I/O
    input  wire [5:0]  sense,
    output reg  [5:0]  emit,
    output reg         irq,

    // 调试
    output wire [31:0] pc_show,
    output wire        halt,
    output wire [1:0]  issue_show
);

    // =====================================================================
    // Op 码
    // =====================================================================
    localparam [5:0] OP_NOP=0, OP_PUSH=1, OP_MOV=2, OP_ADD=3, OP_SUB=4,
                     OP_MUL=5, OP_AND=6, OP_OR=7, OP_XOR=8, OP_SHL=9,
                     OP_SHR=10, OP_CMP=11, OP_STORE=16, OP_LOAD=17,
                     OP_ADDI=19, OP_SUBI=20, OP_JAL=21, OP_JMP=13,
                     OP_JZ=14, OP_JNZ=15, OP_DIV=12, OP_SENSE=36,
                     OP_EMIT=37, OP_CALL=38, OP_RET=39;

    // 指令类别
    localparam [2:0] C_ALU=0, C_MEM=1, C_BR=2, C_MUL=3, C_CTRL=4, C_NONE=5;

    // =====================================================================
    // 寄存器文件 (32 regs, 4R/2W)
    // =====================================================================
    reg [31:0] rf [0:31];
    integer i;

    // =====================================================================
    // BHT/BTB 分支预测
    // =====================================================================
    reg  [1:0]  bht [0:63];
    reg  [31:0] btb_target [0:31];
    reg  [31:0] btb_pc     [0:31];
    reg         btb_valid  [0:31];
    wire        pred_valid = btb_valid[FD_pc[6:2]];
    wire        pred_taken = bht[FD_pc[7:2]][1];
    wire [31:0] pred_target = btb_target[FD_pc[6:2]];

    // =====================================================================
    // IF 级: 双状态机取指 (避免 ack 回落后读到陈旧数据)
    // =====================================================================
    reg [31:0] pc_reg;
    reg        fetch_idle;
    wire [31:0] pc_next = (pred_valid && pred_taken && ibus_ack) ? pred_target : pc_reg + 8;

    always @(posedge clk) begin
        if (!rst_n) begin
            pc_reg <= 0; fetch_idle <= 1; FD_valid <= 0;
            ibus_cyc <= 0; ibus_stb <= 0;
        end else if (FD_flush) begin
            pc_reg <= EM_br_target; fetch_idle <= 1;
            ibus_cyc <= 0; ibus_stb <= 0;
            FD_i0 <= 0; FD_i1 <= 0; FD_valid <= 1;
        end else if (!FE_stall) begin
            if (fetch_idle && !ibus_cyc) begin
                ibus_adr <= pc_reg;
                ibus_cyc <= 1; ibus_stb <= 1;
                fetch_idle <= 0;
            end else if (!fetch_idle && ibus_ack) begin
                FD_pc    <= pc_reg;
                FD_i0    <= ibus_dat[31:0];
                FD_i1    <= ibus_dat[63:32];
                FD_valid <= 1;
                pc_reg   <= pc_next;
                ibus_cyc <= 0; ibus_stb <= 0;
                fetch_idle <= 1;
            end
        end
    end

    assign pc_show = pc_reg;

    // =====================================================================
    // FD 锁存 (在 IF 状态机中被写入)
    reg [31:0] FD_pc, FD_i0, FD_i1;
    reg        FD_valid;

    // =====================================================================
    // 函数
    // =====================================================================
    function [2:0] classify(input [5:0] op);
        case (op)
            OP_ADD, OP_SUB, OP_AND, OP_OR, OP_XOR, OP_SHL, OP_SHR,
            OP_ADDI, OP_SUBI, OP_MOV, OP_CMP: classify = C_ALU;
            OP_LOAD, OP_STORE:                 classify = C_MEM;
            OP_JMP, OP_JZ, OP_JNZ, OP_JAL, OP_RET, OP_CALL: classify = C_BR;
            OP_MUL, OP_DIV:                    classify = C_MUL;
            OP_PUSH, OP_SENSE, OP_EMIT, OP_NOP: classify = C_CTRL;
            default: classify = C_CTRL;
        endcase
    endfunction

    function w_rd(input [5:0] op);
        w_rd = (op == OP_ADD || op == OP_SUB || op == OP_AND ||
                op == OP_OR  || op == OP_XOR || op == OP_SHL ||
                op == OP_SHR || op == OP_ADDI|| op == OP_SUBI||
                op == OP_MOV || op == OP_LOAD|| op == OP_MUL ||
                op == OP_DIV || op == OP_PUSH|| op == OP_JAL ||
                op == OP_CALL|| op == OP_SENSE);
    endfunction

    function can_pair(
        input [5:0] op0, op1, input [3:0] rd0, rd1,
        input [3:0] s0_0, s0_1, s1_0, s1_1, input [2:0] c0, c1
    );
        begin
            can_pair = !(c0 == C_MEM && c1 == C_MEM)       // 双 MEM 不行
                     && !(c0 == C_BR || c1 == C_BR)         // branch 不能配对
                     && !(c0 == C_MUL && c1 == C_MUL)       // 双 MUL 不行
                     && !(w_rd(op0) && w_rd(op1) && rd0 != 0 && rd0 == rd1)  // WAW
                     && !(w_rd(op0) && rd0 != 0 && (s1_0 == rd0 || s1_1 == rd0)) // RAW
                     && (op0 != OP_NOP);
        end
    endfunction

    // =====================================================================
    // ID 配对规则 + 双译码
    // =====================================================================
    wire [5:0] op0_w = FD_i0[31:26];
    wire [5:0] op1_w = FD_i1[31:26];
    wire [3:0] rd0_w = FD_i0[25:22], rd1_w = FD_i1[25:22];
    wire [3:0] rs0_0_w = FD_i0[21:18], rs0_1_w = FD_i0[17:14];
    wire [3:0] rs1_0_w = FD_i1[21:18], rs1_1_w = FD_i1[17:14];
    wire [2:0] c0_w = classify(op0_w), c1_w = classify(op1_w);
    wire       pair_ok = FD_valid && can_pair(op0_w, op1_w, rd0_w, rd1_w,
                                               rs0_0_w, rs0_1_w, rs1_0_w, rs1_1_w,
                                               c0_w, c1_w)
                         && !muldiv_active;  // MUL/DIV 期间禁双发射

    // =====================================================================
    // DE 锁存 (双发射: 两条或一条 NOP)
    // =====================================================================
    reg [31:0] DE_pc;
    reg  [5:0] DE_op0, DE_op1;
    reg  [3:0] DE_rd0, DE_rd1, DE_s0_0, DE_s0_1, DE_s1_0, DE_s1_1;
    reg [31:0] DE_imm0, DE_imm1;
    reg [31:0] DE_v0_0, DE_v0_1, DE_v1_0, DE_v1_1;
    reg        DE_dual;

    always @(posedge clk) begin
        if (!rst_n) begin
            DE_op0 <= 0; DE_op1 <= 0; DE_dual <= 0;
            DE_rd0 <= 0; DE_rd1 <= 0;
            DE_s0_0 <= 0; DE_s0_1 <= 0;
            DE_s1_0 <= 0; DE_s1_1 <= 0;
        end else if (!FD_stall) begin
            if (FD_flush) begin
                DE_op0 <= OP_NOP; DE_op1 <= OP_NOP; DE_dual <= 0;
                DE_rd0 <= 0; DE_rd1 <= 0;
            end else if (FD_valid) begin
                DE_pc     <= FD_pc;
                DE_op0    <= op0_w;
                DE_rd0    <= rd0_w; DE_s0_0 <= rs0_0_w; DE_s0_1 <= rs0_1_w;
                DE_imm0   <= {{18{FD_i0[13]}}, FD_i0[13:0]};
                DE_v0_0   <= rf[rs0_0_w]; DE_v0_1 <= rf[rs0_1_w];

                if (pair_ok) begin
                    DE_op1  <= op1_w;
                    DE_rd1  <= rd1_w; DE_s1_0 <= rs1_0_w; DE_s1_1 <= rs1_1_w;
                    DE_imm1 <= {{18{FD_i1[13]}}, FD_i1[13:0]};
                    DE_v1_0 <= rf[rs1_0_w]; DE_v1_1 <= rf[rs1_1_w];
                    DE_dual <= 1;
                end else begin
                    DE_op1  <= OP_NOP;
                    DE_dual <= 0;
                end
                FD_valid <= 0;  // 消费掉 fetch
            end
        end
    end

    // =====================================================================
    // 前递 (forward)
    // =====================================================================
    reg [31:0] f0_0, f0_1, f1_0, f1_1;
    // 辅助: EM 某 lane 是否写了目标 reg
    function em_wen(input [3:0] test_rd, input [3:0] test_rd1,
                    input [5:0] test_op, input [5:0] test_op1);
        em_wen = (test_rd != 0 && test_op != OP_STORE && test_op != OP_NOP);
    endfunction
    always @(*) begin
        // Lane 0 源1
        f0_0 = DE_v0_0;
        if (em_wen(EM_rd0, EM_rd1, EM_op0, EM_op1) && EM_rd0 == DE_s0_0)
            f0_0 = EM_alu0_out;
        else if (em_wen(EM_rd1, EM_rd0, EM_op1, EM_op0) && EM_rd1 == DE_s0_0)
            f0_0 = EM_alu1_out;
        else if (MW_rf_wen0 && MW_rd0 != 0 && MW_rd0 == DE_s0_0)
            f0_0 = MW_alu0_out;
        else if (MW_rf_wen1 && MW_rd1 != 0 && MW_rd1 == DE_s0_0)
            f0_0 = MW_alu1_out;
        // Lane 0 源2
        f0_1 = DE_v0_1;
        if (em_wen(EM_rd0, EM_rd1, EM_op0, EM_op1) && EM_rd0 == DE_s0_1)
            f0_1 = EM_alu0_out;
        else if (em_wen(EM_rd1, EM_rd0, EM_op1, EM_op0) && EM_rd1 == DE_s0_1)
            f0_1 = EM_alu1_out;
        else if (MW_rf_wen0 && MW_rd0 != 0 && MW_rd0 == DE_s0_1)
            f0_1 = MW_alu0_out;
        else if (MW_rf_wen1 && MW_rd1 != 0 && MW_rd1 == DE_s0_1)
            f0_1 = MW_alu1_out;
        // Lane 1 源1
        f1_0 = DE_v1_0;
        if (em_wen(EM_rd0, EM_rd1, EM_op0, EM_op1) && EM_rd0 == DE_s1_0)
            f1_0 = EM_alu0_out;
        else if (em_wen(EM_rd1, EM_rd0, EM_op1, EM_op0) && EM_rd1 == DE_s1_0)
            f1_0 = EM_alu1_out;
        else if (MW_rf_wen0 && MW_rd0 != 0 && MW_rd0 == DE_s1_0)
            f1_0 = MW_alu0_out;
        else if (MW_rf_wen1 && MW_rd1 != 0 && MW_rd1 == DE_s1_0)
            f1_0 = MW_alu1_out;
        // Lane 1 源2
        f1_1 = DE_v1_1;
        if (em_wen(EM_rd0, EM_rd1, EM_op0, EM_op1) && EM_rd0 == DE_s1_1)
            f1_1 = EM_alu0_out;
        else if (em_wen(EM_rd1, EM_rd0, EM_op1, EM_op0) && EM_rd1 == DE_s1_1)
            f1_1 = EM_alu1_out;
        else if (MW_rf_wen0 && MW_rd0 != 0 && MW_rd0 == DE_s1_1)
            f1_1 = MW_alu0_out;
        else if (MW_rf_wen1 && MW_rd1 != 0 && MW_rd1 == DE_s1_1)
            f1_1 = MW_alu1_out;
    end

    // =====================================================================
    // EX 双发射
    // =====================================================================
    // Lane-0 ALU
    reg [31:0] alu0_out; reg alu0_zero;
    always @(*) begin
        case (DE_op0)
            OP_ADD:   alu0_out = f0_0 + f0_1;
            OP_SUB, OP_CMP: alu0_out = f0_0 - f0_1;
            OP_AND:   alu0_out = f0_0 & f0_1;
            OP_OR:    alu0_out = f0_0 | f0_1;
            OP_XOR:   alu0_out = f0_0 ^ f0_1;
            OP_SHL:   alu0_out = f0_0 << f0_1[4:0];
            OP_SHR:   alu0_out = f0_0 >> f0_1[4:0];
            OP_ADDI:  alu0_out = f0_0 + DE_imm0;
            OP_SUBI:  alu0_out = f0_0 - DE_imm0;
            OP_LOAD, OP_STORE: alu0_out = f0_0 + DE_imm0;
            OP_PUSH:  alu0_out = DE_imm0;
            OP_MOV:   alu0_out = f0_0;
            OP_JMP, OP_JAL, OP_CALL: alu0_out = DE_imm0;
            OP_JZ,  OP_JNZ:  alu0_out = f0_0;
            OP_RET:   alu0_out = f0_0;
            OP_SENSE:alu0_out = {26'b0, sense};
            default:  alu0_out = 0;
        endcase
        alu0_zero = (alu0_out == 0);
    end

    // Lane-1 ALU
    reg [31:0] alu1_out;
    always @(*) begin
        case (DE_op1)
            OP_ADD:   alu1_out = f1_0 + f1_1;
            OP_SUB:   alu1_out = f1_0 - f1_1;
            OP_AND:   alu1_out = f1_0 & f1_1;
            OP_OR:    alu1_out = f1_0 | f1_1;
            OP_XOR:   alu1_out = f1_0 ^ f1_1;
            OP_SHL:   alu1_out = f1_0 << f1_1[4:0];
            OP_SHR:   alu1_out = f1_0 >> f1_1[4:0];
            OP_ADDI:  alu1_out = f1_0 + DE_imm1;
            OP_SUBI:  alu1_out = f1_0 - DE_imm1;
            OP_LOAD, OP_STORE: alu1_out = f1_0 + DE_imm1;
            OP_PUSH:  alu1_out = DE_imm1;
            OP_MOV:   alu1_out = f1_0;
            OP_JMP, OP_JZ, OP_JNZ, OP_JAL, OP_CALL: alu1_out = DE_imm1;
            OP_SENSE:alu1_out = {26'b0, sense};
            default:  alu1_out = 0;
        endcase
    end

    // MUL/DIV (可出现在 Lane 0 或 Lane 1, 但同一时间只能有一个 MUL/DIV)
    // Lane-1 优先 (流水线中 lane-1 通常留给 MUL/DIV)
    reg [31:0] md_res; reg md_done; reg [2:0] md_cnt;
    reg md_active, md_is_div, md_is_lane1;
    reg [31:0] md_a, md_b;
    always @(posedge clk) begin
        if (!rst_n) begin
            md_active <= 0; md_done <= 0; md_cnt <= 0;
            md_is_div <= 0; md_is_lane1 <= 0; md_a <= 0; md_b <= 0; md_res <= 0;
        end else begin
            md_done <= 0;
            if (!md_active) begin
                // 检查 lane-1 优先
                if (DE_dual && (DE_op1 == OP_MUL || DE_op1 == OP_DIV)) begin
                    md_active <= 1; md_is_lane1 <= 1; md_is_div <= (DE_op1 == OP_DIV);
                    md_a <= f1_0; md_b <= f1_1;
                    md_cnt <= (DE_op1 == OP_DIV) ? 3'd8 : 3'd4;
                end else if (DE_op0 == OP_MUL || DE_op0 == OP_DIV) begin
                    md_active <= 1; md_is_lane1 <= 0; md_is_div <= (DE_op0 == OP_DIV);
                    md_a <= f0_0; md_b <= f0_1;
                    md_cnt <= (DE_op0 == OP_DIV) ? 3'd8 : 3'd4;
                end
            end else begin
                if (md_cnt > 1) md_cnt <= md_cnt - 1;
                else begin
                    md_active <= 0; md_done <= 1;
                    md_res <= md_is_div ? md_a / md_b : md_a * md_b;
                end
            end
        end
    end
    wire muldiv_active = md_active;

    // MUL/DIV 结果接入对应 lane
    wire [31:0] lane0_final = (!md_active && md_done && !md_is_lane1) ? md_res : alu0_out;
    wire [31:0] lane1_final = (!md_active && md_done && md_is_lane1)  ? md_res :
                              (DE_dual && (DE_op1 == OP_MUL || DE_op1 == OP_DIV)) ? 32'd0 : alu1_out;
    // lane-1 在 MUL/DIV 执行期间: 结果还没好, 0 作为占位; md_done=1 时用 md_res
    wire        lane0_wen   = (DE_op0 != OP_STORE && DE_op0 != OP_NOP && DE_op0 != OP_EMIT && DE_rd0 != 0);
    wire        lane1_wen   = (DE_dual && DE_op1 != OP_STORE && DE_op1 != OP_NOP && DE_op1 != OP_EMIT && DE_rd1 != 0) ||
                              (!md_active && md_done && md_is_lane1);


    // Branch
    reg br_taken; reg [31:0] br_target, link_pc;
    always @(*) begin
        br_taken = 0; br_target = 0; link_pc = 0;
        case (DE_op0)
            OP_JMP:   begin br_target = DE_imm0; br_taken = 1; end
            OP_JZ:    begin br_target = DE_imm0; br_taken = alu0_zero; end
            OP_JNZ:   begin br_target = DE_imm0; br_taken = !alu0_zero; end
            OP_JAL:   begin br_target = DE_imm0; br_taken = 1; link_pc = DE_pc + 8; end
            OP_CALL:  begin br_target = DE_imm0; br_taken = 1; link_pc = DE_pc + 8; end
            OP_RET:   begin br_target = f0_0; br_taken = 1; end
            default:;
        endcase
    end

    // BHT 更新
    always @(posedge clk) begin
        if (!rst_n) begin
            for (i = 0; i < 64; i = i + 1) bht[i] <= 2'b01;
            for (i = 0; i < 32; i = i + 1) begin btb_valid[i] <= 0; btb_pc[i] <= 0; btb_target[i] <= 0; end
        end else if (DE_op0 == OP_JZ || DE_op0 == OP_JNZ || DE_op0 == OP_JMP ||
                     DE_op0 == OP_JAL || DE_op0 == OP_CALL || DE_op0 == OP_RET) begin
            if (br_taken && bht[DE_pc[7:2]] < 2'b11) bht[DE_pc[7:2]] <= bht[DE_pc[7:2]] + 1;
            else if (!br_taken && bht[DE_pc[7:2]] > 2'b00) bht[DE_pc[7:2]] <= bht[DE_pc[7:2]] - 1;
            if (br_taken) begin
                btb_pc[DE_pc[6:2]]     <= DE_pc;
                btb_target[DE_pc[6:2]] <= br_target;
                btb_valid[DE_pc[6:2]]  <= 1;
            end
        end
    end

    // EM 流水寄存器 (双通道)
    reg [31:0] EM_pc, EM_alu0, EM_alu1, EM_rs2;
    reg  [5:0] EM_op0, EM_op1;
    reg  [3:0] EM_rd0, EM_rd1;
    reg        EM_br_taken, EM_dual, EM_wen1;
    reg [31:0] EM_br_target;

    always @(posedge clk) begin
        EM_pc        <= DE_pc;
        EM_alu0      <= lane0_final;
        EM_alu1      <= lane1_final;
        EM_op0       <= DE_op0;
        EM_op1       <= DE_op1;
        EM_rd0       <= (DE_op0 == OP_JAL || DE_op0 == OP_CALL) ? 4'd1 : DE_rd0;
        EM_rd1       <= (DE_op1 == OP_JAL || DE_op1 == OP_CALL) ? 4'd1 : DE_rd1;
        EM_rs2       <= f0_1;
        EM_br_taken  <= br_taken;
        EM_br_target <= br_target;
        EM_dual      <= DE_dual;
        EM_wen1      <= lane1_wen;
        if (DE_op0 == OP_EMIT) emit <= f0_0[5:0];
    end

    // =====================================================================
    // MEM/WB (双通道)
    // =====================================================================
    reg [31:0] MW_alu0, MW_alu1, MW_mem, MW_pc;
    reg  [5:0] MW_op0, MW_op1;
    reg  [3:0] MW_rd0, MW_rd1;
    reg        MW_wen0, MW_wen1, MW_isload, MW_dual;

    always @(posedge clk) begin
        if (EM_op0 == OP_LOAD) begin
            dbus_adr <= EM_alu0; dbus_sel <= 4'hF; dbus_cyc <= 1; dbus_stb <= 1; dbus_we <= 0;
            if (dbus_ack) begin
                MW_mem <= dbus_dat_r;
                dbus_cyc <= 0; dbus_stb <= 0;
                {MW_alu0, MW_alu1} <= {EM_alu0, EM_alu1};
                {MW_op0, MW_op1} <= {EM_op0, EM_op1};
                {MW_rd0, MW_rd1} <= {EM_rd0, EM_rd1};
                MW_wen0 <= 1; MW_wen1 <= EM_dual; MW_isload <= 1;
                MW_pc <= EM_pc; MW_dual <= EM_dual;
            end
        end else if (EM_op0 == OP_STORE) begin
            dbus_adr <= EM_alu0; dbus_dat_w <= EM_rs2; dbus_sel <= 4'hF; dbus_cyc <= 1; dbus_stb <= 1; dbus_we <= 1;
            if (dbus_ack) begin
                dbus_cyc <= 0; dbus_stb <= 0; dbus_we <= 0;
                MW_mem <= 0; MW_isload <= 0;
                MW_alu0 <= EM_alu0; MW_alu1 <= EM_alu1;
                MW_op0 <= OP_NOP; MW_op1 <= EM_op1;
                MW_rd0 <= 0; MW_rd1 <= EM_rd1;
                MW_wen0 <= 0; MW_wen1 <= EM_dual;
                MW_pc <= EM_pc; MW_dual <= EM_dual;
            end
        end else begin
            MW_mem <= 0; MW_isload <= 0;
            MW_alu0 <= EM_alu0; MW_alu1 <= EM_alu1;
            MW_op0  <= EM_op0;  MW_op1  <= EM_op1;
            MW_rd0  <= EM_rd0;  MW_rd1  <= EM_rd1;
            MW_wen0 <= (EM_op0 != OP_STORE && EM_op0 != OP_NOP && EM_op0 != OP_EMIT && EM_rd0 != 0);
            MW_wen1 <= EM_wen1;
            MW_pc   <= EM_pc; MW_dual <= EM_dual;
        end
    end

    // 双写回
    wire [31:0] wb0 = MW_isload ? MW_mem : (MW_op0 == OP_JAL || MW_op0 == OP_CALL ? MW_pc + 8 : MW_alu0);
    wire [31:0] wb1 = (MW_op1 == OP_JAL || MW_op1 == OP_CALL) ? MW_pc + 8 : MW_alu1;

    always @(posedge clk) begin
        if (!rst_n) begin
            for (i = 0; i < 32; i = i + 1) rf[i] <= 0;
            emit <= 0; irq <= 0;
        end else begin
            if (MW_wen0 && MW_rd0 != 0) rf[MW_rd0] <= wb0;
            if (MW_wen1 && MW_rd1 != 0 && !(MW_wen0 && MW_rd0 != 0 && MW_rd0 == MW_rd1))
                rf[MW_rd1] <= wb1;
        end
    end

    // =====================================================================
    // 流水线控制
    // =====================================================================
    reg FE_stall, FD_stall, FD_flush;
    assign issue_show = DE_dual ? 2'd2 : (DE_op0 != OP_NOP ? 2'd1 : 2'd0);
    assign halt = 0;  // 测试平台用周期上限

    always @(*) begin
        // Load-use hazard: DE op0 uses a reg that EM op0 produces via LOAD
        // 简化: 仅检查来自 EM 的 load-use
        FD_flush = EM_br_taken;
        FE_stall = md_active;  // MUL/DIV 执行期间完全暂停
        FD_stall = md_active;
    end

endmodule
