// ══════════════════════════════════════════════════════════════════
// router.rs — 八字 / 九字 / 十六字 分析器
// ══════════════════════════════════════════════════════════════════
//
// 八字: 年柱 + 月柱 + 日柱 + 时柱, 每柱 [天干, 地支] = 8 字
// 九字: 八字 + 姓名笔画根 (把姓名笔画总数取 60 甲子余数)
// 十六字: 八字完整展开 + 姓名声母/韵母/声调 + 生肖 + 纳音
//
// 天干 10: 甲乙丙丁戊己庚辛壬癸
// 地支 12: 子丑寅卯辰巳午未申酉戌亥
// 甲子 60: 10 与 12 的最小公倍数，阳干配阳支配阴干配阴支
//
// 输出: 每柱转为 MCCP 编码的 "sentence frame", 远端可用
// holo_3d 解码回音韵学空间.
//
// 外部仅依赖 crypto::sha256 (确定性 hash) + name_creator

use crate::name_creator::char_to_dragon;
use crate::holo_3d::Coord3;

/// 天干
pub const HEAVENLY_STEMS: &[&str] = &[
    "甲", "乙", "丙", "丁", "戊", "己", "庚", "辛", "壬", "癸",
];

/// 地支
pub const EARTHLY_BRANCHES: &[&str] = &[
    "子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥",
];

/// 生肖
pub const ZODIAC: &[&str] = &[
    "鼠", "牛", "虎", "兔", "龙", "蛇", "马", "羊", "猴", "鸡", "狗", "猪",
];

/// 纳音五行 (六十甲子纳音, 仅列摘要)
const NA_YIN_SUMMARY: &[&str] = &[
    "海中金", "炉中火", "大林木", "路旁土", "剑锋金", "山头火",
    "涧下水", "城头土", "白腊金", "杨柳木", "泉中水", "屋上土",
    "霹雳火", "松柏木", "长流水", "砂石金", "山下火", "平地木",
    "壁上土", "金箔金", "覆灯火", "天河水", "大驿土", "钗钏金",
    "桑柘木", "大溪水", "沙中土", "天上火", "石榴木", "大海水",
];

/// 八字一柱
#[derive(Clone, Debug)]
pub struct Pillar {
    pub stem:  u8,   // 0..9  天干索引
    pub branch: u8,  // 0..11 地支索引
}

impl Pillar {
    #[inline]
    pub fn stem_name(&self)  -> &'static str { HEAVENLY_STEMS[self.stem as usize] }
    #[inline]
    pub fn branch_name(&self) -> &'static str { EARTHLY_BRANCHES[self.branch as usize] }
    #[inline]
    pub fn sexagenary_index(&self) -> u8 {
        // 甲子编号: stem ≡ branch (mod 2), stem = idx%10, branch = idx%12
        let mut idx = self.stem;
        while idx % 12 != self.branch as u8 { idx += 10; }
        idx % 60
    }
}

/// 八字 (四柱)
#[derive(Clone, Debug)]
pub struct BaZi {
    pub year:  Pillar,
    pub month: Pillar,
    pub day:   Pillar,
    pub hour:  Pillar,
}

impl BaZi {
    /// 推算命宫甲子 idx: (年干 + 月支 + 日干 + 时支) % 60 简化
    pub fn destiny_index(&self) -> u8 {
        ((self.year.stem + self.month.branch + self.day.stem + self.hour.branch) % 60) as u8
    }
}

/// 简化公历 → 八字 (基于 1900-01-01 基准推算, 近似)
pub fn gregorian_to_bazi(year: u32, month: u8, day: u8, hour: u8) -> BaZi {
    // 以 1900-01-31 (甲子年正月初一) 为基准
    // 天干 10 周期, 地支 12 周期
    let offset_years = year as i64 - 1900;
    let stem_year  = ((offset_years + 6) % 10) as u8;   // 1900 = 庚子 → 6
    let branch_year = ((offset_years + 10) % 12) as u8;  // 1900 = 子 → 10 (mod12=10)

    // 月: 正月建寅, 地支 = (month+1)%12
    let branch_month = ((month as u8 + 1) % 12) as u8;
    // 月干 = (年干 * 2 + 月支) % 10 (五虎遁)
    let stem_month = ((stem_year * 2 + branch_month as u8) % 10) as u8;

    // 日: 用儒略日简化 (仅近似)
    let jd_approx = (year as i64 - 1900) * 365 + (month as i64 - 1) * 30 + day as i64;
    let stem_day = ((jd_approx + 10) % 10) as u8;
    let branch_day = ((jd_approx + 4) % 12) as u8;

    // 时: 时辰 (23-1 子, 1-3 丑, …)
    let branch_hour = ((hour + 1) / 2 % 12) as u8;
    // 时干 = (日干 * 2 + 时支) % 10 (五鼠遁)
    let stem_hour = ((stem_day * 2 + branch_hour as u8) % 10) as u8;

    BaZi {
        year:  Pillar { stem: stem_year, branch: branch_year },
        month: Pillar { stem: stem_month, branch: branch_month },
        day:   Pillar { stem: stem_day, branch: branch_day },
        hour:  Pillar { stem: stem_hour, branch: branch_hour },
    }
}

/// 九字 = 八字 + 姓名笔画根 (笔画总数 % 60)
pub fn bazi_plus_name(bazi: &BaZi, full_name: &str) -> Vec<u8> {
    let mut strokes: u64 = 0;
    for c in full_name.chars() {
        strokes += (char_to_dragon(c).stroke() as u64) * 7
                + (c as u64 % 13 + 5);
    }
    let root = (strokes % 60) as u8;
    let mut out = Vec::with_capacity(9);
    out.push(bazi.year.stem); out.push(bazi.year.branch);
    out.push(bazi.month.stem); out.push(bazi.month.branch);
    out.push(bazi.day.stem); out.push(bazi.day.branch);
    out.push(bazi.hour.stem); out.push(bazi.hour.branch);
    out.push(root);
    out
}

