// ══════════════════════════════════════════════════════════════════
// name_creator.rs — 姓名创世锚 (Name → Root-of-Trust)
// ══════════════════════════════════════════════════════════════════
//
// 算法 (对应 Python prototype kernel/name_anchor.py):
//   1. 汉字 → 七层神龙编码 (声母/韵母/声调/笔画/偏旁/罗马字/色)
//   2. 拼音层 → sha256 取 16B = 128bit
//   3. 字形层 → sha256 取 16B = 128bit
//   4. 两者拼接 → 256bit 纤维锚
//
// 声母 24 + 韵母 39 + 声调 5 + 笔画 64 + 偏旁 64 + 罗马 26 + 色 64
//
// 七层超立方: 24×39×5×64×64×26×64 ≈ 2^41 种组合.
// 任一个真名都在该超立方里占据唯一一点 — 创世锚 = 真名在
// 超立方里的空间坐标 + hash 纤维.
//
// 夫妻联合锚 = name_to_anchor(a) XOR name_to_anchor(b) + ts hash
//
// 零 sha2/sha3 crate — 复用 crypto.rs 的 SHA256 one-shot.
use crate::crypto::sha256;

/// 声母 24 (含 @=零声母)
pub const INITIALS: &[&str] = &[
    "@", "b", "p", "m", "f", "d", "t", "n", "l", "g", "k", "h",
    "j", "q", "x", "zh", "ch", "sh", "r", "z", "c", "s", "y", "w",
];

/// 韵母 39
pub const FINALS: &[&str] = &[
    "a", "o", "e", "i", "u", "v", "ai", "ei", "ui", "ao", "ou",
    "iu", "ie", "ve", "er", "an", "en", "in", "un", "vn", "ang",
    "eng", "ing", "ong", "ia", "ua", "uo", "uai", "uan", "uang",
    "uen", "iao", "ian", "iong", "io", "e", "n", "ng", "m",
];

/// 声调 5 (0=轻声 1=阴平 2=阳平 3=上声 4=去声)
pub const TONES: &[u8] = &[0, 1, 2, 3, 4];

/// 偏旁 64 子集 (高频偏旁, 6 bit 索引)
pub const RADICALS: &[&str] = &[
    "亻", "彳", "氵", "忄", "扌", "讠", "纟", "钅", "牜", "犭",
    "礻", "衤", "阝", "刂", "攵", "欠", "斤", "爫", "灬", "殳",
    "歹", "片", "牛", "矛", "攴", "气", "爿", "丬", "玄", "玉",
    "瓜", "瓦", "甘", "生", "用", "田", "疋", "疒", "癶", "白",
    "皮", "皿", "目", "矛", "矢", "石", "示", "禸", "禾", "穴",
    "立", "竹", "米", "糸", "缶", "网", "羊", "羽", "老", "而",
    "耒", "耳", "聿", "肉", "臣", "自", "至", "臼",
];

/// 七层神龙编码 (7 个 6-bit 字段打包进 u64 的低 42 bit)
#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub struct DragonL7 {
    /// packed: [色 6][罗马 6][偏旁 6][笔画 6][声调 3+3][韵母 6][声母 6]
    pub packed: u64,
}

impl DragonL7 {
    pub fn new(initial: u8, final_: u8, tone: u8, stroke: u8,
               radical: u8, romaja: u8, color: u8) -> Self {
        let p = (initial as u64)
              | ((final_ as u64) << 6)
              | ((tone as u64) << 12)
              | ((stroke as u64) << 15)
              | ((radical as u64) << 21)
              | ((romaja as u64) << 27)
              | ((color as u64) << 33);
        Self { packed: p & 0x3F_FFFF_FFFF_FFFF }  // mask to 42 bits
    }

