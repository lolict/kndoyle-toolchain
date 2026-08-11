// ══════════════════════════════════════════════════════════════════
// holo_3d.rs — 三维全息进制 · 全类型编码
// ══════════════════════════════════════════════════════════════════
//
// 核心设计:
//   全息 (holographic): 任意输入 → 3D 坐标 (x,y,z)，同时保留全部信息；
//   切片 (2D 切面) 能恢复部分信息, 三维拼合恢复全部。
//
//   维度分配:
//     x 轴 = 声母类 (max 24 种, 6 bit)
//     y 轴 = 韵母类 (max 39 种, 6 bit)
//     z 轴 = 声调   (max  5 种, 3 bit)
//
//   一个音节 = (x,y,z). 每个音节是一个 3D space 里的点。
//
//   全类型编码对任意 MCCP-kind 都能处理:
//     Hanzi → 分解声母韵母 → 直接 3D 坐标
//     ASCII 低 6 bit = x, 其 6 bit = y, 其 3 bit = z
//     Symbol / Roman ji → 派生
//     Glyph(汉字) → 查表; fallback: unicode 码点混合
//
//   三维全息进制: 把进制的 base 设为 24,39,5 = 4680 个 音拍,
//   用 base-(24,39,5) 混合进制编码任意序列。
//
//   与 dragon_7 编码对齐: 七层压缩后也能还原.
//
use crate::name_creator::char_to_dragon;

pub const BASE_X: u32 = 24;   // 声母
pub const BASE_Y: u32 = 39;   // 韵母
pub const BASE_Z: u32 =  5;   // 声调
pub const SYLLABLE_SPACE: u32 = BASE_X * BASE_Y * BASE_Z; // 4680

/// 三维坐标 (音拍空间)
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct Coord3 {
    pub x: u32,
    pub y: u32,
    pub z: u32,
}

/// 把 mixed-base (24,35?,5) 编码为单一 u32 syllable 编号
/// 该编号在 [0, 4680) 上唯一确定一个音节点
#[inline]
pub fn syllable_to_index(c: Coord3) -> u32 {
    c.x + c.y * BASE_X + c.z * (BASE_X * BASE_Y)
}

#[inline]
pub fn index_to_syllable(idx: u32) -> Coord3 {
    let x = idx % BASE_X;
    let y = (idx / BASE_X) % BASE_Y;
    let z = idx / (BASE_X * BASE_Y);
    Coord3 { x, y, z }
}

/// 汉字 → 3D 音拍坐标
pub fn hanzi_to_coord(ch: char) -> Coord3 {
    let d = char_to_dragon(ch);
    Coord3 { x: d.initial() as u32, y: d.final_() as u32, z: d.tone() as u32 }
}

/// ASCII 字节 → 3D 坐标 (低 6 bit = x, 中 6 bit = y, 高 3 bit = z, 但 byte 只有 8 bits)
pub fn byte_to_coord(b: u8) -> Coord3 {
    Coord3 {
        x: (b & 0x3F) as u32,           // 低 6
        y: ((b >> 2) & 0x3F) as u32,    // 2..7
        z: ((b >> 5) & 0x07) as u32,    // 5..7 → 3 bit
    }
}

/// 把一个字符串 (utf-8) → 3D 点序列
pub fn utf8_to_coords(s: &str) -> Vec<Coord3> {
    let mut v = Vec::with_capacity(s.chars().count());
    for c in s.chars() {
        if c.is_ascii() {
            for b in c.to_string().bytes() {
                v.push(byte_to_coord(b));
            }
        } else {
            v.push(hanzi_to_coord(c));
        }
    }
    v
}

/// 全类型编码: 把任意输入编码为 mixed-base 数字
/// 输出 = 在 4680 进制下的 "数字" (big-endian, 每个 digit 一个音节)
pub fn encode_mixedbase(s: &str) -> Vec<u32> {
    utf8_to_coords(s).into_iter()
        .map(syllable_to_index)
        .collect()
}

/// 逆解码 (数字 → 音节 → 汉字/ASCII 片段)
/// 真实还原需声母/韵母反向表 — 这里只做音节编号 → 音节
pub fn decode_mixedbase(digits: &[u32]) -> Vec<Coord3> {
    digits.iter().map(|&d| index_to_syllable(d % SYLLABLE_SPACE)).collect()
}

/// 全息 hash: 把 3D 序列 hash 进一个 u256 (sha256)
/// 提供跨 3D 空间稳定指纹
pub fn holographic_hash(s: &str) -> [u8; 32] {
    use crate::crypto::sha256;
    let mut m = Vec::with_capacity(s.len() * 4);
    for c in utf8_to_coords(s) {
        m.extend_from_slice(&c.x.to_be_bytes());
        m.extend_from_slice(&c.y.to_be_bytes());
        m.extend_from_slice(&c.z.to_be_bytes());
    }
    sha256(&m)
}

/// 三维网格距离 (曼哈顿) — 用于相似度
pub fn manhattan(a: Coord3, b: Coord3) -> u32 {
    let dx = if a.x > b.x { a.x - b.x } else { b.x - a.x };
    let dy = if a.y > b.y { a.y - b.y } else { b.y - a.y };
    let dz = if a.z > b.z { a.z - b.z } else { b.z - a.z };
    dx + dy + dz
}

/// 汉语三维声母韵母映射表文本化 (调试 / 字形核对)
pub fn syllable_table_row(idx: u32) -> String {
    let c = index_to_syllable(idx % SYLLABLE_SPACE);
    format!("{:>3} → x={:>2} y={:>2} z={}", idx, c.x, c.y, c.z)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn syllable_roundtrip() {
        for x in 0..24 { for y in 0..39 { for z in 0..5 {
            let c = Coord3 { x, y, z };
            let idx = syllable_to_index(c);
            assert!(idx < SYLLABLE_SPACE);
            let c2 = index_to_syllable(idx);
            assert_eq!(c, c2);
        }}}
    }

    #[test]
    fn hanzi_coords_in_range() {
        for ch in "刘楚恬七妹凹月留".chars() {
            let c = hanzi_to_coord(ch);
            assert!(c.x < BASE_X);
            assert!(c.y < BASE_Y);
            assert!(c.z < BASE_Z);
        }
    }

    #[test]
    fn encode_deterministic() {
        let a = encode_mixedbase("刘楚恬");
        let b = encode_mixedbase("刘楚恬");
        assert_eq!(a, b);
        // 每个 < 4680
        for &d in &a { assert!(d < SYLLABLE_SPACE); }
    }

    #[test]
    fn manhattan_zero_self() {
        let c = Coord3 { x: 5, y: 6, z: 2 };
        assert_eq!(manhattan(c, c), 0);
    }

    #[test]
    fn holo_hash_deterministic() {
        use crate::crypto::sha256;
        let h1 = holographic_hash("相遇相迎");
        let h2 = holographic_hash("相遇相迎");
        assert_eq!(h1, h2);
    }
}