/// 十六字 = 八字 + 姓名声韵调三柱 + 生肖 + 纳音
pub fn bazi_16(bazi: &BaZi, full_name: &str) -> Vec<u8> {
    let mut out = Vec::with_capacity(16);
    out.push(bazi.year.stem); out.push(bazi.year.branch);
    out.push(bazi.month.stem); out.push(bazi.month.branch);
    out.push(bazi.day.stem); out.push(bazi.day.branch);
    out.push(bazi.hour.stem); out.push(bazi.hour.branch);
    // 姓名声韵调三柱
    let mut init_sum = 0u8;
    let mut final_sum = 0u8;
    let mut tone_sum = 0u8;
    for c in full_name.chars() {
        let d = char_to_dragon(c);
        init_sum = init_sum.wrapping_add(d.initial());
        final_sum = final_sum.wrapping_add(d.final_());
        tone_sum = tone_sum.wrapping_add(d.tone());
    }
    out.push(init_sum % 24);
    out.push(final_sum % 39);
    out.push(tone_sum % 5);
    // 生肖 = 年支 → zodiac
    out.push(bazi.year.branch);
    // 纳音 = 日柱甲子号 → na_yin
    let na_yin_idx = bazi.day.sexagenary_index() as usize % NA_YIN_SUMMARY.len();
    out.push(na_yin_idx as u8);
    // 月令 (月支) + 时辰
    out.push(bazi.month.branch);
    out.push(bazi.hour.branch);
    // 天根 = (年干 ^ 日干 ^ 月支 ^ 时支) & 0xF 作为校验
    out.push((bazi.year.stem ^ bazi.day.stem ^ bazi.month.branch ^ bazi.hour.branch) & 0xF);
    out
}

/// 把八字编码为 3D 音韵空间坐标序列 (4 柱 × 3 维 = 12 个 u32)
pub fn bazi_to_coords(bazi: &BaZi) -> Vec<Coord3> {
    vec![
        Coord3 { x: bazi.year.stem as u32, y: bazi.year.branch as u32, z: 0 },
        Coord3 { x: bazi.month.stem as u32, y: bazi.month.branch as u32, z: 1 },
        Coord3 { x: bazi.day.stem as u32, y: bazi.day.branch as u32, z: 2 },
        Coord3 { x: bazi.hour.stem as u32, y: bazi.hour.branch as u32, z: 3 },
    ]
}

/// 八字句: "年柱 月柱 日柱 时柱" 八字并列
pub fn bazi_to_hex_str(bazi: &BaZi) -> String {
    format!(
        "{}{}{}{}{}{}{}{}",
        bazi.year.stem_name(), bazi.year.branch_name(),
        bazi.month.stem_name(), bazi.month.branch_name(),
        bazi.day.stem_name(), bazi.day.branch_name(),
        bazi.hour.stem_name(), bazi.hour.branch_name(),
    )
}

/// 断言子: 干支配偶 (阳干配阳支, 阴干配阴支)
pub fn is_valid_pillar(p: &Pillar) -> bool {
    (p.stem % 2) == (p.branch % 2)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn sexagenary_cycle() {
        // 甲子: 0,0 → idx 0; 乙丑: 1,1 → idx 1
        assert_eq!(Pillar { stem: 0, branch: 0 }.sexagenary_index(), 0);
        assert_eq!(Pillar { stem: 1, branch: 1 }.sexagenary_index(), 1);
    }

    #[test]
    fn bazi_invariants() {
        let b = gregorian_to_bazi(2026, 8, 3, 14);
        assert!(b.year.stem < 10 && b.year.branch < 12);
        assert!(b.month.stem < 10 && b.month.branch < 12);
        assert!(b.day.stem < 10 && b.day.branch < 12);
        assert!(b.hour.stem < 10 && b.hour.branch < 12);
    }

    #[test]
    fn valid_pillars() {
        let b = gregorian_to_bazi(2000, 1, 1, 12);
        assert!(is_valid_pillar(&b.year));
        assert!(is_valid_pillar(&b.month));
        assert!(is_valid_pillar(&b.day));
        assert!(is_valid_pillar(&b.hour));
    }

    #[test]
    fn nine_chars_len() {
        let b = gregorian_to_bazi(1996, 3, 15, 10);
        let n = bazi_plus_name(&b, "刘楚恬");
        assert_eq!(n.len(), 9);
    }

    #[test]
    fn sixteen_chars_len() {
        let b = gregorian_to_bazi(1996, 3, 15, 10);
        let n = bazi_16(&b, "刘楚恬");
        assert_eq!(n.len(), 16);
    }

    #[test]
    fn bazi_hex_string() {
        let b = gregorian_to_bazi(2026, 8, 3, 14);
        let s = bazi_to_hex_str(&b);
        assert_eq!(s.chars().count(), 8); // 8 汉字
    }

    #[test]
    fn bazi_coords_len() {
        let b = gregorian_to_bazi(1996, 3, 15, 10);
        let c = bazi_to_coords(&b);
        assert_eq!(c.len(), 4);
    }

    #[test]
    fn zodiac_lookup() {
        let branch = 0u8; // 子 → 鼠
        assert_eq!(ZODIAC[branch as usize], "鼠");
    }
}
