// lang42 - 声韵调层级进制 · 以人类语言为单位的进制 (Rust 零依赖)
//
// 核心规则: 进制必须以排列发生, 以人类语言为单位, 不掺非语言符号.
// 三级数码单位:
//   声母 23 = 窄单位 (最窄量化)
//   韵母 24 = 宽单位 (最长符号量)
//   声调 5  = 相位单位
//   音节    = 声母+韵母+声调 = 共同体(字) = 23×24×5 = 2760 全覆盖
//
// 层级化: 声母(窄) 管 韵母(宽) —— 加法管理乘法, 权力链条
// 一维时间串联: 声母先于韵母, 声调为相位
// 公约折叠: 2760 = 23×24×5, 按因子拆分层级, 找出可折叠的层级关系
//
// 用法:
//   lang42 list
//   lang42 sheng   <索引>    声母索引→字母
//   lang42 yun     <索引>    韵母索引→韵母
//   lang42 diao    <索引>    声调索引→调名
//   lang42 jie     <音节>    音节→三维坐标(声母,韵母,声调)
//   lang42 e       <数值>    数值→音节编码(四音节=2760^3空间)
//   lang42 d       <音节串>  音节串→数值
//   lang42 fold    <总量>    公约折叠: 因数分解找层级

use std::env;
use std::fs;
use std::process;

struct Yinyun {
    sheng: Vec<String>, // 声母 窄单位
    yun: Vec<String>,   // 韵母 宽单位
    diao: Vec<String>,  // 声调 相位
}

fn load_rules(path: &str) -> Result<Yinyun, String> {
    let content = fs::read_to_string(path).map_err(|e| format!("规则表读取失败: {}", e))?;
    let mut sheng = Vec::new();
    let mut yun = Vec::new();
    let mut diao = Vec::new();
    for line in content.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let parts: Vec<&str> = line.split('|').map(|s| s.trim()).collect();
        if parts.len() < 2 {
            continue;
        }
        let items: Vec<String> = parts[1].split_whitespace().map(|s| s.to_string()).collect();
        match parts[0] {
            "声母" => sheng = items,
            "韵母" => yun = items,
            "声调" => diao = items,
            _ => {}
        }
    }
    if sheng.is_empty() || yun.is_empty() || diao.is_empty() {
        return Err("规则表不完整: 需声母/韵母/声调三段".into());
    }
    Ok(Yinyun { sheng, yun, diao })
}

// 公约折叠: 因数分解, 找出可折叠的层级关系
fn fold(n: u64) -> Vec<u64> {
    let mut factors = Vec::new();
    let mut v = n;
    let mut d = 2;
    while d * d <= v {
        while v % d == 0 {
            factors.push(d);
            v /= d;
        }
        d += 1;
    }
    if v > 1 {
        factors.push(v);
    }
    factors
}

fn rules_path() -> String {
    let candidates = ["lang42_rs/rules/yinyun.chain", "rules/yinyun.chain"];
    for c in candidates {
        if std::path::Path::new(c).exists() {
            return c.to_string();
        }
    }
    "lang42_rs/rules/yinyun.chain".to_string()
}

