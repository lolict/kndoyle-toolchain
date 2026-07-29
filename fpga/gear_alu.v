// 混元齿轮核 v0.6 — 单齿 ALU（6 bit 加减，啮合点 = 进位/借位）
// 齿轮传动律：满 64 进一，借位绕回
module GearALU (
    input  wire [5:0] a, b,
    input  wire       sub,          // 0 = 加, 1 = 减
    output wire [5:0] result,
    output wire       carry         // 加法=进位; 减法=取反即借位
);
    wire [7:0] full;
    wire [5:0] b2;
    assign b2    = sub ? (b ^ 6'h3F) : b;      // 减法取 1 的补码
    assign full  = {2'b0, a} + {2'b0, b2} + {7'b0, sub};
    assign result = full[5:0];
    assign carry  = full[6];
endmodule
