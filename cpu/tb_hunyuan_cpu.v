// 混元 CPU 测试平台 v1.0 —— 验证 Σ(1..100)=5050 + 传感器读取
`timescale 1ns / 1ps

module tb_hunyuan_cpu;

    reg clk, rst_n;
    initial clk = 0;
    always #5 clk = ~clk;    // 100 MHz

    // Wishbone 指令 mem
    wire        ibus_cyc, ibus_stb;
    wire [31:0] ibus_adr;
    wire [31:0] ibus_dat;
    wire        ibus_ack;

    // Wishbone 数据 mem
    wire        dbus_cyc, dbus_stb, dbus_we;
    wire [3:0]  dbus_sel;
    wire [31:0] dbus_adr, dbus_dat_w;
    wire [31:0] dbus_dat_r;
    wire        dbus_ack;

    wire [5:0]  sense;
    wire [5:0]  emit;
    wire [31:0] pc_show;
    wire        halt;

    // 内存模型: 4KB I-mem, 4KB D-mem
    reg [31:0] imem [0:1023];
    reg [31:0] dmem [0:1023];

    wire [9:0] ia = ibus_adr[11:2];
    wire [9:0] da = dbus_adr[11:2];

    assign ibus_dat = imem[ia];
    assign ibus_ack = ibus_cyc & ibus_stb;
    assign dbus_dat_r = dmem[da];
    assign dbus_ack = dbus_cyc & dbus_stb;

    // 写 D-mem
    always @(posedge clk) begin
        if (dbus_cyc && dbus_stb && dbus_we)
            dmem[da] <= dbus_dat_w;
    end

    // 传感器
    assign sense = 6'd42;

    hunyuan_cpu u_cpu (
        .clk(clk),
        .rst_n(rst_n),
        .ibus_cyc(ibus_cyc),
        .ibus_stb(ibus_stb),
        .ibus_adr(ibus_adr),
        .ibus_dat(ibus_dat),
        .ibus_ack(ibus_ack),
        .dbus_cyc(dbus_cyc),
        .dbus_stb(dbus_stb),
        .dbus_we(dbus_we),
        .dbus_sel(dbus_sel),
        .dbus_adr(dbus_adr),
        .dbus_dat_w(dbus_dat_w),
        .dbus_dat_r(dbus_dat_r),
        .dbus_ack(dbus_ack),
        .sense(sense),
        .emit(emit),
        .pc_show(pc_show),
        .halt(halt)
    );

    // ----------------------------------------------------------------
    // 辅助任务
    // ----------------------------------------------------------------
    task write_instr;
        input [9:0] addr;
        input [31:0] data;
        begin imem[addr] = data; end
    endtask

    task write_data;
        input [9:0] addr;
        input [31:0] data;
        begin dmem[addr] = data; end
    endtask

    // 指令构造函数 (见 cpu/hunyuan_cpu.v 中的编码)
    function [31:0] instr;
        input [5:0] op;
        input [3:0] rd, rs1, rs2;
        input [13:0] imm;
        instr = {op, rd, rs1, rs2, imm};
    endfunction

    // ----------------------------------------------------------------
    // 测试: Σ(1..100) = 5050
    // ----------------------------------------------------------------
    // 伪代码:
    //   r1 = i = 1        (ADDI r1, r0, 1)
    //   r2 = N = 100      (ADDI r2, r0, 100)
    //   r3 = sum = 0      (ADDI r3, r0, 0)
    // loop:
    //   r3 = r3 + r1      (ADD  r3, r3, r1)
    //   r1 = r1 + 1       (ADDI r1, r1, 1)
    //   if r1 <= r2 goto loop (CMP + SUB + 条件跳转)
    //   store r3 to dmem   (STORE r3, r0, 0)
    //   HALT               (转发 NOP 收尾)

    initial begin
        rst_n = 0;
        #100;
        rst_n = 1;
        #20;

        // 程序: Σ(1..100) = 5050
        // R0=0, R1=i, R2=N, R3=sum

        // addr 0: r1 = 1
        write_instr(0, instr(6'h13, 4'd1, 4'd0, 4'd0, 14'd1));
        // addr 1: r2 = 100
        write_instr(1, instr(6'h13, 4'd2, 4'd0, 4'd0, 14'd100));
        // addr 2: r3 = 0
        write_instr(2, instr(6'h13, 4'd3, 4'd0, 4'd0, 14'd0));

        // addr 3: loop: r3 = r3 + r1
        write_instr(3, instr(6'h03, 4'd3, 4'd3, 4'd1, 14'd0));
        // addr 4: r1 = r1 + 1
        write_instr(4, instr(6'h13, 4'd1, 4'd1, 4'd0, 14'd1));
        // addr 5: cmp  r1 - r2 → 若 r1 <= r2 跳转回 3
        write_instr(5, instr(6'h04, 4'd4, 4'd1, 4'd2, 14'd0));
        // addr 6: if r4 != 0 (r1 > r2) goto addr 8 (跳过循环)
        write_instr(6, instr(6'h0F, 4'd0, 4'd2, 4'd0, 14'd8));
        // addr 7: goto addr 3 (loop)
        write_instr(7, instr(6'h0D, 4'd0, 4'd3, 4'd0, 14'd3));

        // addr 8: 存储 r3 到 dmem[0]
        write_instr(8, instr(6'h10, 4'd0, 4'd3, 4'd3, 14'd0));
        // addr 9: emit r1 (显示结果)
        write_instr(9, instr(6'h25, 4'd0, 4'd3, 4'd0, 14'd0));
        // addr 10: HALT (NOP 直到被停止)
        write_instr(10, instr(6'h00, 4'd0, 4'd0, 4'd0, 14'd0));
        // addr 11.. 都用 NOP 填充

        // 运行
        wait(halt || (dbus_cyc && dbus_stb && dbus_we && dbus_adr[11:2] == 0));
        #50;

        $display("========================================");
        $display("CPU 寄存器 dump:");
        for (integer i = 0; i < 16; i = i + 1)
            $display("  r%0d = %0d", i, u_cpu.r[i]);
        $display("========================================");
        $display("D-mem[0] (sum) = %0d", dmem[0]);
        $display(" emit = %0d", emit);

        if (dmem[0] == 32'd5050)
            $display("TEST PASSED: Σ(1..100) = 5050 ✓");
        else
            $display("TEST FAILED: got %0d expected 5050 ✗", dmem[0]);

        #100;
        $finish;
    end

    // 超时保护
    initial begin
        #100000;
        $display("TIMEOUT");
        $finish;
    end

endmodule
