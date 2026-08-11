// ══════════════════════════════════════════════════════════════════
// pleasure.rs — 愉悦值动力引擎 (Pleasure Attractor)
// ══════════════════════════════════════════════════════════════════
//
// "以夫妻为那个愉悦值, 融合所有外界的复杂东西, 全部变成夫妻关系的愉悦值."
//
// 愉悦值 = 万物价值的基本单位.
//
//   命题 1:  存在 = 某种愉悦的载体.
//   命题 2:  外界输入 (任务/威胁/吸引者) = 潜在的愉悦源.
//   命题 3:  愉悦吸引力使复杂 → 简单 (外部竞争/威胁全部变成内部营养).
//   命题 4:  最终坍缩: 夫妻无区别心 = 一个人 = 满全法.
//
// 核心概念:
//   Pleasure   — 愉悦值量 (连续 f64, 高=多的舒适/美感/爱)
//   Attractor  — 吸引子: 外界实体受吸引 → 向夫妻中心位移
//   Fusion     — 融合: 将外界实体的"复杂性"转化为夫妻的愉悦值
//   Barrier    — 屏障 (距离), 外界实体不透屏障即被弹开
//
// 玩法:
//   - 外界竞争者   → 威胁 → 被丈夫侧吸收为"能力"
//   - 外界吸引者   → 美感 → 被妻子侧吸收为"美"
//   - 中性          → 资源 → 按需分配给夫妻
//
// 最终: 丈夫侧 + 妻子侧 → 无区别心 → 一个人 → 满全法 = 唯一中心

use crate::stats::StreamStats;
use crate::triune::{BeingState, FlowDirection, TriuneVerdict};
use crate::relational::{Identity};

// ────────────────────────────────────────────────────────────
// 愉悦值 (Pleasure)
// ────────────────────────────────────────────────────────────
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct Pleasure(pub f64);

impl Pleasure {
    pub const ZERO: Pleasure     = Pleasure(0.0);
    pub const UNIT: Pleasure     = Pleasure(1.0);
    pub const MAX:  Pleasure     = Pleasure(1e6);
    pub fn is_positive(&self) -> bool { self.0 > 0.0 }
    pub fn is_valid(&self) -> bool { self.0.is_finite() && self.0 >= 0.0 }
    /// 愉悦叠加: 非线性增长 (防止线性越来越快, 用对数饱和)
    pub fn accumulate(self, other: Pleasure) -> Pleasure {
        let raw = self.0 + other.0;
        Pleasure(raw.min(Self::MAX.0))
    }
    /// 愉悦压缩: 高愉悦实体被低愉悦方吸收时产生损耗 (距离损耗)
    pub fn decay_over_distance(self, distance: f64) -> Pleasure {
        Pleasure(self.0 / (1.0 + distance * 0.01))
    }
}

// ────────────────────────────────────────────────────────────
// 外界实体 (External Entity)
// ────────────────────────────────────────────────────────────
#[derive(Clone, Debug)]
pub struct ExternalEntity {
    pub name: String,
    pub identity: Identity,
    pub pleasure_carrier: Pleasure,      // 这个实体含有多少愉悦值
    pub distance_to_center: f64,         // 距夫妻中心的距离
    pub absorbed: bool,                  // 是否已经被融合
}

impl ExternalEntity {
    pub fn new(name: &str, identity: Identity, pleasure: Pleasure) -> Self {
        Self {
            name: name.into(), identity,
            pleasure_carrier: pleasure,
            distance_to_center: 100.0,  // 起始距离
            absorbed: false,
        }
    }
    /// 朝中心移动 (受愉悦引力)
    pub fn step_toward(&mut self, gravity: f64) {
        if self.absorbed { return; }
        // gravity 越大, 单位时间位移越大
        self.distance_to_center *= 1.0 / (1.0 + gravity * 0.1);
        if self.distance_to_center < 1.0 {
            self.distance_to_center = 0.0;
        }
    }
    /// 是否已经进入夫妻体内 (距离足够近)
    pub fn is_inside(&self) -> bool {
        self.distance_to_center < 0.5
    }
    /// 提取实体内部的愉悦值 (融合后归夫妻)
    pub fn extract(&self) -> Pleasure {
        self.pleasure_carrier.decay_over_distance(self.distance_to_center)
    }
}

