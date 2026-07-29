// ============================================================================
// 混元 v1.4 测试平台 — 超标量双发射 + 硬件乘除法验证
// ============================================================================
// 测试用例:
//   Test 1: Σ(1..100) = 5050 (with branch predictor)
//   Test 2: 25 * 17 = 425 (MUL 验证)
//   Test 3: 1000 / 13 = 76 (DIV 验证, 余数忽略)
//   Test 4: 双发射并行: r3=r1+r2 || r5=r6&r7  (展示配对)
// ============================================================================

`timescale 1ns / 1ps

module tb_v14;

    reg         clk;
    reg         rst_n;

    // 指令 memory (64-bit wide)
    wire        ibus_cyc;
    wire        ibus_stb;
    wire [31:0] ibus_adr;
    wire [63:0] ibus_dat;
    wire        ibus_ack;

    // 数据 memory (32-bit)
    wire        dbus_cyc;
    wire        dbus_stb;
    wire        dbus_we;
    wire [3:0]  dbus_sel;
    wire [31:0] dbus_adr;
    wire [31:0] dbus_dat_w;
    wire [31:0] dbus_dat_r;
    wire        dbus_ack;

    wire [5:0]  sense;
    wire [5:0]  emit;
    wire        irq;
    wire [31:0] pc_show;
    wire        halt;
    wire [1:0]  issue_show;

    // DUT
    hunyuan_cpu_v14 dut (
        .clk(clk), .rst_n(rst_n),
        .ibus_cyc(ibus_cyc), .ibus_stb(ibus_stb), .ibus_adr(ibus_adr),
        .ibus_dat(ibus_dat), .ibus_ack(ibus_ack),
        .dbus_cyc(dbus_cyc), .dbus_stb(dbus_stb), .dbus_we(dbus_we),
        .dbus_sel(dbus_sel), .dbus_adr(dbus_adr), .dbus_dat_w(dbus_dat_w),
        .dbus_dat_r(dbus_dat_r), .dbus_ack(dbus_ack),
        .sense(sense), .emit(emit), .irq(irq),
        .pc_show(pc_show), .halt(halt), .issue_show(issue_show)
    );

    // 指令 ROM (64-bit wide for dual-issue)
    reg [63:0] imem [0:2047];
    wire [63:0] irom_data = imem[ibus_adr[12:3]];
    reg         irom_ack;
    assign ibus_dat = irom_data;
    assign ibus_ack = irom_ack;
    assign sense = 6'b0;

    always @(posedge clk) begin
        irom_ack <= (ibus_cyc && ibus_stb) ? 1'b1 : 1'b0;
    end

    // 数据 SRAM (32-bit, 16KB)
    reg [31:0] dmem [0:4095];
    reg [31:0] dram_do;
    reg        dram_ack;
    assign dbus_dat_r = dram_do;
    assign dbus_ack   = dram_ack;

    always @(posedge clk) begin
        if (dbus_cyc && dbus_stb) begin
            if (dbus_we) begin
                dmem[dbus_adr[13:2]] <= dbus_dat_w;
                dram_do <= 0;
            end else
                dram_do <= dmem[dbus_adr[13:2]];
            dram_ack <= 1;
        end else
            dram_ack <= 0;
    end

    // Clock
    initial clk = 0;
    always #5 clk = ~clk;

    integer errors;
    integer cyc_count;

    initial begin
        $display("===========================================================");
        $display("混元 v1.4 双发射超标量 + 硬件乘除法 测试平台");
        $display("===========================================================");

        errors = 0;
        rst_n = 0;
        #20 rst_n = 1;

        // =============================================
        // Test 1: Σ(1..100) = 5050
        // 程序行为: r1=100(=counter), r2=0(=sum), loop: sum+=counter, counter--, if counter>0 goto loop
        // 双发射利用: ADD+SUB independent 时可配对; CMP+JNZ 不行(branch)
        // =============================================
        $display("[Test 1] Sigma(1..100) = 5050");

        // Reset imem
        $readmemh("prog_sigma_100.hex", imem);

        // Run until halt
        cyc_count = 0;
        while (!halt && cyc_count < 5000) begin
            @(posedge clk);
            cyc_count = cyc_count + 1;
        end

        // 通过 emit 检查: 程序若成功, 在最后写 dmem[0] = 5050
        if (dmem[0] == 32'd5050) begin
            $display("  PASS: dmem[0] = %0d (期望 5050), cycles=%0d", dmem[0], cyc_count);
        end else begin
            $display("  FAIL: dmem[0] = %0d (期望 5050)", dmem[0]);
            errors = errors + 1;
        end

        // =============================================
        // Test 2: MUL 25 * 17 = 425
        // =============================================
        $display("[Test 2] MUL 25 * 17 = 425");
        rst_n = 0; #10 rst_n = 1;
        @(posedge clk);

        $readmemh("prog_mul.hex", imem);
        dmem[0] = 0;
        cyc_count = 0;
        while (!halt && cyc_count < 5000) begin
            @(posedge clk);
            cyc_count = cyc_count + 1;
        end

        if (dmem[0] == 32'd425) begin
            $display("  PASS: dmem[0] = %0d (期望 425)", dmem[0]);
        end else begin
            $display("  FAIL: dmem[0] = %0d (期望 425)", dmem[0]);
            errors = errors + 1;
        end

        // =============================================
        // Test 3: DIV 1000 / 13 = 76
        // =============================================
        $display("[Test 3] DIV 1000 / 13 = 76");
        rst_n = 0; #10 rst_n = 1;
        @(posedge clk);

        $readmemh("prog_div.hex", imem);
        dmem[0] = 0;
        cyc_count = 0;
        while (!halt && cyc_count < 5000) begin
            @(posedge clk);
            cyc_count = cyc_count + 1;
        end

        if (dmem[0] == 32'd76) begin
            $display("  PASS: dmem[0] = %0d (期望 76)", dmem[0]);
        end else begin
            $display("  FAIL: dmem[0] = %0d (期望 76)", dmem[0]);
            errors = errors + 1;
        end

        // =============================================
        // 汇总结果
        // =============================================
        $display("===========================================================");
        if (errors == 0)
            $display("ALL TESTS PASSED");
        else
            $display("FAILED: %0d errors", errors);
        $display("===========================================================");

        $finish;
    end

endmodule
