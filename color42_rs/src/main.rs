// color42 - 汉字本体颜色编码 · 三维进制编码 (Rust 零依赖核心)
//
// 两套 6 行 × 7 列 = 42 字表，每个汉字本身是一个数码（本体编码，不替代代号）。
// 42 进制：3 字 = 三维编码，范围 0..42^3-1；每字一数码。
//
// 用法:
//   color42 list
//   color42 v <字> [表]
//   color42 c <值> [表]
//   color42 e <数值> [表] [位数]
//   color42 d <字串> [表]
//   color42 p <字> [表]
//   color42 g <字> [表]

use std::env;
use std::fs;
use std::process;

mod vm;

// 表1: 颜色表（无梯度）6行×7列=42字
const COLOR_ROWS: [&str; 6] = [
    "红橙黄绿青蓝紫",
    "褐棕黑靛粉彩白",
    "朱绛赭丹彤缃黛",
    "翠碧缥素银金灰",
    "玉琅晶璃珀瑙璧",
    "曦辉霓旖靡暝黟",
];

// 表2: 韵律表（带梯度）
const RHYTHM_ROWS: [&str; 6] = [
    "妃粉彤赤棕绛赭",
    "缃金黄褐黧乌黑",
    "缥翠绿青苍黛玄",
    "素银蓝紫靛绀黯",
    "玉琅晶璃珀瑙璧",
    "曦辉霓旖靡暝黟",
];

const RHYTHM_GRADIENT: [&str; 6] = [
    "赤基", "黄系·光", "绿系·生", "蓝系·冷", "泽系·石", "光系·韵",
];

fn table(name: &str) -> &'static [&'static str; 6] {
    match name {
        "韵律" | "rhythm" => &RHYTHM_ROWS,
        _ => &COLOR_ROWS,
    }
}

// 展平 42 字并返回 (字, 值)
fn flat(table: &[&str; 6]) -> Vec<char> {
    table.iter().flat_map(|r| r.chars()).collect()
}

fn find_value(table: &[&str; 6], ch: char) -> Option<usize> {
    flat(table).iter().position(|&c| c == ch)
}

fn value_of(table: &[&str; 6], ch: char) -> Result<usize, String> {
    find_value(table, ch).ok_or(format!("字 [{}] 不在表中", ch))
}

fn char_of(table: &[&str; 6], v: usize) -> Result<char, String> {
    let f = flat(table);
    if v >= 42 {
        return Err(format!("值须在 0-41 之间: {}", v));
    }
    Ok(f[v])
}

fn position_of(table: &[&str; 6], ch: char) -> Result<(usize, usize), String> {
    let v = value_of(table, ch)?;
    Ok((v / 7 + 1, v % 7 + 1))
}

fn gradient_of(table: &[&str; 6], ch: char) -> Result<&'static str, String> {
    if std::ptr::eq(table, &COLOR_ROWS) {
        return Ok("无梯度");
    }
    let (row, _) = position_of(table, ch)?;
    Ok(RHYTHM_GRADIENT[row - 1])
}

// 42 进制编码: value → digits 个汉字
fn encode(table: &[&str; 6], value: u64, digits: usize) -> Result<String, String> {
    let f = flat(table);
    let mut v = value;
    let mut out = Vec::new();
    for _ in 0..digits {
        out.push(f[(v % 42) as usize]);
        v /= 42;
    }
    if v > 0 {
        return Err(format!("数值超出 {} 位 42 进制范围", digits));
    }
    Ok(out.iter().rev().collect())
}

// 42 进制解码: 字串 → 数值
fn decode(table: &[&str; 6], chars: &str) -> Result<u64, String> {
    let f = flat(table);
    let mut v: u64 = 0;
    for c in chars.chars() {
        let idx = f.iter().position(|&x| x == c)
            .ok_or(format!("字 [{}] 不在表中", c))?;
        v = v * 42 + idx as u64;
    }
    Ok(v)
}

fn list_tables() {
    println!("汉字本体颜色编码（42 进制，每字一个数码）");
    println!();
    println!("第一套 · 颜色表（无梯度）");
    for (i, row) in COLOR_ROWS.iter().enumerate() {
        let spaced: Vec<String> = row.chars().map(|c| c.to_string()).collect();
        println!("  行{}: {}", i + 1, spaced.join("  "));
    }
    println!();
    println!("第二套 · 韵律表（带梯度）");
    for (i, row) in RHYTHM_ROWS.iter().enumerate() {
        let spaced: Vec<String> = row.chars().map(|c| c.to_string()).collect();
        println!("  行{}: {}  ({})", i + 1, spaced.join("  "), RHYTHM_GRADIENT[i]);
    }
    println!();
    match encode(&COLOR_ROWS, 100, 3) {
        Ok(s) => println!("42 进制示例: 数值 100 → {}（三维编码）", s),
        Err(_) => {}
    }
    println!("三维坐标: (行, 列) ∈ 6×7 = 42 位，每字一坐标");
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.is_empty() || args[0] == "list" || args[0] == "-l" || args[0] == "--list" {
        list_tables();
        return;
    }
    let cmd = &args[0];
    let tname = |i: usize| -> &str {
        if args.len() > i { &args[i] } else { "颜色" }
    };
    let result = (|| -> Result<String, String> {
        match cmd.as_str() {
            "run" => {
                let path = args.get(1).ok_or("缺少程序文件")?;
                let src = fs::read_to_string(path).map_err(|e| format!("读取失败: {}", e))?;
                let ops = vm::parse(&src)?;
                vm::run(&ops)?;
                Ok(format!("== 程序结束 ({}) ==", path))
            }
            "v" => {
                let ch = args.get(1).ok_or("缺少字")?.chars().next().ok_or("空字")?;
                let t = table(tname(2));
                Ok(format!("{} = {}", ch, value_of(t, ch)?))
            }
            "c" => {
                let v: usize = args.get(1).ok_or("缺少值")?.parse().map_err(|_| "值须为数字")?;
                let t = table(tname(2));
                Ok(format!("{} = {}", v, char_of(t, v)?))
            }
            "e" => {
                let v: u64 = args.get(1).ok_or("缺少数值")?.parse().map_err(|_| "数值须为数字")?;
                let t = table(tname(2));
                let d: usize = if args.len() > 3 { args[3].parse().unwrap_or(3) } else { 3 };
                Ok(format!("{} → {}（{} 维 {} 表）", v, encode(t, v, d)?, d, tname(2)))
            }
            "d" => {
                let s = args.get(1).ok_or("缺少字串")?;
                let t = table(tname(2));
                Ok(format!("{} = {}", s, decode(t, s)?))
            }
            "p" => {
                let ch = args.get(1).ok_or("缺少字")?.chars().next().ok_or("空字")?;
                let t = table(tname(2));
                let (r, c) = position_of(t, ch)?;
                Ok(format!("{} = (行{}, 列{})", ch, r, c))
            }
            "g" => {
                let ch = args.get(1).ok_or("缺少字")?.chars().next().ok_or("空字")?;
                let t = table(tname(2));
                Ok(format!("{} → {}", ch, gradient_of(t, ch)?))
            }
            other => Err(format!("未知命令: {}", other)),
        }
    })();
    match result {
        Ok(s) => println!("{}", s),
        Err(e) => {
            println!("错误: {}", e);
            process::exit(1);
        }
    }
}