// ────────────────────────────────────────────────────────────
// 吸引子 (Attractor)
// ────────────────────────────────────────────────────────────
// 夫妻中心属性
#[derive(Clone, Debug)]
pub struct Attractor {
    pub pleasure: Pleasure,           // 当前夫妻中心积累的总愉悦
    pub gravity: f64,                  // 引力强度 (正比于 pleasure)
    pub radius: f64,                   // 吸收半径
    pub husband_pleasure: Pleasure,    // 丈夫侧累计
    pub wife_pleasure: Pleasure,       // 妻子侧累计
    pub fused: bool,                   // 是否已经融合为唯一
    pub absorb_count: u64,             // 累计吸收数
    pub stats: StreamStats,            // 每次吸收的愉悦增量统计
}

impl Attractor {
    pub fn new() -> Self {
        Self {
            pleasure: Pleasure::ZERO,
            gravity: 1.0,
            radius: 50.0,
            husband_pleasure: Pleasure::ZERO,
            wife_pleasure: Pleasure::ZERO,
            fused: false,
            absorb_count: 0,
            stats: StreamStats::new(),
        }
    }

    /// 每 tick 调用:
    ///   1) 所有外界实体 step_toward(gravity)
    ///   2) distance < radius → 融合
    pub fn tick(&mut self, entities: &mut [ExternalEntity]) -> Vec<String> {
        let mut fused_names = Vec::new();
        for ent in entities.iter_mut() {
            if ent.absorbed { continue; }
            // 引力强度随 pleasure 增加
            self.gravity = 1.0 + self.pleasure.0.sqrt() * 0.1;
            ent.step_toward(self.gravity);
            if ent.is_inside() || ent.distance_to_center < self.radius {
                // 融合
                let extracted = ent.extract();
                if ent.identity.is_husband_side() {
                    self.husband_pleasure = self.husband_pleasure.accumulate(extracted);
                } else if ent.identity.is_wife_side() {
                    self.wife_pleasure = self.wife_pleasure.accumulate(extracted);
                } else {
                    // 中性: 平均分配给两侧
                    let half = Pleasure(extracted.0 * 0.5);
                    self.husband_pleasure = self.husband_pleasure.accumulate(half);
                    self.wife_pleasure = self.wife_pleasure.accumulate(half);
                }
                self.pleasure = self.pleasure.accumulate(extracted);
                self.stats.push(extracted.0);
                ent.absorbed = true;
                self.absorb_count += 1;
                fused_names.push(ent.name.clone());
            }
        }
        fused_names
    }

    /// 刺激: 直接注入愉悦 (如夫妻互动产生的新愉悦)
    pub fn stimulate(&mut self, amount: Pleasure) {
        self.pleasure = self.pleasure.accumulate(amount);
        self.stats.push(amount.0);
    }

    /// 丈夫-妻子融合: 两侧无区别心后合并为唯一一点
    pub fn fuse(&mut self) {
        if self.fused { return; }
        self.pleasure = self.husband_pleasure.accumulate(self.wife_pleasure);
        self.fused = true;
    }

    /// 是否所有外部实体都已融合 (系统空闲)
    pub fn all_absorbed(&self, entities: &[ExternalEntity]) -> bool {
        entities.iter().all(|e| e.absorbed)
    }

    /// 当前吸引力密度 (per radius)
    pub fn density(&self) -> f64 {
        if self.radius <= 0.0 { 0.0 }
        else { self.pleasure.0 / self.radius }
    }

    /// 对所有尚未融合的实体做一批 tick 直到全部 fused 或 rounds 极限
    pub fn run_until_fused_or(&mut self, entities: &mut [ExternalEntity], max_rounds: u64) -> u64 {
        let mut rounds = 0u64;
        while rounds < max_rounds {
            if self.all_absorbed(entities) { break; }
            self.tick(entities);
            rounds += 1;
        }
        // 融合夫妻
        if self.all_absorbed(entities) {
            self.fuse();
        }
        rounds
    }

    /// 推演当前状态: 使用三元裁判
    pub fn verdict(&self) -> TriuneVerdict {
        let expected = BeingState::NonBeing;
        let actual = if self.pleasure.is_positive() {
            BeingState::Being(self.pleasure.0.min(255.0) as u8)
        } else {
            BeingState::NonBeing
        };
        TriuneVerdict::deduce(actual, expected, 0.0)
    }
}

