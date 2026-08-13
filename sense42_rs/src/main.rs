// sense42 - 感官映射链 · 跨感官互译 (Rust 零依赖)
//
// 六根 = 色声香味触法, 对应颜色谱系6梯度系
// 颜色字 (行r,列c) → 感官r的第c级梯度 → 可译成任意感官
// 颜色 → 音高/情绪/方位/时空 全映射
//
// 用法:
//   sense42 list              列出六根·梯度·映射
//   sense42 trans <颜色字> <感官>  颜色字 → 目标感官梯度
//   sense42 map <感官> <级>    感官在某一级的梯度字
//   sense42 polar <颜色字>     颜色字 → 情绪极性/方位/音高/频率
//   sense42 freq <颜色字>      颜色字 → 音高频率Hz
//   sense42 audio <颜色字>     颜色字 → 听觉梯度字

use std::env;
use std::fs;
use std::process;

const NOTES: [&str; 7] = ["C", "D", "E", "F", "G", "A", "B"];
const OCTAVE_BASE: f64 = 261.63; // C4

struct Sense42 {
    color_rows: Vec<Vec<String>>, // 6梯度系 × 7
    color_names: Vec<String>,
    senses: Vec<String>,          // 色声香味触法
    sense_names: Vec<String>,     // 视觉/听觉/...
    senses_map: Vec<String>,      // 感官 → 索引 (中文感官名或六根名)
    gradients: Vec<Vec<String>>,  // 每感官7级
    polarity: Vec<String>,        // 6情绪
    direction: Vec<String>,       // 6方位
}

fn rules_path() -> String {
    for c in ["sense42_rs/rules/sense.chain", "rules/sense.chain"] {
        if std::path::Path::new(c).exists() {
            return c.to_string();
        }
    }
    "sense42_rs/rules/sense.chain".to_string()
}

fn color_rules_path() -> String {
    for c in [
        "kan42_rs/rules/spectrum.chain",
        "rules/spectrum.chain",
    ] {
        if std::path::Path::new(c).exists() {
            return c.to_string();
        }
    }
    "kan42_rs/rules/spectrum.chain".to_string()
}

fn load_sense(path: &str) -> Result<Vec<(String, Vec<String>)>, String> {
    let content = fs::read_to_string(path).map_err(|e| format!("感官规则表读取失败: {}", e))?;
    let mut out = Vec::new();
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
        out.push((parts[0].to_string(), items));
    }
    Ok(out)
}

fn load_color_rows(path: &str) -> Result<(Vec<String>, Vec<Vec<String>>), String> {
    let content = fs::read_to_string(path).map_err(|e| format!("颜色谱系读取失败: {}", e))?;
    let orders = ["红系", "黄系", "绿系", "蓝系", "泽系", "光系"];
    let mut map: std::collections::HashMap<String, Vec<String>> = std::collections::HashMap::new();
    for line in content.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let parts: Vec<&str> = line.split('|').map(|s| s.trim()).collect();
        if parts.len() < 2 {
            continue;
        }
        let items: Vec<String> = if parts[1].contains(' ') {
            parts[1].split_whitespace().map(|s| s.to_string()).collect()
        } else {
            parts[1].chars().map(|c| c.to_string()).collect()
        };
        map.insert(parts[0].to_string(), items);
    }
    let mut names = Vec::new();
    let mut rows = Vec::new();
    for o in orders {
        if let Some(v) = map.get(o) {
            names.push(o.to_string());
            rows.push(v.clone());
        }
    }
    if rows.len() != 6 {
        return Err("颜色谱系不完整".to_string());
    }
    Ok((names, rows))
}

fn load() -> Result<Sense42, String> {
    let rows = load_sense(&rules_path())?;
    let mut k = Sense42 {
        color_rows: Vec::new(),
        color_names: Vec::new(),
        senses: Vec::new(),
        sense_names: Vec::new(),
        senses_map: Vec::new(),
        gradients: Vec::new(),
        polarity: Vec::new(),
        direction: Vec::new(),
    };
    // 六根
    if let Some((_, v)) = rows.iter().find(|(n, _)| n == "感官") {
        k.senses = v.clone();
    }
    // 感官名 6 行: 色感官/声感官/... 每行 [中文名, 别名]
    for s in ["色", "声", "香", "味", "触", "法"] {
        if let Some((_, v)) = rows.iter().find(|(n, _)| n == &format!("{}感官", s)) {
            k.sense_names.push(v.first().cloned().unwrap_or_default());
            k.senses_map.push(s.to_string());
        }
    }
    // 梯度: 每感官 [梯度字×7]
    for s in ["色", "声", "香", "味", "触", "法"] {
        if let Some((_, v)) = rows.iter().find(|(n, _)| n == &format!("{}感官梯度", s)) {
            k.gradients.push(v.clone());
        }
    }
    if let Some((_, v)) = rows.iter().find(|(n, _)| n == "情绪极性") {
        k.polarity = v.clone();
    }
    if let Some((_, v)) = rows.iter().find(|(n, _)| n == "空间方位") {
        k.direction = v.clone();
    }
    let (names, rows) = load_color_rows(&color_rules_path())?;
    k.color_names = names;
    k.color_rows = rows;
    Ok(k)
}

fn color_pos(k: &Sense42, ch: &str) -> Option<(usize, usize, usize)> {
    // 返回 (值, 行, 列)
    for (r, row) in k.color_rows.iter().enumerate() {
        if let Some(c) = row.iter().position(|x| x == ch) {
            return Some((r * 7 + c, r, c));
        }
    }
    None
}