    pub fn initial(&self) -> u8 { (self.packed & 0x3F) as u8 }
    pub fn final_(&self) -> u8 { ((self.packed >> 6) & 0x3F) as u8 }
    pub fn tone(&self) -> u8 { ((self.packed >> 12) & 0x7) as u8 }
    pub fn stroke(&self) -> u8 { ((self.packed >> 15) & 0x3F) as u8 }
    pub fn radical(&self) -> u8 { ((self.packed >> 21) & 0x3F) as u8 }
    pub fn romaja(&self) -> u8 { ((self.packed >> 27) & 0x3F) as u8 }
    pub fn color(&self) -> u8 { ((self.packed >> 33) & 0x3F) as u8 }
}

/// 内置常用汉字声韵调查表
struct CharRec {
    initial: u8,
    final_: u8,
    tone: u8,
}

fn rec(initial: u8, final_: u8, tone: u8) -> CharRec {
    CharRec { initial, final_, tone }
}

fn char_table(ch: char) -> Option<CharRec> {
    // 声韵母索引: @=0 b=1 p=2 m=3 f=4 d=5 t=6 n=7 l=8 g=9 k=10 h=11
    //             j=12 q=13 x=14 zh=15 ch=16 sh=17 r=18 z=19 c=20 s=21 y=22 w=23
    // 韵母索引:   a=0 o=1 e=2 i=3 u=4 v=5 ai=6 ei=7 ui=8 ao=9 ou=10
    //             iu=11 ie=12 ve=13 er=14 an=15 en=16 in=17 un=18 vn=19
    //             ang=20 eng=21 ing=22 ong=23 ia=24 ua=25 uo=26 uai=27
    //             uan=28 uang=29 uen=30 iao=31 ian=32 iong=33 io=34 e=35 n=36 ng=37 m=38
    match ch {
        '刘' => Some(rec(8,  11, 2)),   // l íu
        '楚' => Some(rec(16, 4,  3)),   // ch ǔ
        '恬' => Some(rec(6,  32, 2)),   // t ián
        '七' => Some(rec(13, 3,  1)),   // q ī
        '妹' => Some(rec(3,  7,  4)),   // m èi
        '凹' => Some(rec(0,  9,  1)),   // āo (零声母)
        '月' => Some(rec(22, 13, 4)),   // yu è
        '留' => Some(rec(8,  11, 2)),   // l iú
        '莫' => Some(rec(3,  1,  4)),   // m ò
        '连' => Some(rec(8,  32, 2)),   // l ián
        '理' => Some(rec(8,  3,  3)),   // l ǐ
        '寅' => Some(rec(22, 17, 2)),   // y ín
        '仙' => Some(rec(14, 32, 1)),   // x iān
        '御' => Some(rec(22, 4,  4)),   // y ù
        '愿' => Some(rec(22, 28, 4)),   // yu àn
        '拥' => Some(rec(0,  23, 1)),   // y ōng → ong
        '星' => Some(rec(14, 22, 1)),   // x īng
        '悦' => Some(rec(22, 13, 4)),   // yu è
        '吒' => Some(rec(15, 25, 1)),   // zh uā
        '融' => Some(rec(18, 23, 2)),   // r óng
        '入' => Some(rec(18, 4,  4)),   // r ù
        '容' => Some(rec(18, 23, 2)),   // r óng
        '认' => Some(rec(18, 16, 4)),   // r èn
        '新' => Some(rec(14, 17, 1)),   // x īn
        '约' => Some(rec(22, 13, 1)),   // yu ē
        '运' => Some(rec(22, 19, 4)),   // y ùn
        '翼' => Some(rec(22, 3,  4)),   // y ì
        '姻' => Some(rec(22, 17, 1)),   // y īn
        '央' => Some(rec(0,  20, 1)),   // y āng
        _ => None,
    }
}