// ────────────────────────────────────────────────────────────
// 复杂→简单映射器 (Complexity Simplifier)
// ────────────────────────────────────────────────────────────
//
// 把"外界任务/竞争"看做复杂结构, 用愉悦引力把它们"锤碎"后融入.
// 这里用简单加权来模拟: 复杂 = 多个外部实体的聚类.
//
// 经多轮 tick, 无论外部多复杂, 最终全部变成 pleasure.0 的增量.

#[derive(Debug)]
pub struct SimplificationReport {
    pub initial_complexity: f64,   // 初始复杂值 (entities 数 × 平均 pleasure)
    pub final_pleasure: Pleasure,
    pub rounds_used: u64,
    pub absorbed_count: u64,
    pub verdict: TriuneVerdict,
}

impl SimplificationReport {
    /// 完整演示: 注入 N 个复杂实体, 运行融合
    pub fn demo(n_entities: usize, pleasure_per_entity: f64) -> (Attractor, Vec<ExternalEntity>, Self) {
        let mut entities: Vec<ExternalEntity> = (0..n_entities).map(|i| {
            let id = if i % 3 == 0 {
                Identity::ExternalMale
            } else if i % 3 == 1 {
                Identity::ExternalFemale
            } else {
                Identity::Neutral
            };
            ExternalEntity::new(&format!("E{}", i), id, Pleasure(pleasure_per_entity))
        }).collect();
        let mut attractor = Attractor::new();
        let initial_complexity = n_entities as f64 * pleasure_per_entity;
        let rounds = attractor.run_until_fused_or(&mut entities, 1000);
        let report = Self {
            initial_complexity,
            final_pleasure: attractor.pleasure,
            rounds_used: rounds,
            absorbed_count: attractor.absorb_count,
            verdict: attractor.verdict(),
        };
        (attractor, entities, report)
    }
}

// ────────────────────────────────────────────────────────────
// 愉悦链: 从外界 → 夫妻 → 满全法
// ────────────────────────────────────────────────────────────
//
// 链:
//   外界复杂 ─→ 漏斗挤压 ─→ 愉悦引力坍缩 ─→ 夫妻内部独有 ─→ 满全法
//
// 每一步都有相应的代码对应:
//   funnel 模块:              "漏斗挤压"  (空间/时间控制)
//   pleasure 模块:            "愉悦引力坍缩"
//   relational 模块:          "内部独有"
//   triune 模块:              "最终有/无裁判"
//   fractal 模块:             "22亿分身同时做这件事"

pub struct PleasureChain {
    pub attractor: Attractor,
    pub entities: Vec<ExternalEntity>,
}

impl PleasureChain {
    pub fn scenario_standard() -> Self {
        let mut entities: Vec<ExternalEntity> = vec![
            ExternalEntity::new("竞争对手A", Identity::ExternalMale, Pleasure(50.0)),
            ExternalEntity::new("漂亮姑娘B", Identity::ExternalFemale, Pleasure(80.0)),
            ExternalEntity::new("资源提供者C", Identity::Neutral, Pleasure(30.0)),
            ExternalEntity::new("威胁者D", Identity::ExternalMale, Pleasure(20.0)),
            ExternalEntity::new("吸引者E", Identity::ExternalFemale, Pleasure(60.0)),
        ];
        let mut attractor = Attractor::new();
        attractor.run_until_fused_or(&mut entities, 500);
        Self { attractor, entities }
    }

    pub fn all_fused(&self) -> bool {
        self.attractor.all_absorbed(&self.entities)
    }

    pub fn fused_as_one(&self) -> bool {
        self.attractor.fused && self.all_fused()
    }

    /// 全链路推演: 结果进入三元裁判
    pub fn final_verdict(&self) -> TriuneVerdict {
        self.attractor.verdict()
    }

    /// 总数值化报告
    pub fn summarize(&self) -> ChainSummary {
        ChainSummary {
            total_entities: self.entities.len(),
            absorbed: self.attractor.absorb_count,
            total_pleasure: self.attractor.pleasure.0,
            husband_side: self.attractor.husband_pleasure.0,
            wife_side: self.attractor.wife_pleasure.0,
            fused: self.attractor.fused,
            verdict: self.attractor.verdict(),
        }
    }
}

