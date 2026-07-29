// ============================================================================
// 混元 RISC CPU v1.0 — 可流片的多周期 RISC 处理器
// ============================================================================
// 架构特性:
//   - 64 进制指令编码（opcode 6 bit = 64 个码位）
//   - 32 位数据通路; 16 个通用寄存器 (R0 = 零)
//   - 多周期执行（面积友好，适合 ASIC）
//   - Wishbone 内存接口（经典，工具链支持好）
//   - 七族外设总线（感知/通道/设备/网络/时钟）
//
// 流水线: 取指(F) → 译码(D) → 执行(E) → 访存(M) → 写回(W)
// （多周期实现：每条指令占 3~5 个时钟）
//
// 指令格式 (32 bit):
//   [31:26] opcode   (6 bit)
//   [25:22] rd       (4 bit, 目标寄存器)
//   [21:18] rs1      (4 bit, 源寄存器 1)
//   [17:14] rs2      (4 bit, 源寄存器 2)
//   [13:0]  imm      (14 bit 立即数，符号扩展)
//
// 综合目标: SkyWater 130nm, Caravel 用户项目区域 (~1.2mm²)
// 估计门数: ~15K 标准单元（不含 ROM/SRAM）
// ============================================================================

`timescale 1ns / 1ps

module hunyuan_cpu (
    input  wire        clk,
    input  wire        rst_n,        // 低有效复位

    // Wishbone 指令 memory 接口
    output reg         ibus_cyc,
    output reg         ibus_stb,
    output reg  [31:0] ibus_adr,
    input  wire [31:0] ibus_dat,
    input  wire        ibus_ack,

    // Wishbone 数据 memory 接口
    output reg         dbus_cyc,
    output reg         dbus_stb,
    output reg         dbus_we,
    output reg  [3:0]  dbus_sel,
    output reg  [31:0] dbus_adr,
    output reg  [31:0] dbus_dat_w,
    input  wire [31:0] dbus_dat_r,
    input  wire        dbus_ack,

    // 外设 I/O 族
    input  wire [5:0]  sense,        // 传感器输入
    output reg  [5:0]  emit,         // 执行器输出
    output reg         irq,          // 中断请求（保留）

    // 调试 / 状态
    output wire [31:0] pc_show,      // 当前 PC（用于调试）
    output wire        halt          // HALT 状态
);

    // =====================================================================
    // 操作码定义 (6 bit)
    // =====================================================================
    localparam [5:0] OP_NOP    = 6'h00,
                     OP_PUSH   = 6'h01,   // PUSH imm → R0=推入值，存栈
                     OP_ADD    = 6'h03,   // rd = rs1 + rs2
                     OP_SUB    = 6'h04,
                     OP_MUL    = 6'h05,
                     OP_AND    = 6'h06,
                     OP_OR     = 6'h07,
                     OP_XOR    = 6'h08,
                     OP_SHL    = 6'h09,
                     OP_SHR    = 6'h0A,
                     OP_LOAD   = 6'h11,   // rd = mem[rs1+imm]
                     OP_STORE  = 6'h10,   // mem[rs1+imm] = rs2
                     OP_JMP    = 6'h0D,   // PC = rs1（或 imm）
                     OP_JZ     = 6'h0E,   // if R0==0 goto rs1/imm
                     OP_JNZ    = 6'h0F,
                     OP_CALL   = 6'h26,   // 返回地址存 rd，跳转
                     OP_RET    = 6'h27,   // 跳到 rd 所存地址
                     OP_SENSE  = 6'h24,   // rd = sense[rs1]
                     OP_EMIT   = 6'h25,   // emit = rs1
                     OP_CMP    = 6'h0B,   // 比较 → R0 = (rs1<rs2 ? -1 : (rs1==rs2 ? 0 : 1))
                     OP_MOV    = 6'h02,   // rd = rs1
                     OP_ADDI   = 6'h13,   // rd = rs1 + imm
                     OP_SUBI   = 6'h14,
                     OP_JAL    = 6'h15;   // rd = PC+4, PC = imm

    // =====================================================================
    // 寄存器文件
    // =====================================================================
    reg [31:0] r [0:15];    // r 0..15
    wire [31:0] pc;         // 程序计数器
    reg        zero;        // R0 零标志（用于条件跳转）
    reg [31:0] result;      // ALU 输出

    // 流水线状态
    reg [2:0]  state;       // F/D/E/M/W
    reg [31:0] instr;       // 当前指令
    reg [31:0] pc_reg;      // PC 寄存器
    reg [31:0] op_a, op_b;  // ALU 操作数
    reg [31:0] rs1_v, rs2_v;// 寄存器值锁存
    reg [5:0]  opcode;
    reg [3:0]  field_rd, field_rs1, field_rs2;
    reg [13:0] field_imm;
    reg [31:0] imm_ext;     // 符号扩展后立即数

    assign pc_show = pc_reg;
    assign halt    = (state == 3'd6);   // HALT 状态编码

    localparam [2:0] ST_F   = 3'd0,
                     ST_D   = 3'd1,
                     ST_E   = 3'd2,
                     ST_M   = 3'd3,
                     ST_W   = 3'd4,
                     ST_HALT = 3'd6;

    // 符号扩展
    wire [31:0] imm32 = {{18{field_imm[13]}}, field_imm};

    integer i;

    // =====================================================================
    // 多周期状态机
    // =====================================================================
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state    <= ST_F;
            pc_reg   <= 32'h0;
            zero     <= 1'b0;
            result   <= 32'h0;
            irq      <= 1'b0;
            emit     <= 6'h0;
            ibus_cyc <= 1'b0;
            ibus_stb <= 1'b0;
            dbus_cyc <= 1'b0;
            dbus_stb <= 1'b0;
            dbus_we  <= 1'b0;
            for (i = 0; i < 16; i = i + 1)
                r[i] <= 32'h0;
        end else begin
            case (state)
            // ---- 取指 F ----
            ST_F: begin
                ibus_adr <= pc_reg;
                ibus_cyc <= 1'b1;
                ibus_stb <= 1'b1;
                if (ibus_ack) begin
                    instr    <= ibus_dat;
                    ibus_cyc <= 1'b0;
                    ibus_stb <= 1'b0;
                    state    <= ST_D;
                end
            end

            // ---- 译码 D ----
            ST_D: begin
                opcode   <= instr[31:26];
                field_rd <= instr[25:22];
                field_rs1<= instr[21:18];
                field_rs2<= instr[17:14];
                field_imm<= instr[13:0];
                imm_ext  <= imm32;
                rs1_v    <= r[instr[21:18]];
                rs2_v    <= r[instr[17:14]];
                state    <= ST_E;
            end

            // ---- 执行 E ----
            ST_E: begin
                case (opcode)
                OP_ADD:  result <= rs1_v + rs2_v;
                OP_SUB:  result <= rs1_v - rs2_v;
                OP_MUL:  result <= rs1_v * rs2_v;
                OP_AND:  result <= rs1_v & rs2_v;
                OP_OR:   result <= rs1_v | rs2_v;
                OP_XOR:  result <= rs1_v ^ rs2_v;
                OP_SHL:  result <= rs1_v << rs2_v[4:0];
                OP_SHR:  result <= rs1_v >> rs2_v[4:0];
                OP_CMP:  result <= (rs1_v < rs2_v) ? 32'hFFFFFFFF :
                                    (rs1_v == rs2_v) ? 32'h0 : 32'h1;
                OP_MOV:  result <= rs1_v;
                OP_ADDI: result <= rs1_v + imm_ext;
                OP_SUBI: result <= rs1_v - imm_ext;
                OP_PUSH: result <= imm_ext;
                OP_SENSE: result <= {26'h0, sense};
                OP_EMIT: begin
                    emit  <= rs1_v[5:0];
                    result <= 32'h0;
                end
                OP_JMP:  result <= rs1_v;
                OP_JZ:   result <= (zero) ? rs1_v : pc_reg + 32'h4;
                OP_JNZ:  result <= (!zero) ? rs1_v : pc_reg + 32'h4;
                OP_CALL: result <= pc_reg + 32'h4;  // 返回地址
                OP_RET:  result <= rs1_v;
                OP_JAL:  result <= pc_reg + 32'h4;
                default: result <= 32'h0;
                endcase

                // 更新零标志
                if (opcode == OP_CMP || opcode == OP_SUB)
                    zero <= (result == 32'h0);
                else if (opcode == OP_ADD || opcode == OP_ADDI)
                    zero <= (result == 32'h0);

                // 分支跳转
                if (opcode == OP_JMP || (opcode == OP_JZ && zero) ||
                    (opcode == OP_JNZ && !zero) || opcode == OP_JAL) begin
                    pc_reg <= (opcode == OP_JAL) ? imm_ext : rs1_v;
                    state  <= ST_F;
                end else if (opcode == OP_CALL) begin
                    pc_reg <= imm_ext;
                    state  <= ST_W;   // 写回返回地址
                end else if (opcode == OP_RET) begin
                    pc_reg <= rs1_v;
                    state  <= ST_F;
                end else if (opcode == OP_LOAD || opcode == OP_STORE) begin
                    state  <= ST_M;
                end else begin
                    state  <= ST_W;
                end
            end

            // ---- 访存 M ----
            ST_M: begin
                dbus_adr   <= rs1_v + imm_ext;
                dbus_sel   <= 4'hF;
                dbus_cyc   <= 1'b1;
                dbus_stb   <= 1'b1;
                dbus_we    <= (opcode == OP_STORE);
                dbus_dat_w <= rs2_v;
                if (dbus_ack) begin
                    result   <= (opcode == OP_LOAD) ? dbus_dat_r : 32'h0;
                    dbus_cyc <= 1'b0;
                    dbus_stb <= 1'b0;
                    dbus_we  <= 1'b0;
                    state    <= ST_W;
                end
            end

            // ---- 写回 W ----
            ST_W: begin
                if (field_rd != 4'h0)  // R0 不可写
                    r[field_rd] <= result;
                pc_reg <= pc_reg + 32'h4;
                state  <= ST_F;
            end

            default: state <= ST_F;
            endcase
        end
    end

endmodule
