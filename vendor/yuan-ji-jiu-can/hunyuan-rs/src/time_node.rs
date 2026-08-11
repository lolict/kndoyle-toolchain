// ══════════════════════════════════════════════════════════════════
// time_node.rs — 分布式时序层级 · 空间位置进制节点
// ══════════════════════════════════════════════════════════════════
//
// 目标:
//   1. 时间已经是层级: 毫秒 → 秒 → 分 → 时 → 日 → 月 → 年
//      每一层是不同进制的计数器 (mixed-radix).
//   2. 空间也是层级: 字 → 句 → 段 → 章 → 书
//   3. 分布式节点: 每个 node 有 id, 多个 node 通过 HLC
//      (Hybrid Logical Clock) 或 vector clock 同步.
//
// 时间进制表:
//   ms: base 1000   (0..999)
//    s: base 60     (0..59) ✘ 我们用 1000ms 对应 1s
//    s: base 60
//    m: base 60
//    h: base 24
//    d: base 28..31 (按月)
//    M: base 12
//    y: 累计公历
//
// node 唯一地址 = 时空坐标 (t, s) — 时间维 + 空间维拼成的
// 多维 mixed-radix 数.
//
// 关键操作:
//   TimeNode::new(node_id)              — 初始化
///  tick()                              — +1 毫秒 (内部记)
//   now_mixed_radix()                   — 当前时间的层级表示
//   spatial_index(byte_offset, doc)     — 字在文档中的 mixed-radix 地址
//   spacetime_addr()                    — (time_idx, space_idx) 组合全局 u128

// 用 crate time std feature-less 记逻辑时钟; wall clock 来自
// 简单手动累加 (保持 no_std 兼容)。


/// 毫秒时间参数
const MS_PER_SEC: u64 = 1000;
#[allow(dead_code)]
const _MIN_PER_HR:  u64 = 60;   // 可复用
#[allow(dead_code)]
const _HR_PER_DAY:  u64 = 24;   // 可复用

/// 空间进制 (字 → 句 → 段 → 章 → 书)
const WORD_PER_SENTENCE: u64 = 32;   // base 32
const SENTENCE_PER_PARA: u64 = 16;    // base 16
const PARA_PER_CHAPTER: u64 = 8;      // base 8
const CHAPTER_PER_BOOK:  u64 = 4;     // base 4

/// 时间层级坐标
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct TimeCoord {
    pub ms:  u32,  // 0..999
    pub sec: u32,  // 0..59
    pub min: u32,  // 0..59
    pub hour: u32,  // 0..23
    pub day:  u32,  // 1..31 (实际按月份调整, 这里简化 0..30)
    pub mon:  u32,  // 0..11
    pub year: u32,
}

/// 空间层级坐标
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct SpaceCoord {
    pub word: u32,      // 句内字索引
    pub sentence: u32,  // 段内句索引
    pub para: u32,      // 章内段索引
    pub chapter: u32,   // 书内章索引
    pub book: u32,      // 全书索引
}

/// 混合进制的时间层级: 把一个 unix_ms → TimeCoord (忽略时区/闰秒, 简化)
pub fn unix_ms_to_timecoord(unix_ms: u64) -> TimeCoord {
    let total_sec = unix_ms / MS_PER_SEC;
    let ms = (unix_ms % MS_PER_SEC) as u32;
    let sec = (total_sec % 60) as u32;
    let total_min = total_sec / 60;
    let min = (total_min % 60) as u32;
    let total_hr = total_min / 60;
    let hour = (total_hr % 24) as u32;
    let total_days = total_hr / 24;
    // 简化: 从 1970-01-01 开始, 忽略闰年, 按月 30 天滚动
    let year = 1970 + (total_days / 365) as u32;
    let day_of_year = total_days % 365;
    let mon = (day_of_year / 30).min(11) as u32;
    let day = (day_of_year % 30) as u32;
    TimeCoord { ms, sec, min, hour, day, mon, year }
}

