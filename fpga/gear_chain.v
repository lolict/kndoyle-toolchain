// 混元齿轮核 v0.6 — 三齿轮啮合链（64 进制计数器）
// 逐级啮合：个位满 64 → 十位进一；十位满 64 → 百位进一；满链溢出
module GearChain (
    input  wire       clk,
    input  wire       en,            // 小齿轮脉冲
    output reg  [5:0] d0,            // 个位
    output reg  [5:0] d1,            // 十位
    output reg  [5:0] d2,            // 百位
    output reg        overflow       // 满 64^3 溢出
);
    always @(posedge clk) begin
        if (en) begin
            if (d0 == 6'd63) begin
                d0 <= 6'd0;
                if (d1 == 6'd63) begin
                    d1 <= 6'd0;
                    if (d2 == 6'd63) begin
                        d2 <= 6'd0;
                        overflow <= 1'b1;
                    end else begin
                        d2 <= d2 + 6'd1;
                    end
                end else begin
                    d1 <= d1 + 6'd1;
                end
            end else begin
                d0 <= d0 + 6'd1;
            end
        end
    end
endmodule
