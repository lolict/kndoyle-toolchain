// 混元 FPGA 顶层 v0.6 — 12 MHz ↗ 慢闪 LED 演示
// Tang Nano 9K / iCE40UP5K: 12 MHz 晶振 → 26 位分频 → 1Hz 使能 → 64 进制计数 → 7 路 LED
module HunYuanTop (
    input  wire       clk,           // 12 MHz
    input  wire       rst,           // 按键复位（低有效）
    output wire [6:0] led            // [5:0] = 个位齿轮, [6] = 溢出
);
    reg [25: 0] div;
    wire        en;
    wire [5:0]  d0;

    assign en = &div;                // div 全 1 时产生一个使能脉冲

    always @(posedge clk) begin
        if (!rst) div <= 26'd0;
        else      div <= div + 26'd1;
    end

    GearChain u_counter (
        .clk(clk),
        .en(en),
        .d0(d0),
        .d1(),
        .d2(),
        .overflow(/* unused */)
    );

    assign led = d0;

endmodule