fn sense_index(k: &Sense42, s: &str) -> Option<usize> {
    // 支持: 色声香味触法 / 视觉听觉... / 眼耳鼻舌身意 / 数字0-5
    for (i, (name, six)) in k.sense_names.iter().zip(&k.senses_map).enumerate() {
        if s == name || s == six {
            return Some(i);
        }
    }
    match s {
        "眼" => Some(0),
        "耳" => Some(1),
        "鼻" => Some(2),
        "舌" => Some(3),
        "身" => Some(4),
        "意" => Some(5),
        _ => s.parse::<usize>().ok().filter(|&i| i < 6),
    }
}

fn note_for(v: usize) -> (usize, &'static str) {
    let octave = v / 7; // 0-5
    let note = NOTES[v % 7];
    (octave, note)
}

fn freq_for(v: usize) -> f64 {
    let octave = v / 7;
    let note = v % 7;
    let semitone = match note {
        0 => 0.0, // C
        1 => 2.0, // D
        2 => 4.0, // E
        3 => 5.0, // F
        4 => 7.0, // G
        5 => 9.0, // A
        _ => 11.0, // B
    };
    OCTAVE_BASE * 2f64.powf((octave as f64) + semitone / 12.0)
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    let k = load().unwrap_or_else(|e| {
        println!("错误: {}", e);
        process::exit(1);
    });
    let cmd = args.first().map(|s| s.as_str()).unwrap_or("list");

    match cmd {
        "list" | "-l" => {
            println!("感官映射链 · 跨感官互译 (六根 = 色声香味触法)\n");
            for i in 0..6 {
                let (six, name, grad) = (&k.senses[i], &k.sense_names[i], &k.gradients[i]);
                println!("{}感官[{}] 7级: {}", six, name, grad.join(" "));
                println!("   ↳ 颜色{} 值{}-{}", k.color_names[i], i * 7, i * 7 + 6);
            }
            println!("\n情绪极性 (6梯度系): {}", k.polarity.join(" "));
            println!("空间方位 (6梯度系): {}", k.direction.join(" "));
            println!("音高映射: 每梯度系一个八度, 7列=7音阶 {}", NOTES.join(" "));
            println!("\n跨感官互译: 颜色字(行r,列c) → 感官r的第c级梯度");
        }
        "trans" => {
            let ch = args.get(1).map(|s| s.as_str()).unwrap_or("");
            let target = args.get(2).map(|s| s.as_str()).unwrap_or("法");
            let (v, r, c) = match color_pos(&k, ch) {
                Some(x) => x,
                None => {
                    println!("字 [{}] 不在颜色谱系", ch);
                    return;
                }
            };
            let ti = match sense_index(&k, target) {
                Some(x) => x,
                None => {
                    println!("未知感官: {} (可用: {} / 色声香味触法 / 眼耳鼻舌身意)", target, k.sense_names.join("/"));
                    return;
                }
            };
            let grad = &k.gradients[ti][c];
            println!("{} ({}) → {}感官{}级 = [{}]", ch, k.color_names[r], k.senses[ti], c, grad);
            println!("  颜色值{} 六根归属{} ({}), 梯度级{}", v, k.senses[ti], k.sense_names[ti], c);
        }
        "map" => {
            let s = args.get(1).map(|s| s.as_str()).unwrap_or("法");
            let lvl: usize = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(0);
            let si = match sense_index(&k, s) {
                Some(x) => x,
                None => {
                    println!("未知感官");
                    return;
                }
            };
            if lvl >= 7 {
                println!("梯度级越界 (0-6)");
                return;
            }
            println!("{}感官[{}] 第{}级 = [{}]", k.senses[si], k.sense_names[si], lvl, k.gradients[si][lvl]);
        }
        "polar" => {
            let ch = args.get(1).map(|s| s.as_str()).unwrap_or("");
            let (v, r, c) = match color_pos(&k, ch) {
                Some(x) => x,
                None => {
                    println!("字 [{}] 不在颜色谱系", ch);
                    return;
                }
            };
            let (oct, note) = note_for(v);
            let f = freq_for(v);
            println!("{} = 值{} 颜色{} 列{}", ch, v, k.color_names[r], c);
            println!("  情绪极性: [{}]", k.polarity[r]);
            println!("  空间方位: [{}]", k.direction[r]);
            println!("  音高: {}{} 频率 {:.1}Hz", note, oct + 1, f);
            println!("  法感官: [{}] (意识·显隐)", k.gradients[5][c]);
        }
        "freq" => {
            let ch = args.get(1).map(|s| s.as_str()).unwrap_or("");
            let (v, _, _) = match color_pos(&k, ch) {
                Some(x) => x,
                None => {
                    println!("字 [{}] 不在颜色谱系", ch);
                    return;
                }
            };
            let (oct, note) = note_for(v);
            let f = freq_for(v);
            println!("{} = 值{} → 音高{}{} 频率{:.1}Hz", ch, v, note, oct + 1, f);
        }
        "audio" => {
            let ch = args.get(1).map(|s| s.as_str()).unwrap_or("");
            let (v, r, c) = match color_pos(&k, ch) {
                Some(x) => x,
                None => {
                    println!("字 [{}] 不在颜色谱系", ch);
                    return;
                }
            };
            println!("{} ({}) → 听觉 = [{}]", ch, k.color_names[r], k.gradients[1][c]);
            println!("  值{} 声音梯度级{}", v, c);
        }
        other => println!("未知命令: {} (可用: list/trans/map/polar/freq/audio)", other),
    }
}