// 解析音节: 最长匹配声母 → 最长匹配韵母 → 剩余匹配声调
fn parse_syllable(yinyun: &Yinyun, part: &str) -> Option<(usize, usize, usize)> {
    let chars: Vec<char> = part.chars().collect();
    // 找声母: 从首字符起, 尝试各长度
    for slen in (1..=chars.len()).rev() {
        let s: String = chars[..slen].iter().collect();
        if let Some(si) = yinyun.sheng.iter().position(|x| x == &s) {
            // 找韵母: 从声母后起
            for flen in (1..=(chars.len() - slen)).rev() {
                let f: String = chars[slen..slen + flen].iter().collect();
                if let Some(fi) = yinyun.yun.iter().position(|x| x == &f) {
                    let rest: String = chars[slen + flen..].iter().collect();
                    if let Some(di) = yinyun.diao.iter().position(|x| x == &rest) {
                        return Some((si, fi, di));
                    }
                }
            }
        }
    }
    None
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    let yinyun = load_rules(&rules_path()).unwrap_or_else(|e| {
        println!("错误: {}", e);
        process::exit(1);
    });
    let cmd = args.first().map(|s| s.as_str()).unwrap_or("list");

    match cmd {
        "list" | "-l" => {
            println!("声韵调层级进制 · 以人类语言为单位的进制");
            println!("规则: 进制以排列发生, 以人类语言为单位, 不掺非语言符号\n");
            println!("声母 {} 个 (窄单位 · 最窄量化):", yinyun.sheng.len());
            println!("  {}", yinyun.sheng.join(" "));
            println!("\n韵母 {} 个 (宽单位 · 最长符号量):", yinyun.yun.len());
            println!("  {}", yinyun.yun.join(" "));
            println!("\n声调 {} 个 (相位单位):", yinyun.diao.len());
            println!("  {}", yinyun.diao.join(" "));
            let total = yinyun.sheng.len() * yinyun.yun.len() * yinyun.diao.len();
            println!("\n音节 = 声母+韵母+声调 = 共同体(字)");
            println!("  覆盖率 = {} × {} × {} = {} 个音节 (语言全方位覆盖)", 
                yinyun.sheng.len(), yinyun.yun.len(), yinyun.diao.len(), total);
            println!("层级: 声母(窄) 管 韵母(宽) —— 加法管理乘法, 权力链条");
            println!("一维时间串联: 声母先于韵母, 声调为相位");
        }
        "sheng" => {
            let idx: usize = args.get(1).and_then(|s| s.parse().ok()).unwrap_or(0);
            match yinyun.sheng.get(idx) {
                Some(s) => println!("声母[{}] = {}", idx, s),
                None => println!("声母索引 {} 越界 (0..{})", idx, yinyun.sheng.len()),
            }
        }
        "yun" => {
            let idx: usize = args.get(1).and_then(|s| s.parse().ok()).unwrap_or(0);
            match yinyun.yun.get(idx) {
                Some(s) => println!("韵母[{}] = {}", idx, s),
                None => println!("韵母索引 {} 越界 (0..{})", idx, yinyun.yun.len()),
            }
        }
        "diao" => {
            let idx: usize = args.get(1).and_then(|s| s.parse().ok()).unwrap_or(0);
            match yinyun.diao.get(idx) {
                Some(s) => println!("声调[{}] = {}", idx, s),
                None => println!("声调索引 {} 越界 (0..{})", idx, yinyun.diao.len()),
            }
        }
        "jie" => {
            // 音节 → 三维坐标 (声母,韵母,声调)
            let s = args.get(1).map(|s| s.as_str()).unwrap_or("");
            if s.is_empty() {
                println!("用法: lang42 jie <音节>  例: lang42 jie ma阴平");
                process::exit(1);
            }
            match parse_syllable(&yinyun, s) {
                Some((si, fi, tone)) => {
                    println!("音节 {} → (声母{}, 韵母{}, 声调{})", s, si, fi, tone);
                    let value = si * yinyun.yun.len() * yinyun.diao.len() + fi * yinyun.diao.len() + tone;
                    println!("  值 = {}", value);
                    println!("  层链: {} (窄) → {} (宽) → {} (相位)",
                        yinyun.sheng[si], yinyun.yun[fi], yinyun.diao[tone]);
                }
                None => println!("音节 [{}] 无法解析 (需 声母+韵母+声调 例: ma阴平)", s),
            }
        }
        "e" => {
            // 数值 → 音节编码 (四音节 = 2760^3 空间)
            let n: u64 = args.get(1).and_then(|s| s.parse().ok()).unwrap_or(0);
            let ns = yinyun.sheng.len();
            let ny = yinyun.yun.len();
            let nd = yinyun.diao.len();
            let base = (ns * ny * nd) as u64;
            let mut v = n;
            let mut out = Vec::new();
            for _ in 0..4 {
                let d = (v % base) as usize;
                let tone = d % nd;
                let d = d / nd;
                let yun = d % ny;
                let sheng = d / ny;
                out.push(format!("{}{}{}", yinyun.sheng[sheng], yinyun.yun[yun], yinyun.diao[tone]));
                v /= base;
            }
            out.reverse();
            println!("{} → {}", n, out.join("."));
        }
        "d" => {
            // 音节串 → 数值
            let s = args.get(1).map(|s| s.as_str()).unwrap_or("");
            let ns = yinyun.sheng.len();
            let ny = yinyun.yun.len();
            let nd = yinyun.diao.len();
            let base = (ns * ny * nd) as u64;
            let mut v: u64 = 0;
            for part in s.split('.') {
                let part = part.trim();
                if part.is_empty() {
                    continue;
                }
                match parse_syllable(&yinyun, part) {
                    Some((si, fi, tone)) => {
                        let val = ((si * ny) + fi) * nd + tone;
                        v = v * base + val as u64;
                    }
                    None => {
                        println!("音节 [{}] 无法解析", part);
                        process::exit(1);
                    }
                }
            }
            println!("{} = {}", s, v);
        }
        "fold" => {
            let n: u64 = args.get(1).and_then(|s| s.parse().ok()).unwrap_or(2760);
            let factors = fold(n);
            println!("公约折叠: {} = {}", n, factors.iter().map(|f| f.to_string()).collect::<Vec<_>>().join(" × "));
            // 找出可折叠的层级 (两两合并)
            let ns = yinyun.sheng.len();
            let ny = yinyun.yun.len();
            let nd = yinyun.diao.len();
            println!("语言层级: {} (声母) × {} (韵母) × {} (声调) = {}", ns, ny, nd, ns * ny * nd);
            if n == (ns * ny * nd) as u64 {
                println!("→ 音节总量 = 声韵调三级折叠, 无需公约化 (天然层级)");
            } else {
                println!("→ 总量 {} 需按因子拆分层级: {}", n, factors.iter().map(|f| f.to_string()).collect::<Vec<_>>().join(" × "));
            }
        }
        other => println!("未知命令: {} (可用: list/sheng/yun/diao/jie/e/d/fold)", other),
    }
}
