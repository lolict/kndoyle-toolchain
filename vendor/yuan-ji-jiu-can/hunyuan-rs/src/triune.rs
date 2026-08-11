// ══════════════════════════════════════════════════════════════════
// triune.rs — 三元裁判机 (Triune Judgement Engine)
// ══════════════════════════════════════════════════════════════════
//
// 内心观测者 对 一个被观测现象 做三元推演:
//
//   维度1: 定义         — 这是"有"还是"无" (being / non-being)
//   维度2: 流动方向     — 正在"由有转无"还是"由无转有"
//   维度3: 等效对齐     — 实际与预期是否对齐 (perfect / crooked 都可)
//
// 漏斗形状也可以不完美 (歪歪的) — 只要存在"由大到小"的趋势,
// 它就是有效的漏斗. 这对应 "等效对齐 不一定完美, 但方向对"。
//
// 推演规则:
//   expected=NonBeing +  实际=Being      => 正在从无变有  (Collapse)
//   expected=  Being  +  实际=NonBeing    => 正在从有变无  (Expand)
//   expected=  Being  +  实际=Being       => 有内有  (可坍缩)
//   expected=NonBeing +  实际=NonBeing    => 无外无  (可通过)
//
// 这三元逻辑是满全法所有后续模块的基础判读单元.

// ────────────────────────────────────────────────────────────
// 有无 (Being / Non-Being)
// ────────────────────────────────────────────────────────────
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum BeingState {
    Being(u8),    // 有内容, 内部存储一个 u8 的 payload
    NonBeing,     // 无 (空位)
}

// ────────────────────────────────────────────────────────────
// 流动方向
// ────────────────────────────────────────────────────────────
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum FlowDirection {
    Collapse,     // 坍缩   — 由外向内 (辐射→中心)
    Expand,       // 辐射   — 由内向外 (中心→外)
    Static,       // 不动   — 既不坍缩也不辐射
}

// ────────────────────────────────────────────────────────────
// 三元推演结果
// ────────────────────────────────────────────────────────────
#[derive(Clone, Debug)]
pub struct TriuneVerdict {
    pub being:      BeingState,       // 实际观测到的有无
    pub flow:       FlowDirection,    // 推演出的流动方向
    pub alignment:  bool,             // 是否等效对齐
    pub confidence: f64,              // 推演置信度 0..1 (歪斜的漏斗会降低 confidence)
}

impl TriuneVerdict {
    /// 推演: 实际 + 预期 → 三元裁判结果
    pub fn deduce(actual: BeingState, expected: BeingState, crooked: f64) -> Self {
        let alignment = match (actual, expected) {
            (BeingState::Being(_), BeingState::Being(_)) => true,
            (BeingState::NonBeing, BeingState::NonBeing) => true,
            _ => false,
        };
        let flow = match (actual, expected) {
            (BeingState::Being(_), BeingState::NonBeing) => FlowDirection::Collapse,  // 凭空生出
            (BeingState::NonBeing, BeingState::Being(_)) => FlowDirection::Expand,    // 有化为无
            _ => FlowDirection::Static,
        };
        // 歪斜度越低 (crooked 近0) confidence 越高; 越歪 confidence 越低
        // 但方向对时 confidence 不会降到 0: 歪歪但有效的漏斗 still gives signal
        let confidence = if alignment {
            1.0
        } else {
            // 歪漏斗仍然可以推演, 只是置信度折半
            (1.0 - crooked).max(0.3)
        };
        TriuneVerdict { being: actual, flow, alignment, confidence }
    }
}

// ────────────────────────────────────────────────────────────
// 漏斗 (允许歪斜)
// ────────────────────────────────────────────────────────────
// 漏斗只要求 mouth > neck (由大到小),
// 歪斜不影响有效性, 只降低 confidence.
//
//   neck     neck     neck            neck
//    |        |        |               |
//    v        v        v               v
//   ╱        |  ╲    ╱   ╲          |
//  ╱         |   ╲  ╱     ╲         |      ← 歪歪的也 ok
// ╱          |    ╲       ╲         |
// ───────────────────────────────────────────── mouth