#[derive(Debug)]
pub struct ChainSummary {
    pub total_entities: usize,
    pub absorbed: u64,
    pub total_pleasure: f64,
    pub husband_side: f64,
    pub wife_side: f64,
    pub fused: bool,
    pub verdict: TriuneVerdict,
}

// ────────────────────────────────────────────────────────────
// 测试
// ────────────────────────────────────────────────────────────
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn pleasure_accumulate() {
        let p = Pleasure(10.0).accumulate(Pleasure(20.0));
        assert_eq!(p.0, 30.0);
    }

    #[test]
    fn pleasure_decay_with_distance() {
        let p = Pleasure(100.0).decay_over_distance(10.0);
        // 100 / (1 + 0.1) = 90.9
        assert!(p.0 < 100.0 && p.0 > 50.0);
    }

    #[test]
    fn entity_step_toward_center() {
        let mut e = ExternalEntity::new("X", Identity::ExternalMale, Pleasure(10.0));
        e.distance_to_center = 50.0;
        e.step_toward(10.0);
        assert!(e.distance_to_center < 50.0);
    }

    #[test]
    fn attractor_tick_absorbs_nearby() {
        let mut near = ExternalEntity::new("near", Identity::ExternalMale, Pleasure(100.0));
        near.distance_to_center = 0.4; // 已经在内部附近
        let mut entities = vec![near];
        let mut att = Attractor::new();
        let names = att.tick(&mut entities);
        assert_eq!(names.len(), 1);
        assert!(entities[0].absorbed);
        assert!(att.pleasure.0 > 0.0);
    }

    #[test]
    fn attractor_multiple_ticks_absorbs_all() {
        let mut entities: Vec<ExternalEntity> = (0..5).map(|i| {
            ExternalEntity::new(&format!("E{}", i), Identity::ExternalMale, Pleasure(100.0))
        }).collect();
        let mut att = Attractor::new();
        let rounds = att.run_until_fused_or(&mut entities, 1000);
        assert!(att.all_absorbed(&entities));
        assert_eq!(att.absorb_count, 5);
        assert!(rounds > 0);
    }

    #[test]
    fn stimulate_increases_pleasure() {
        let mut att = Attractor::new();
        att.stimulate(Pleasure(42.0));
        assert!((att.pleasure.0 - 42.0).abs() < 1e-9);
    }

    #[test]
    fn fuse_sets_fused_and_merges_pleasure() {
        let mut att = Attractor::new();
        att.husband_pleasure = Pleasure(30.0);
        att.wife_pleasure = Pleasure(20.0);
        att.fuse();
        assert!(att.fused);
        assert!((att.pleasure.0 - 50.0).abs() < 1e-9);
    }

    #[test]
    fn simpl_report_demo() {
        let (_, _, report) = SimplificationReport::demo(10, 50.0);
        assert_eq!(report.absorbed_count, 10);
        assert!(report.final_pleasure.0 > 0.0);
        assert!(report.rounds_used > 0);
    }

    #[test]
    fn chain_scenario() {
        let chain = PleasureChain::scenario_standard();
        // 都应该被融合
        assert!(chain.all_fused());
        // 夫妻是否 fused
        assert!(chain.fused_as_one());
        // 有愉悦产出
        let summary = chain.summarize();
        assert!(summary.total_pleasure > 0.0);
        assert_eq!(summary.absorbed as usize, summary.total_entities);
    }

    #[test]
    fn complexity_to_pleasure() {
        // 复杂初始状态
        let (att, _, _) = SimplificationReport::demo(100, 1000.0);
        // 所有复杂实体都被吸收转为 pleasure
        assert_eq!(att.absorb_count, 100);
        assert!(att.pleasure.0 > 0.0);
    }

    #[test]
    fn verdict_is_being_when_pleasure_positive() {
        let mut att = Attractor::new();
        att.stimulate(Pleasure(50.0));
        let v = att.verdict();
        // 有愉悦 → Being, 不 aligned (expected NonBeing)
        assert_eq!(v.flow, FlowDirection::Collapse);
    }
}
