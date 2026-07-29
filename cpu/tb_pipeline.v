// 混元流水线 CPU 测试平台 v1.1
`timescale 1ns / 1ps

module tb_hunyuan_cpu_pipelined;

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

    hunyuan_cpu_pipelined u_cpu (
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

    // Σ(1..100) = 5050 — 流水线版本
    initial begin
        rst_n = 0; #100; rst_n = 1; #20;

        write_instr(0,  instr(6'h13,1,0,0,14'd1));     // r1 = 1 (i)
        write_instr(1,  instr(6'h13,2,0,0,14'd100));   // r2 = 100 (N)
        write_instr(2,  instr(6'h13,3,0,0,14'd0));     // r3 = 0 (sum)
        // loop (addr 3):
        write_instr(3,  instr(6'h03,3,3,1,14'd0));     // r3 += r1
        write_instr(4,  instr(6'h13,1,1,0,14'd1));     // r1 += 1
        write_instr(5,  instr(6'h04,4,1,2,14'd0));     // r4 = r1 - r2
        write_instr(6,  instr(6'h0E,0,3,0,14'd3));     // if r4==0 goto 3 (loop)
        write_instr(7,  instr(6'h0D,0,3,0,14'd9));     // goto 9 (exit)
        write_instr(8,  instr(6'h00,0,0,0,14'd0));     // NOP (unused)
        write_instr(9,  instr(6'h10,0,3,3,14'd0));     // dmem[0] = r3
        write_instr(10, instr(6'h25,0,3,0,14'd0));     // emit r3
        write_instr(11, instr(6'h00,0,0,0,14'd0));     // NOP

        wait(dmem[0] != 0 || halt);
        #50;

        $display("========================================");
        $display("Pipeline CPU register dump:");
        for (integer i=0;i<16;i=i+1)
            $display("  r%0d = %0d", i, u_cpu.rf[i]);
        $display(" dmem[0] = %0d", dmem[0]);
        $display(" emit = %0d", emit);

        if (dmem[0] == 32'd5050)
            $display("PIPELINE TEST PASSED: Sigma(1..100) = 5050");
        else
            $display("PIPELINE TEST FAILED: got %0d expected 5050", dmem[0]);

        #100; $finish;
    end

    initial begin #200000; $display("TIMEOUT"); $finish; end

endmodule