#[derive(Clone, Debug)]
pub struct Funnel {
    pub mouth:        f64,   // 开口宽度 (大)
    pub neck:         f64,   // 窄口宽度 (小)
    pub crooked:      f64,   // 歪斜度 0..1 (0=完美 1=非常歪)
    pub trend_collapsing: bool, // 是否由大到小
}

impl Funnel {
    /// 构造漏斗. assert mouth >= neck.
    pub fn new(mouth: f64, neck: f64, crooked: f64) -> Self {
        assert!(mouth >= neck, "漏斗开口必须≥窄口");
        assert!((0.0..=1.0).contains(&crooked), "歪斜度必须在 0..1");
        Self {
            mouth,
            neck,
            crooked,
            trend_collapsing: mouth > neck,
        }
    }

    /// 漏斗是否有效 (不管多歪, 只要由大到小就是有效漏斗)
    pub fn is_valid(&self) -> bool {
        self.mouth > self.neck
    }

    /// 收缩比 (mouth / neck ≥ 1). 越大收缩越剧烈.
    pub fn contraction_ratio(&self) -> f64 {
        self.mouth / self.neck.max(1e-9)
    }

    /// 漏斗吞入 width 的流, 输出被收缩后的宽度
    pub fn pass_through(&self, width: f64) -> f64 {
        width / self.contraction_ratio()
    }

    /// 漏斗吞入一组节点, 统计坍缩结果
    pub fn swallow(&self, nodes: &[BeingState]) -> CollapseResult {
        let full_count = nodes.iter()
            .filter(|n| matches!(n, BeingState::Being(_)))
            .count();
        let total = nodes.len();
        let input_density = if total == 0 { 0.0 }
                            else { full_count as f64 / total as f64 };
        // 收缩后密度上升: density_out = density_in * contraction_ratio
        let output_density = (input_density * self.contraction_ratio()).min(1.0);
        CollapseResult {
            input_total: total,
            input_full: full_count,
            output_density,
            output_count: ((total as f64) / self.contraction_ratio()).max(1.0) as usize,
            crooked: self.crooked,
            ratio: self.contraction_ratio(),
        }
    }
}

#[derive(Debug)]
pub struct CollapseResult {
    pub input_total:   usize,
    pub input_full:    usize,
    pub output_density: f64,
    pub output_count:  usize,
    pub crooked:       f64,
    pub ratio:         f64,
}

// ────────────────────────────────────────────────────────────
// 推演引擎: 组合多个节点 → 逐三元 → 判断整体坍缩方向
// ────────────────────────────────────────────────────────────

pub struct TriuneEngine {
    pub funnel: Funnel,
}

impl TriuneEngine {
    pub fn new(funnel: Funnel) -> Self {
        Self { funnel }
    }

    /// 对一组做三元推演后, 整体坍缩方向多数决
    pub fn collective_flow(&self, actuals: &[BeingState], expected: BeingState) -> FlowDirection {
        let mut collapse_cnt = 0u32;
        let mut expand_cnt = 0u32;
        for a in actuals {
            let v = TriuneVerdict::deduce(*a, expected, self.funnel.crooked);
            match v.flow {
                FlowDirection::Collapse => collapse_cnt += 1,
                FlowDirection::Expand => expand_cnt += 1,
                FlowDirection::Static => {}
            }
        }
        if collapse_cnt > expand_cnt { FlowDirection::Collapse }
        else if expand_cnt > collapse_cnt { FlowDirection::Expand }
        else { FlowDirection::Static }
    }

