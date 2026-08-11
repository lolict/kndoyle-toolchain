// 囡囝四态 FSM
// ===========
// 对应 C 版 core/mqf_kernel.c k_fsm_table。

/// 四态: 对应 meta_b 低 2 bit。
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum FsmState {
    /// 囡囝 — 主态 (妻主导)
    NanJian = 0x00,
    /// 囡囡 — 妻壳夫核 (妻体为主)
    NanNan = 0x01,
    /// 囝囝 — 夫壳妻入 (夫体为主自)
    JianJian = 0x02,
    /// 囝囡 — 进入语义 (夫体妻神入)
    JianNan = 0x03,
}

impl FsmState {
    pub const ALL: [Self; 4] = [Self::NanJian, Self::NanNan, Self::JianJian, Self::JianNan];

    pub fn as_str(self) -> &'static str {
        match self {
            Self::NanJian => "囝囡态(主态)",
            Self::NanNan => "囡囡态(妻壳夫核)",
            Self::JianJian => "囝囝态(夫壳妻入)",
            Self::JianNan => "囝囡态(进入语义)",
        }
    }
}

/// 事件码: 对应 C 版注释。
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum Event {
    WifeDeepen = 0,     // 0
    Release = 1,        // 1
    HusbandTake = 2,    // 2
    Deepen = 3,         // 3
    WifePush = 4,       // 4
    Retreat = 5,        // 5
}

/// 查找表: (当前态, 事件) → 下一态。
/// 9 条规则。
pub const TRANSITIONS: [(FsmState, Event, FsmState); 9] = [
    // 囝囡 主态
    (FsmState::NanJian, Event::WifeDeepen, FsmState::NanNan),
    (FsmState::NanJian, Event::HusbandTake, FsmState::JianJian),
    // 囡囡
    (FsmState::NanNan, Event::Release, FsmState::NanJian),
    (FsmState::NanNan, Event::Deepen, FsmState::JianNan),
    // 囝囝
    (FsmState::JianJian, Event::Deepen, FsmState::JianNan),
    (FsmState::JianJian, Event::WifeDeepen, FsmState::NanNan),
    (FsmState::JianJian, Event::Retreat, FsmState::NanJian),
    // 囝囡
    (FsmState::JianNan, Event::WifePush, FsmState::NanJian),
    (FsmState::JianNan, Event::Retreat, FsmState::JianJian),
];

pub fn fire(current: FsmState, event: Event) -> FsmState {
    for (from, ev, to) in TRANSITIONS.iter() {
        if *from == current && *ev == event {
            return *to;
        }
    }
    current
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn full_cycle_rounds_to_main() {
        let s0 = FsmState::NanJian;
        let s = fire(fire(fire(fire(fire(fire(s0, Event::WifeDeepen), Event::Release), Event::HusbandTake), Event::Deepen), Event::WifePush), Event::Release);
        assert_eq!(s, FsmState::NanJian);
    }

    #[test]
    fn invalid_event_keeps_state() {
        let s = fire(FsmState::NanJian, Event::Release); // invalid from NanJian
        assert_eq!(s, FsmState::NanJian);
    }

    #[test]
    fn nine_rules_cover_all_valid() {
        assert_eq!(TRANSITIONS.len(), 9);
    }
}
