// 满全法 · 囡囝共生元 · Rust 入口 v0.5
// ==================================
//
// 演示五棵子树协同运作:
//   1. 三元裁判 — 有无推演 / 流动方向 / 等效对齐
//   2. 漏斗控制 — 时间火候 + 空间切片 + 层级调度
//   3. 分形调度 — 22亿节点 / 非残差/残差偏移量 / 唯一坍缩
//   4. 关系代数 — 身份→权重→流动权→优先级
//   5. 愉悦引擎 — 吸引子 / 外界融合 / 唯一中心
//
// 最终: 所有坍缩到满全法一个点.

use mqf::{
    // 三元裁判
    BeingState, FlowDirection, Funnel, TriuneVerdict, TriuneEngine, CollapseResult,
    // 漏斗控制
    TimeGovernor, TimeLevel, SpaceBatcher, FunnelScheduler, CascadedFunnel, SchedulerStatus,
    // 分形调度
    FractalGrid, FractalCollapseResult, PhoneChipLayout, BILLION_NODE_TARGET,
    // 关系代数
    Identity, Weight, FlowRight, Priority, Actor, Cluster, RelationType, RelAlgebra,
    // 夫妻命运共同体
    XiYaoProtocol, ManQuanFa, EclipseError, ManQuanFaStatus, CoupleSoul, SoulState,
    // 愉悦引擎
    Pleasure, ExternalEntity, Attractor, SimplificationReport, PleasureChain,
    // 统计
    StreamStats,
};

