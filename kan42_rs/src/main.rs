// kan42 - 感知进制链 · 全量化辅助状态变化/身份互换 (Rust 零依赖)
//
// 多谱系串联为层级化组织:
//   颜色谱系 42进制 (6梯度系×7色)    宽单位
//   音韵谱系 2760进制 (声母23×韵母24×声调5)  最宽单位
//   时间谱系 60进制 (天干10×地支12=60甲子)   窄单位/相位
//
// 关系算子 (身份互换):
//   公约数 = 中心 (正交点/静态不变), 公倍数 = 边界 (镜像对偶/曲线)
//   gcd(42,60,2760) = 6  → 全谱系共享的中心
//   lcm(42,60,2760) = 3220 → 全谱系回归同一中心的周期
//   镜像对偶: 值 v 的镜像 = 进制-1-v (对称轴)
//
// 用法:
//   kan42 list            列出全部谱系与维度
//   kan42 color <字>      颜色字→梯度系/行/列/值
//   kan42 yinyun <音节>   音节→(声母,韵母,声调)/值
//   kan42 jiazi <甲子>    甲子→(天干,地支)/值
//   kan42 xh <谱系> <值>  镜像对偶: 进制-1-值
//   kan42 gcd             全谱系最大公约数 (中心)
//   kan42 lcm             全谱系最小公倍数 (周期)
//   kan42 gd <谱系> <值>  梯度系归属查询

use std::env;
use std::fs;
use std::process;

struct Kan42 {
    color_rows: Vec<Vec<String>>, // 6梯度系 × 7
    color_names: Vec<String>,
    sheng: Vec<String>,
    yun: Vec<String>,
    diao: Vec<String>,
    tian: Vec<String>,
    di: Vec<String>,
}

fn rules_path() -> String {
    for c in ["kan42_rs/rules/spectrum.chain", "rules/spectrum.chain"] {
        if std::path::Path::new(c).exists() {
            return c.to_string();
        }
    }
    "kan42_rs/rules/spectrum.chain".to_string()
}

fn load(path: &str) -> Result<Kan42, String> {
    let content = fs::read_to_string(path).map_err(|e| format!("规则表读取失败: {}", e))?;
    let mut k = Kan42 {
        color_rows: Vec::new(),
        color_names: Vec::new(),
        sheng: Vec::new(),
        yun: Vec::new(),
        diao: Vec::new(),
        tian: Vec::new(),
        di: Vec::new(),
    };
    let color_orders = ["红系", "黄系", "绿系", "蓝系", "泽系", "光系"];
    let mut color_map: std::collections::HashMap<String, Vec<String>> = std::collections::HashMap::new();
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
        match parts[0] {
            "声母" => k.sheng = items,
            "韵母" => k.yun = items,
            "声调" => k.diao = items,
            "天干" => k.tian = items,
            "地支" => k.di = items,
            other => {
                color_map.insert(other.to_string(), items);
            }
        }
    }
    for n in color_orders {
        if let Some(v) = color_map.get(n) {
            k.color_names.push(n.to_string());
            k.color_rows.push(v.clone());
        }
    }
    if k.color_rows.len() != 6 {
        return Err(format!("颜色谱系不完整: 期望6梯度系, 得{}", k.color_rows.len()));
    }
    Ok(k)
}

fn gcd(a: u64, b: u64) -> u64 {
    if b == 0 { a } else { gcd(b, a % b) }
}

