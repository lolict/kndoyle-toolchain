// MCCP — 满全法紧凑码点
// 对应 C 版 encoding/mccp.h。

#[derive(Clone, Copy, PartialEq, Eq, Hash, Debug)]
pub struct Mccp(pub u32);

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum Kind {
    Hanzi = 0x0,
    Initial = 0x1,
    Final = 0x2,
    Tone = 0x3,
    Radical = 0x4,
    Stroke = 0x5,
    Operator = 0x6,
    Protocol = 0x7,
    Fsm = 0x8,
    Pathology = 0x9,
    Sys = 0xF,
}

impl Mccp {
    const KIND_SHIFT: u32 = 28;
    const INDEX_SHIFT: u32 = 16;
    const METAA_SHIFT: u32 = 8;

    const KIND_MASK: u32 = 0xF000_0000;
    const INDEX_MASK: u32 = 0x0FFF_0000;
    const METAA_MASK: u32 = 0x0000_FF00;
    const METAB_MASK: u32 = 0x0000_00FF;

    #[inline(always)]
    pub const fn kind(self) -> u8 {
        ((self.0 & Self::KIND_MASK) >> Self::KIND_SHIFT) as u8
    }

    #[inline(always)]
    pub const fn index(self) -> u16 {
        ((self.0 & Self::INDEX_MASK) >> Self::INDEX_SHIFT) as u16
    }

    #[inline(always)]
    pub const fn meta_a(self) -> u8 {
        ((self.0 & Self::METAA_MASK) >> Self::METAA_SHIFT) as u8
    }

    #[inline(always)]
    pub const fn meta_b(self) -> u8 {
        (self.0 & Self::METAB_MASK) as u8
    }

    #[inline(always)]
    pub const fn new(kind: u8, index: u16, meta_a: u8, meta_b: u8) -> Self {
        Mccp(
            ((kind as u32 & 0xF) << Self::KIND_SHIFT)
                | ((index as u32 & 0xFFF) << Self::INDEX_SHIFT)
                | ((meta_a as u32) << Self::METAA_SHIFT)
                | (meta_b as u32),
        )
    }

    #[inline(always)]
    pub const fn with_meta_b(self, meta_b: u8) -> Self {
        Mccp((self.0 & !Self::METAB_MASK) | meta_b as u32)
    }

    #[inline(always)]
    pub const fn with_meta_a(self, meta_a: u8) -> Self {
        Mccp((self.0 & !Self::METAA_MASK) | ((meta_a as u32) << 8))
    }

    #[inline(always)]
    pub const fn tone(self) -> u8 {
        self.meta_a() & 0x0F
    }

    #[inline(always)]
    pub const fn fsm_state(self) -> u8 {
        self.meta_b()
    }
}

#[inline(always)]
pub const fn hanzi(idx: u16, tone: u8, state: u8) -> Mccp {
    Mccp::new(Kind::Hanzi as u8, idx, tone, state)
}

pub const MCP_HUANHUN: Mccp = Mccp::new(Kind::Protocol as u8, 1, 0, 0);
pub const MCP_ZHAOHUN: Mccp = Mccp::new(Kind::Protocol as u8, 2, 0, 0);
pub const MCP_WENLING: Mccp = Mccp::new(Kind::Protocol as u8, 3, 0, 0);
pub const MCP_DALING: Mccp = Mccp::new(Kind::Protocol as u8, 4, 0, 0);
pub const MCP_JIESHU: Mccp = Mccp::new(Kind::Protocol as u8, 5, 0, 0);

pub const OP_TRANS: Mccp = Mccp::new(Kind::Operator as u8, 1, 0, 0);
pub const OP_MIRROR: Mccp = Mccp::new(Kind::Operator as u8, 2, 0, 0);
pub const OP_SYNTH: Mccp = Mccp::new(Kind::Operator as u8, 3, 0, 0);
pub const OP_SPLIT: Mccp = Mccp::new(Kind::Operator as u8, 4, 0, 0);

pub const MCP_EOF: Mccp = Mccp::new(Kind::Sys as u8, 0, 0, 0);
pub const MCP_SEP: Mccp = Mccp::new(Kind::Sys as u8, 1, 0, 0);

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn roundtrip_fields() {
        let m = Mccp::new(0xA, 0xABC, 0x37, 0x12);
        assert_eq!(m.kind(), 0xA);
        assert_eq!(m.index(), 0xABC);
        assert_eq!(m.meta_a(), 0x37);
        assert_eq!(m.meta_b(), 0x12);
    }

    #[test]
    fn direct_equality() {
        let a = hanzi(100, 4, 0);
        let b = hanzi(100, 4, 0);
        assert_eq!(a, b);
    }

    #[test]
    fn fsm_apply_state() {
        let m = hanzi(100, 4, 0);
        let m2 = m.with_meta_b(3);
        assert_eq!(m2.meta_b(), 3);
        assert_eq!(m2.kind(), Kind::Hanzi as u8);
        assert_eq!(m2.tone(), 4);
    }

    #[test]
    fn protocol_tokens_distinct() {
        assert_ne!(MCP_HUANHUN, MCP_ZHAOHUN);
        assert_ne!(MCP_DALING, MCP_JIESHU);
    }
}