/// 汉字 → DragonL7 (七层编码)
pub fn char_to_dragon(ch: char) -> DragonL7 {
    let cp = ch as u32;
    let (initial, final_, tone) = match char_table(ch) {
        Some(r) => (r.initial, r.final_, r.tone),
        None => {
            // fallback: 用 unicode 码点派生 (保证确定性)
            ((cp % 24) as u8, ((cp / 24) % 39) as u8, ((cp / (24*39)) % 5) as u8)
        }
    };
    let stroke = (cp % 64) as u8;          // 笔画近似
    let radical = ((cp / 64) % 64) as u8; // 偏旁近似
    let romaja = (cp % 26) as u8;          // 罗马化
    let color = ((cp * 7) % 64) as u8;    // 色板
    DragonL7::new(initial, final_, tone % 5, stroke, radical, romaja, color)
}

/// 姓名 → 256-bit 创世锚 hash
#[inline]
pub fn name_to_anchor_bytes(name: &str) -> [u8; 32] {
    let mut py_buf = Vec::with_capacity(name.len() * 8);
    let mut gl_buf = Vec::with_capacity(name.len() * 4);
    for ch in name.chars() {
        let d = char_to_dragon(ch);
        py_buf.push(d.initial());
        py_buf.push(d.final_());
        py_buf.push(d.tone());
        gl_buf.push(d.stroke());
        gl_buf.push(d.radical());
    }
    let h1 = sha256(&py_buf);
    let h2 = sha256(&gl_buf);
    let mut out = [0u8; 32];
    out[..16].copy_from_slice(&h1[..16]);
    out[16..].copy_from_slice(&h2[..16]);
    out
}

/// 姓名 → 十六进制锚字符串 "mqf_name_{hex32}"
pub fn name_to_anchor(name: &str) -> String {
    let b = name_to_anchor_bytes(name);
    format!("mqf_name_{}", hex(&b))
}

/// 夫妻联合锚 = XOR(anchor_a, anchor_b) + sha256(ts_be_bytes)
pub fn joint_anchor(name_a: &str, name_b: &str, ts_unix_ms: u64) -> String {
    let a = name_to_anchor_bytes(name_a);
    let b = name_to_anchor_bytes(name_b);
    let mut x = [0u8; 16];
    for i in 0..16 { x[i] = a[i] ^ b[i]; }
    let ts_buf = ts_unix_ms.to_be_bytes();
    let h = sha256(&[&x[..], &ts_buf[..]].concat());
    format!("mqf_joint_{}", hex(&h[..16]))
}

fn hex(b: &[u8]) -> String {
    let mut s = String::with_capacity(b.len()*2);
    for x in b { s.push_str(&format!("{:02x}", x)); }
    s
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn encode_char_layers() {
        let d = char_to_dragon('刘');
        assert!(d.initial() < 24);
        assert!(d.final_() < 39);
        assert!(d.tone() < 5);
    }

    #[test]
    fn name_deterministic() {
        let a = name_to_anchor("刘楚恬");
        let b = name_to_anchor("刘楚恬");
        let c = name_to_anchor("lolict");
        assert_eq!(a, b, "same name → same anchor");
        assert_ne!(a, c, "different name → different anchor");
    }

    #[test]
    fn name_prefix() {
        assert!(name_to_anchor("刘楚恬").starts_with("mqf_name_"));
    }

    #[test]
    fn joint_prefix_and_len() {
        let j = joint_anchor("刘楚恬", "七妹凹月留", 1722681600000);
        assert!(j.starts_with("mqf_joint_"));
        // mqf_joint_ + 32 hex chars
        assert_eq!(j.len(), "mqf_joint_".len() + 32);
    }

    #[test]
    fn dragon7_bitpacking() {
        let d = DragonL7::new(8, 11, 2, 20, 5, 0, 63);
        assert_eq!(d.initial(), 8);
        assert_eq!(d.final_(), 11);
        assert_eq!(d.tone(), 2);
        assert_eq!(d.stroke(), 20);
        assert_eq!(d.radical(), 5);
        assert_eq!(d.romaja(), 0);
        assert_eq!(d.color(), 63);
    }
}