    /// 对一组节点整体做漏斗坍缩推演
    pub fn collapse(&self, nodes: &[BeingState]) -> (FlowDirection, f64) {
        let expected = BeingState::NonBeing;  // 预期本应无: 生出了东西就是坍缩
        let flow = self.collective_flow(nodes, expected);
        // 整体 confidence = 平均 confidence 受歪斜影响
        let avg_conf = nodes.iter()
            .map(|n| TriuneVerdict::deduce(*n, expected, self.funnel.crooked).confidence)
            .sum::<f64>() / nodes.len().max(1) as f64;
        (flow, avg_conf)
    }
}

// ────────────────────────────────────────────────────────────
// 测试
// ────────────────────────────────────────────────────────────
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn being_nonbeing_deduce() {
        let v = TriuneVerdict::deduce(BeingState::Being(42), BeingState::NonBeing, 0.0);
        assert_eq!(v.flow, FlowDirection::Collapse);
        assert!(!v.alignment);
        // 歪斜=0 时非对齐 confidence 仍然是 (1-0) = 1... 但是非对齐时公式是 (1-crooked).max(0.3)
        assert!((v.confidence - 1.0).abs() < 1e-9);
    }

    #[test]
    fn align_same_state() {
        let v = TriuneVerdict::deduce(BeingState::Being(1), BeingState::Being(1), 0.5);
        assert!(v.alignment);
        assert_eq!(v.flow, FlowDirection::Static);
    }

    #[test]
    fn crooked_reduces_confidence() {
        let a = TriuneVerdict::deduce(BeingState::Being(5), BeingState::NonBeing, 0.0).confidence;
        let b = TriuneVerdict::deduce(BeingState::Being(5), BeingState::NonBeing, 0.8).confidence;
        // 歪斜越大, 非对齐 confidence 越低
        assert!(b < a, "歪斜高 → 低 confidence");
        assert!(b >= 0.3, "有最低 floor = 0.3");
    }

    #[test]
    fn funnel_valid_even_crooked() {
        let f = Funnel::new(100.0, 1.0, 0.9); // 非常歪
        assert!(f.is_valid()); // 只要 mouth > neck 就是有效漏斗
        assert_eq!(f.contraction_ratio(), 100.0);
    }

    #[test]
    fn funnel_pass_through_shrinks() {
        let f = Funnel::new(100.0, 10.0, 0.1);
        let out = f.pass_through(50.0);
        assert!((out - 5.0).abs() < 1e-9);
    }

    #[test]
    fn funnel_swallow_density_rises() {
        let f = Funnel::new(100.0, 10.0, 0.2);
        let nodes = vec![
            BeingState::Being(1),
            BeingState::NonBeing,
            BeingState::Being(2),
            BeingState::NonBeing,
            BeingState::Being(3),
            BeingState::NonBeing,
            BeingState::Being(4),
            BeingState::NonBeing,
            BeingState::Being(5),
            BeingState::NonBeing,
        ];
        let r = f.swallow(&nodes);
        // 输入 density 0.5, ratio 10 → 输出 density 1.0 (clamp)
        assert!((r.output_density - 1.0).abs() < 1e-9);
        assert_eq!(r.input_full, 5);
    }

    #[test]
    fn collective_collapse_direction() {
        let eng = TriuneEngine::new(Funnel::new(100.0, 1.0, 0.0));
        let actuals = vec![BeingState::Being(1), BeingState::Being(2), BeingState::NonBeing];
        let (flow, conf) = eng.collapse(&actuals);
        assert_eq!(flow, FlowDirection::Collapse);
        assert!(conf > 0.0);
    }

    #[test]
    fn collective_expand_when_emptying() {
        let eng = TriuneEngine::new(Funnel::new(100.0, 1.0, 0.0));
        // 预期 Being, 实际 NonBeing → expand
        let actuals = vec![BeingState::NonBeing, BeingState::NonBeing, BeingState::Being(1)];
        let flow = eng.collective_flow(&actuals, BeingState::Being(99));
        assert_eq!(flow, FlowDirection::Expand);
    }
}