fn lcm(a: u64, b: u64) -> u64 {
    a / gcd(a, b) * b
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    let k = load(&rules_path()).unwrap_or_else(|e| {
        println!("错误: {}", e);
        process::exit(1);
    });
    let cmd = args.first().map(|s| s.as_str()).unwrap_or("list");

    match cmd {
        "list" | "-l" => {
            let c42 = 6 * 7;
            let y2760 = k.sheng.len() * k.yun.len() * k.diao.len();
            let t60 = lcm(k.tian.len() as u64, k.di.len() as u64);
            println!("感知进制链 · 全量化辅助状态变化\n");
            println!("颜色谱系 {}进制 ({}梯度系 × 7色):", c42, k.color_names.len());
            for (i, (n, row)) in k.color_names.iter().zip(&k.color_rows).enumerate() {
                println!("  行{} {}: {}", i + 1, n, row.join(" "));
            }
            println!("\n音韵谱系 {}进制 (声母{} × 韵母{} × 声调{}):", y2760, k.sheng.len(), k.yun.len(), k.diao.len());
            println!("  声母: {}", k.sheng.join(" "));
            println!("  韵母: {}", k.yun.join(" "));
            println!("  声调: {}", k.diao.join(" "));
            println!("\n时间谱系 {}进制 (天干{} × 地支{} = {}甲子):", t60, k.tian.len(), k.di.len(), t60);
            println!("  天干: {}", k.tian.join(" "));
            println!("  地支: {}", k.di.join(" "));
            let g = gcd(gcd(c42 as u64, t60 as u64), y2760 as u64);
            let l = lcm(lcm(c42 as u64, t60 as u64), y2760 as u64);
            println!("\n层级: 时间(窄/相位) 管 颜色(中) 管 音韵(宽) —— 加法管理乘法");
            println!("公约数(中心/正交点/静态不变) gcd({},{},{}) = {}", c42, t60, y2760, g);
            println!("公倍数(边界/镜像对偶/周期) lcm({},{},{}) = {}", c42, t60, y2760, l);
            println!("身份互换: 任一字 ∈ 任一谱系, 均可换到另两谱系 (异置互换)");
        }
        "color" => {
            let ch = args.get(1).map(|s| s.as_str()).unwrap_or("");
            for (i, (n, row)) in k.color_names.iter().zip(&k.color_rows).enumerate() {
                if let Some(c) = row.iter().position(|x| x == ch) {
                    let v = i * 7 + c;
                    println!("{} = 行{}[{}] 列{} 值{} ({}进制)", ch, i + 1, n, c + 1, v, 42);
                    println!("  层级链: 时间(窄) ← 颜色(中) ← 音韵(宽)");
                    return;
                }
            }
            println!("字 [{}] 不在颜色谱系", ch);
        }
        "yinyun" => {
            let s = args.get(1).map(|s| s.as_str()).unwrap_or("");
            if let Some((si, fi, di)) = parse_syllable(&k, s) {
                let v = (si * k.yun.len() + fi) * k.diao.len() + di;
                println!("音节 {} → (声母{}, 韵母{}, 声调{}) 值{} ({}进制)",
                    s, si, fi, di, v, k.sheng.len() * k.yun.len() * k.diao.len());
            } else {
                println!("音节 [{}] 无法解析", s);
            }
        }
        "jiazi" => {
            let s = args.get(1).map(|s| s.as_str()).unwrap_or("");
            for (i, (t, d)) in k.tian.iter().zip(&k.di).enumerate() {
                let mut jia = String::new();
                jia.push_str(t);
                jia.push_str(d);
                if jia == s {
                    println!("{} = 天干{} 地支{} 值{} (60甲子)", s, i % 10, i % 12, i);
                    return;
                }
            }
            // 也支持单查
            if k.tian.contains(&s.to_string()) {
                let i = k.tian.iter().position(|x| x == &s.to_string()).unwrap();
                println!("天干{} 值{} (与地支{}组合起)", s, i, i % 12);
            } else if k.di.contains(&s.to_string()) {
                let i = k.di.iter().position(|x| x == &s.to_string()).unwrap();
                println!("地支{} 值{}", s, i);
            } else {
                println!("[{}] 不在时间谱系 (用甲子, 如 甲子/乙丑...)", s);
            }
        }
        "xh" => {
            // 镜像对偶
            let spec = args.get(1).map(|s| s.as_str()).unwrap_or("颜色");
            let v: u64 = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(0);
            let base: u64 = match spec {
                "颜色" => 42,
                "音韵" => (k.sheng.len() * k.yun.len() * k.diao.len()) as u64,
                "时间" => lcm(k.tian.len() as u64, k.di.len() as u64),
                _ => 42,
            };
            if v >= base {
                println!("值 {} 越界 (进制 {} 范围 0..{})", v, base, base - 1);
                return;
            }
            let mirror = base - 1 - v;
            println!("镜像对偶 {}进制: {} ↔ {} (对称轴 {})", base, v, mirror, (base - 1) as f64 / 2.0);
            println!("  公约数(中心)管辖: 静态不变; 公倍数(边界)管辖: 镜像对偶曲线");
        }
        "gcd" => {
            let c42 = 42u64;
            let y2760 = (k.sheng.len() * k.yun.len() * k.diao.len()) as u64;
            let t60 = lcm(k.tian.len() as u64, k.di.len() as u64);
            let g = gcd(gcd(c42, t60), y2760);
            println!("公约数(中心/正交点/静态不变)");
            println!("  gcd({}, {}, {}) = {}", c42, t60, y2760, g);
            println!("  中心男人=公约数, 静态固化不变; 所有公倍数受其管辖");
        }
        "lcm" => {
            let c42 = 42u64;
            let y2760 = (k.sheng.len() * k.yun.len() * k.diao.len()) as u64;
            let t60 = lcm(k.tian.len() as u64, k.di.len() as u64);
            let l = lcm(lcm(c42, t60), y2760);
            println!("公倍数(边界/镜像对偶/全周期)");
            println!("  lcm({}, {}, {}) = {}", c42, t60, y2760, l);
            println!("  边界女人=公倍数, 包裹中心; 全谱系回归同一中心的周期");
        }
        "gd" => {
            // 梯度系归属
            let spec = args.get(1).map(|s| s.as_str()).unwrap_or("颜色");
            let v: u64 = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(0);
            if spec == "颜色" {
                if v >= 42 {
                    println!("越界");
                    return;
                }
                let (row, col) = ((v / 7) as usize, (v % 7) as usize);
                println!("值{} → 行{}[{}] 列{} {}", v, row + 1, k.color_names[row], col + 1, k.color_rows[row][col]);
            } else if spec == "时间" {
                if v >= 60 {
                    println!("越界");
                    return;
                }
                let t = &k.tian[(v % 10) as usize];
                let d = &k.di[(v % 12) as usize];
                println!("值{} → 甲子 {}{}", v, t, d);
            } else {
                println!("gd 仅支持 颜色/时间 谱系");
            }
        }
        other => println!("未知命令: {} (可用: list/color/yinyun/jiazi/xh/gcd/lcm/gd)", other),
    }
}

// 解析音节: 最长匹配声母 → 最长匹配韵母 → 剩余匹配声调
fn parse_syllable(k: &Kan42, part: &str) -> Option<(usize, usize, usize)> {
    let chars: Vec<char> = part.chars().collect();
    for slen in (1..=chars.len()).rev() {
        let s: String = chars[..slen].iter().collect();
        if let Some(si) = k.sheng.iter().position(|x| x == &s) {
            for flen in (1..=(chars.len() - slen)).rev() {
                let f: String = chars[slen..slen + flen].iter().collect();
                if let Some(fi) = k.yun.iter().position(|x| x == &f) {
                    let rest: String = chars[slen + flen..].iter().collect();
                    if let Some(di) = k.diao.iter().position(|x| x == &rest) {
                        return Some((si, fi, di));
                    }
                }
            }
        }
    }
    None
}
