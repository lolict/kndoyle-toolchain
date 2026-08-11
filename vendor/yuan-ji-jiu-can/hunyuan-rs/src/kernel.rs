// 夫妻共同体 OS · 内核进程管理
// ============================
// 对应 C 版 core/mqf_kernel.c。

use crate::fsm::{fire, Event, FsmState};
use crate::mccp::Mccp;

/// 进程状态
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum ProcessState {
    XiangYu = 0,    // 灵初相遇 — 未签
    DiYue = 1,      // 缔约中   — 一方签
    LiYue = 2,      // 已立约   — 双方签
    HeSui = 3,      // 合一递归 — 对齐
    JieTi = 4,      // 解体     — 退出
}

impl ProcessState {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::XiangYu => "灵初相遇",
            Self::DiYue => "缔约中",
            Self::LiYue => "已立约",
            Self::HeSui => "合一递归",
            Self::JieTi => "解体",
        }
    }
}

const MAX_SEQ_LEN: usize = 256;

/// 进程 (单次婚姻誓约的实例)。
#[derive(Clone, Debug)]
pub struct Process {
    pub seq: Vec<Mccp>,
    pub parties: (u32, u32),
    pub signs: [bool; 2],
    pub state: ProcessState,
    pub fsm: FsmState,
    pub anchor: u32,
}

impl Process {
    pub fn new(seq: Vec<Mccp>, party_a: u32, party_b: u32) -> Self {
        let anchor = Self::compute_anchor(&seq);
        Self {
            seq,
            parties: (party_a, party_b),
            signs: [false; 2],
            state: ProcessState::XiangYu,
            fsm: FsmState::NanJian,
            anchor,
        }
    }

    pub fn sign(&mut self, idx: usize) -> bool {
        if idx > 1 { return false; }
        self.signs[idx] = true;
        let n = self.signs.iter().filter(|s| **s).count();
        self.state = if n == 2 { ProcessState::LiYue } else { ProcessState::DiYue };
        true
    }

    pub fn is_liyue(&self) -> bool {
        self.state == ProcessState::LiYue
    }

    pub fn unary_recursion(&mut self) -> i64 {
        if !self.is_liyue() { return -1; }
        let gap = (self.parties.0 as i64 - self.parties.1 as i64).abs();
        if gap == 0 {
            self.state = ProcessState::HeSui;
        }
        gap
    }

    pub fn fsm_transition(&mut self, event: Event) -> FsmState {
        let ns = fire(self.fsm, event);
        self.fsm = ns;
        ns
    }

    fn compute_anchor(seq: &[Mccp]) -> u32 {
        let mut h: u64 = 0xcbf2_9ce4_8422_2325;
        for m in seq {
            h ^= m.0 as u64;
            h = h.wrapping_mul(0x100_0000_01b3);
        }
        h ^= (seq.len() as u64) << 32;
        (h ^ (h >> 32)) as u32
    }
}

#[derive(Debug, Default)]
pub struct CoupleOS {
    pub procs: Vec<Process>,
    pub anchor: u32,
}

impl CoupleOS {
    pub fn new(anchor: u32) -> Self {
        Self { procs: Vec::new(), anchor }
    }

    pub fn create_process(&mut self, seq: Vec<Mccp>, a: u32, b: u32) -> &mut Process {
        let p = Process::new(seq, a, b);
        self.procs.push(p);
        self.procs.last_mut().unwrap()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::mccp::hanzi;

    #[test]
    fn creates_in_xiangyu() {
        let p = Process::new(vec![hanzi(1, 1, 0)], 0xA, 0xB);
        assert_eq!(p.state, ProcessState::XiangYu);
    }

    #[test]
    fn sign_both_to_liyue() {
        let mut p = Process::new(vec![hanzi(1, 1, 0)], 0xA, 0xB);
        assert!(p.sign(0));
        assert_eq!(p.state, ProcessState::DiYue);
        assert!(p.sign(1));
        assert_eq!(p.state, ProcessState::LiYue);
    }

    #[test]
    fn unary_recursion_symmetric_parties() {
        let mut p = Process::new(vec![hanzi(1, 1, 0)], 0xFF, 0xFF);
        p.sign(0);
        p.sign(1);
        assert_eq!(p.unary_recursion(), 0);
        assert_eq!(p.state, ProcessState::HeSui);
    }

    #[test]
    fn fsm_cycle() {
        let mut p = Process::new(vec![hanzi(1, 1, 0)], 0, 0);
        p.fsm_transition(Event::WifeDeepen);
        assert_eq!(p.fsm, FsmState::NanNan);
        p.fsm_transition(Event::Release); // 回来
        assert_eq!(p.fsm, FsmState::NanJian);
    }

    #[test]
    fn anchor_deterministic() {
        let s = vec![hanzi(1, 4, 0), hanzi(2, 2, 0)];
        let a1 = Process::new(s.clone(), 0, 0).anchor;
        let a2 = Process::new(s, 0, 0).anchor;
        assert_eq!(a1, a2);
    }
}