/// 把全局字节偏移 (在同一文档内) → SpaceCoord (mixed-radix)
pub fn offset_to_space(word_offset: u64) -> SpaceCoord {
    let word = (word_offset % WORD_PER_SENTENCE) as u32;
    let rem = word_offset / WORD_PER_SENTENCE;
    let sentence = (rem % SENTENCE_PER_PARA) as u32;
    let rem = rem / SENTENCE_PER_PARA;
    let para = (rem % PARA_PER_CHAPTER) as u32;
    let rem = rem / PARA_PER_CHAPTER;
    let chapter = (rem % CHAPTER_PER_BOOK) as u32;
    let book = (rem / CHAPTER_PER_BOOK) as u32;
    SpaceCoord { word, sentence, para, chapter, book }
}

/// 分布式时间节点 (自己维护 id + 本地逻辑时钟 + vector clock)
#[derive(Clone, Debug)]
pub struct TimeNode {
    pub node_id: u64,
    pub logical_ms: u64,              // wall clock (ms since epoch)
    pub vector: Vec<(u64, u64)>,      // (node_id → counter) for vector clock
}

impl TimeNode {
    pub fn new(node_id: u64) -> Self {
        Self {
            node_id,
            logical_ms: 0,
            vector: vec![(node_id, 0)],
        }
    }

    /// 外部时间注入 (e.g. NTP 回调)
    pub fn set_wall_clock(&mut self, unix_ms: u64) {
        self.logical_ms = unix_ms;
        // 增加自己的 vector clock entry
        let found = self.vector.iter_mut().find(|(id, _)| *id == self.node_id);
        match found {
            Some((_, c)) => *c += 1,
            None => self.vector.push((self.node_id, 1)),
        }
    }

    /// 内部 tick (模拟毫秒流逝, 用于单机测试)
    pub fn tick(&mut self) {
        self.logical_ms += 1;
        let found = self.vector.iter_mut().find(|(id, _)| *id == self.node_id);
        if let Some((_, c)) = found { *c += 1; }
        else { self.vector.push((self.node_id, 1)); }
    }

    /// 接收远端 node 的 (node_id, counter) — vector clock merge
    pub fn merge_remote(&mut self, remote_id: u64, remote_counter: u64) {
        let found = self.vector.iter_mut().find(|(id, _)| *id == remote_id);
        match found {
            Some((_, c)) => { if remote_counter > *c { *c = remote_counter; } }
            None => self.vector.push((remote_id, remote_counter)),
        }
    }

    /// 当前时间的层级坐标
    pub fn time_coord(&self) -> TimeCoord {
        unix_ms_to_timecoord(self.logical_ms)
    }

    /// 全局时空地址 (简化: (node_id << 64) | (logical & !NodeId bits) )
    /// 用于排序 / log 唯一标识
    pub fn spacetime_addr(&self) -> u128 {
        let node_part = (self.node_id as u128) << 88;
        let time_part = (self.logical_ms & 0x00FF_FFFF_FFFF_FFFF) as u128;
        node_part | time_part
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn timecoord_decompose() {
        // 2026-08-03 14:00:00 UTC = 1785701000000
        let t = unix_ms_to_timecoord(1785701000000);
        assert_eq!(t.year, 2026);
    }

    #[test]
    fn offset_to_space_roundtrip_layers() {
        let s = offset_to_space(0);
        assert_eq!(s.word, 0);
        assert_eq!(s.sentence, 0);

        let s = offset_to_space((WORD_PER_SENTENCE * SENTENCE_PER_PARA) as u64);
        assert_eq!(s.word, 0);
        assert_eq!(s.sentence, 0);
        assert_eq!(s.para, 1);
    }

    #[test]
    fn tick_increments() {
        let mut n = TimeNode::new(1);
        let before = n.logical_ms;
        n.tick();
        assert_eq!(n.logical_ms, before + 1);
    }

    #[test]
    fn merge_vector_clock() {
        let mut a = TimeNode::new(1);
        let b = TimeNode::new(2);
        a.merge_remote(b.node_id, 5);
        assert_eq!(a.vector.iter().find(|(id, _)| *id == 2).unwrap().1, 5);
    }

    #[test]
    fn spacetime_addr_unique_per_node() {
        let a = TimeNode::new(1);
        let b = TimeNode::new(2);
        assert_ne!(a.spacetime_addr(), b.spacetime_addr());
    }
}