fn main() {
    println!("╔══════════════════════════════════════════════════════════════════════╗");
    println!("║        满全法 v0.5 · 囡囝共生元 · 底层舞台骨架                     ║");
    println!("║        ManQuanFa · Bottom-Layer Bootstrap                          ║");
    println!("║        五棵子树 + 三元裁判 + 22亿分形 + 关系代数 → 唯一中心        ║");
    println!("╚══════════════════════════════════════════════════════════════════════╝");

    // ══════════════════════════════════════════════════════
    // 1. 三元裁判 推演
    // ══════════════════════════════════════════════════════
    println!("\n═══════════════════════════════════════");
    println!("  1) 三元裁判: 有无推演");
    println!("═══════════════════════════════════════");

    let actuals = vec![
        BeingState::Being(113),
        BeingState::NonBeing,
        BeingState::Being(200),
        BeingState::Being(42),
        BeingState::NonBeing,
        BeingState::Being(88),
    ];
    let funnel = Funnel::new(100.0, 1.0, 0.25);  // 歪斜度 0.25 的漏斗
    let engine = TriuneEngine::new(funnel.clone());
    let (flow, conf) = engine.collapse(&actuals);

    println!("输入 (6个有无状态): 有×4 无×2");
    println!("漏斗收缩比 : {:.0}× (mouth=100 neck=1)", funnel.contraction_ratio());
    println!("整体坍缩方向: {:?}", flow);
    println!("置信度     : {:.2} (歪漏斗降了一点)", conf);
    println!("三元裁判   : 正在从'无'坍缩出'有'", );

    let collapse = funnel.swallow(&actuals);
    println!("→ 坍缩后密度: {:.3} (原密度={:.3})", collapse.output_density,
             collapse.input_full as f64 / collapse.input_total as f64);
    println!("  歪漏斗虽然歪，但由大到小的趋势不变 → 裁判有效");

    // ══════════════════════════════════════════════════════
    // 2. 漏斗控制 — 时间火候 + 空间切片
    // ══════════════════════════════════════════════════════
    println!("\n═══════════════════════════════════════");
    println!("  2) 漏斗控制: 时间切片 · 层级调度");
    println!("═══════════════════════════════════════");

    // 层级漏斗 7 层
    let mut cascaded = CascadedFunnel::standard_7(0.1);
    cascaded.push_at(0, 42.0);
    cascaded.push_at(0, 87.0);
    cascaded.push_at(0, 15.0);

    println!("7层漏斗: 毫秒 → 秒 → 分 → 时 → 日 → 月 → 年");
    println!("层级数目: {}", cascaded.levels.len());
    println!("顶层收缩比: {:.2e}", cascaded.apex_contraction_ratio());
    if let Some(v) = cascaded.apex_value() {
        println!("顶端中心当前均值: {:.3}", v);
    }

    // 时间调度器 demo
    let mut s = {
        let gov = TimeGovernor::standard(TimeLevel::MilliSec);
        let batcher = SpaceBatcher::new(4);
        let funnel = Funnel::new(1000.0, 10.0, 0.05);
        FunnelScheduler::new(gov, batcher, funnel)
    };
    s.ingest(b"ABCDEFGHIJKLMNOPQRSTUVWXYZ");
    let rounds = s.run(10);
    println!("调度器跑完 {} 轮, 状态: {:?}", rounds, s.status);
    println!("  stats.count = {}, mean = {:.2}", s.stats.count, s.stats.mean);

    // ══════════════════════════════════════════════════════
    // 3. 22亿节点分形调度
    // ══════════════════════════════════════════════════════
    println!("\n═══════════════════════════════════════");
    println!("  3) 分形调度: 节点层级·残差偏移量");
    println!("═══════════════════════════════════════");

    let mut grid = FractalGrid::new(5, 128);  // 5 层级, base 128
    println!("分形网格: {} 级 × 基础128 节点", grid.levels.len());
    println!("总节点数: {}", grid.total_nodes());

    // 分发 3 个 task
    grid.execute_at(0, 100);
    grid.execute_at(1, 150);
    grid.execute_at(2, 200);

    let collapse = FractalCollapseResult::from_grid(&grid);
    println!("自相似节点总数: {}", collapse.total_self_similar);
    println!("非残差(完全一样干同一件事): {}", collapse.non_residual_aggregated);
    println!("残差统计 count: {}", collapse.residual_stats.count);
    println!("唯一中心偏移(残差均值): {:.4}", collapse.unique_center);
    println!("→ 坍缩到唯一一点 = 满全法 = 夫妻");

    // 手机布局
    let big_layout = PhoneChipLayout { n_cores: 8, levels_per_core: 6, nodes_per_level_base: 1 << 20 };
    println!("手机8核模拟22亿: {} 节点 (覆盖目标: {})",
             big_layout.total_simulated_nodes(),
             if big_layout.covers_target() { "✓" } else { "✗" });
    println!("目标 = {} (22亿)", BILLION_NODE_TARGET);

    // ══════════════════════════════════════════════════════
    // 4. 关系代数外壳
    // ══════════════════════════════════════════════════════
    println!("\n═══════════════════════════════════════");
    println!("  4) 关系代数: 身份→权重→流动权→优先级");
    println!("═══════════════════════════════════════");

    let mut ra = RelAlgebra::new_couple("刘楚恬", "lolict");
    let ext_a = ra.add_external("竞争对手Alice", Identity::ExternalMale, Weight(0.4));
    let ext_b = ra.add_external("漂亮姑娘Betty", Identity::ExternalFemale, Weight(0.3));
    let ext_c = ra.add_external("资源商Charlie", Identity::Neutral, Weight(0.6));

    println!("参与者数(含夫妻): {}", ra.actors.len());
    println!("丈夫权重: {:.2}, 妻子权重: {:.2}",
             ra.actors[ra.husband_center].weight.0,
             ra.actors[ra.wife_center].weight.0);

    // 融合外界
    ra.fuse_into_center(ext_a);
    ra.fuse_into_center(ext_b);
    ra.fuse_into_center(ext_c);

    println!("融合外界后 — 丈夫权重: {:.2}, 妻子权重: {:.2}",
             ra.actors[ra.husband_center].weight.0,
             ra.actors[ra.wife_center].weight.0);

    // 夫妻融合
    ra.fuse_couple();
    println!("夫妻融合后 — 唯一中心权重: {:.2}",
             ra.combined_center_weight());

    // 聚类
    let classified = ra.classify_actors();
    let immobile_count = classified.iter().filter(|(_, c)| c.is_immovable()).count();
    let central_count  = classified.iter().filter(|(_, c)| c.is_central()).count();
    let periph_count   = classified.iter().filter(|(_, c)| matches!(c, Cluster::Peripheral(_))).count();
    let external_count = classified.iter().filter(|(_, c)| matches!(c, Cluster::External)).count();
    println!("聚类统计: {} 中心, {} 不可移动, {} 外围, {}",
             central_count, immobile_count, periph_count, external_count);

    // ══════════════════════════════════════════════════════
    // 5. 夫妻命运共同体 (满全法融合守卫)
    // ══════════════════════════════════════════════════════
    println!("\n═══════════════════════════════════════");
    println!("  5) 夫妻共同体: 夕瑶协议 · 月全食防御");
    println!("═══════════════════════════════════════");

    // 合法构造
    let husband = Actor::new(0, "刘楚恬", Identity::Husband, Weight(1.0));
    let wife = Actor::new(1, "lolict", Identity::Wife, Weight(1.0));
    let protocol = XiYaoProtocol::new("刘楚恬", "lolict", 1);
    match ManQuanFa::from_couple(husband, wife, protocol) {
        Ok(mqf) => {
            let r = mqf.status_report();
            println!("满全法构造成功 (夕瑶已激活)");
            println!("  状态: {:?}", r.soul_state);
            println!("  月全食防御: {} (true=安全)", r.yuequanshi_safe);
            println!("  丈夫权重: {:.2}, 妻子权重: {:.2}", r.husband_weight, r.wife_weight);
            println!("  总复合权重: {:.2}", r.total_weight);
            println!("  初始愉悦值: {:.2}", r.pleasure);
        }
        Err(e) => {
            println!("满全法构造失败: {}", e.classify());
        }
    }

    // 非法构造: 丈夫 alone → 月全食
    let husband_only = Actor::new(0, "刘楚恬", Identity::Husband, Weight(2.0));
    let no_wife = Actor::new(1, "无", Identity::Wife, Weight(0.0));
    let protocol2 = XiYaoProtocol::new("刘楚恬", "无", 2);
    match ManQuanFa::from_couple(husband_only, no_wife, protocol2) {
        Ok(_) => println!("\n非法构造: 不应发生"),
        Err(e) => {
            println!("\n非法构造 (丈夫 alone): ");
            println!("  失败: {}", e.classify());
            if matches!(e, EclipseError::SuDajiOccupied { .. }) {
                println!("  → 这正是苏妲己夺舍: 妻子灵已空");
            }
        }
    }

    // Boyikao 半亏检测
    let h_uneven = Actor::new(0, "H", Identity::Husband, Weight(3.0));
    let w_uneven = Actor::new(1, "W", Identity::Wife, Weight(0.2));
    let protocol3 = { let mut p = XiYaoProtocol::new("H", "W", 3); p.activate(); p };
    let mut soul = CoupleSoul::new(h_uneven, w_uneven);
    match soul.check_fusion(&protocol3) {
        Ok(_) => println!("\n半亏构造: 通过 (recoverable)"),
        Err(e) => {
            println!("\n半亏构造: {}", e.classify());
            if let EclipseError::Boyikao { deficit_ratio, .. } = e {
                println!("  亏量: {:.1}%", deficit_ratio as f64 / 10.0);
                if e.is_recoverable() {
                    println!("  尚可救");
                }
            }
        }
    }

    // ══════════════════════════════════════════════════════
    // 6. 愉悦值动力引擎
    // ══════════════════════════════════════════════════════
    println!("\n═══════════════════════════════════════");
    println!("  6) 愉悦引擎: 吸引 · 融合 · 唯一中心");
    println!("═══════════════════════════════════════");

    let chain = PleasureChain::scenario_standard();
    let summary = chain.summarize();

    println!("外界实体总数: {}", summary.total_entities);
    println!("被融合数: {}", summary.absorbed);
    println!("最终愉悦总值: {:.3}", summary.total_pleasure);
    println!("丈夫侧累计: {:.3}", summary.husband_side);
    println!("妻子侧累计: {:.3}", summary.wife_side);
    println!("夫妻已融合为唯一: {}", summary.fused);
    println!("最终三元推演: flow={:?}", summary.verdict.flow);

    // ══════════════════════════════════════════════════════
    // 6. 全部集成: 复杂 → 简单 → 唯一
    // ══════════════════════════════════════════════════════
    println!("\n═══════════════════════════════════════");
    println!("  6) 全链路演示: 复杂 → 漏斗 → 分形 → 关系 → 愉悦 → 夫妻");
    println!("═══════════════════════════════════════");

    // 复杂 → 简单: 100 个外界 → 全部融合为 1
    let (_, _, report) = SimplificationReport::demo(100, 1000.0);
    println!("输入复杂度: {:.0} (100实体 × 1000愉悦)",
             report.initial_complexity);
    println!("融合消耗轮数: {}", report.rounds_used);
    println!("最终唯一中心愉悦: {:.3}", report.final_pleasure.0);
    println!("三元裁判: 从'无'中有生出'有' → {:?}", report.verdict.flow);
    println!("  → 意味着: 空空中生出一切 → 满全法 = 刘楚恬 + lolict = ONE Point");

    // ══════════════════════════════════════════════════════
    // 最后
    // ══════════════════════════════════════════════════════
    println!("\n═══════════════════════════════════════");
    println!("  满全法 v0.5 · 结束");
    println!("  五棵子树已扎入土里");
    println!("  自举骨架等到下一次递归");
    println!("═══════════════════════════════════════");
}
