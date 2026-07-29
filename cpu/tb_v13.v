// 混元 CPU v1.3 测试平台 — 分支预测 + OoO 验证
`timescale 1ns / 1ps

module tb_hunyuan_cpu_v13;

    reg clk, rst_n;
    initial clk = 0;
    always #5 clk = ~clk;

    wire        ibus_cyc, ibus_stb;
    wire [31:0] ibus_adr, ibus_dat;
    wire        ibus_ack;
    wire        dbus_cyc, dbus_stb, dbus_we;
    wire [3:0]  dbus_sel;
    wire [31:0] dbus_adr, dbus_dat_w, dbus_dat_r;
    wire        dbus_ack;
    wire [5:0]  sense;
    wire [5:0]  emit;
    wire [31:0] pc_show;
    wire        halt;

    reg [31:0] imem [0:1023];
    reg [31:0] dmem [0:1023];

    wire [9:0] ia = ibus_adr[11:2];
    wire [9:0] da = dbus_adr[11:2];

    assign ibus_dat = imem[ia];
    assign ibus_ack = ibus_cyc & ibus_stb;
    assign dbus_dat_r = dmem[da];
    assign dbus_ack = dbus_cyc & dbus_stb;
    assign sense = 6'd42;

    always @(posedge clk)
        if (dbus_cyc && dbus_stb && dbus_we)
            dmem[da] <= dbus_dat_w;

    hunyuan_cpu_v13 #(.ROB_DEPTH(8), .PHYS_REGS(32)) u_cpu (
        .clk(clk), .rst_n(rst_n),
        .ibus_cyc(ibus_cyc), .ibus_stb(ibus_stb), .ibus_adr(ibus_adr),
        .ibus_dat(ibus_dat), .ibus_ack(ibus_ack),
        .dbus_cyc(dbus_cyc), .dbus_stb(dbus_stb), .dbus_we(dbus_we),
        .dbus_sel(dbus_sel), .dbus_adr(dbus_adr),
        .dbus_dat_w(dbus_dat_w), .dbus_dat_r(dbus_dat_r), .dbus_ack(dbus_ack),
        .sense(sense), .emit(emit), .irq(),
        .pc_show(pc_show), .halt(halt)
    );

    function [31:0] instr;
        input [5:0] op; input [3:0] rd, rs1, rs2; input [13:0] imm;
        instr = {op, rd, rs1, rs2, imm};
    endfunction

    task write_instr; input [9:0] a; input [31:0] d; begin imem[a]=d; end endtask

    // 测试: 循环 Σ(1..100) = 5050 (触发多次分支预测)
    initial begin
        rst_n = 0; #100; rst_n = 1; #20;

        // 0: r1 = 1 (i)
        write_instr(0,  instr(6'd19,1,0,0,14'd1));
        // 1: r2 = 100 (N)
        write_instr(1,  instr(6'd19,2,0,0,14'd100));
        // 2: r3 = 0 (sum)
        write_instr(2,  instr(6'd19,3,0,0,14'd0));
        // 3: loop: r3 += r1
        write_instr(3,  instr(6'd3,3,3,1,14'd0));
        // 4: r1 += 1
        write_instr(4,  instr(6'd19,1,1,0,14'd1));
        // 5: r4 = r1 - r2
        write_instr(5,  instr(6'd4,4,1,2,14'd0));
        // 6: if r4 == 0 goto loop (addr 3)
        write_instr(6,  instr(6'd14,0,0,0,14'd3));
        // 7: goto exit (addr 9)
        write_instr(7,  instr(6'd13,0,0,0,14'd9));
        // 8: NOP
        write_instr(8,  instr(6'd0,0,0,0,14'd0));
        // 9: store r3 to dmem[0]
        write_instr(9,  instr(6'd16,0,0,3,14'd0));
        // 10: emit sum
        write_instr(10, instr(6'd37,0,3,0,14'd0));
        // 11.. NOP

        wait(emit != 0 || dmem[0] != 0);
        #100;

        $display("========================================");
        $display("CPU v1.3 Pipeline + Prediction + OoO");
        $display(" dmem[0] (sum) = %0d", dmem[0]);
        $display(" emit = %0d", emit);
        $display(" predictions: BHT[0]=%b", u_cpu.bht[0]);

        if (dmem[0] == 32'd5050)
            $display("V1.3 TEST PASSED: Sigma(1..100) = 5050 ✓ (with branch prediction)");
        else
            $display("V1.3 TEST FAILED: got %0d expected 5050", dmem[0]);

        #100; $finish;
    end

    initial begin #300000; $display("TIMEOUT"); $finish; end

endmodule
