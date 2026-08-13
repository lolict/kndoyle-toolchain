// kan42 - 感知进制链 · 全量化辅助状态变化/身份互换 (Rust 零依赖)
//
// 多谱系串联为层级化组织:
//   颜色谱系 42进制 (6梯度系×7色)      中单位
//   音韵谱系 2760进制 (声母23×韵母24×声调5)  最宽单位
//   时间谱系 60进制 (天干10×地支12=60甲子)   窄单位/相位
//   生态谱系 (扩展): 生肖12 / 星宿28 / 节气24
//
// 关系算子 (身份互换):
//   公约数 = 中心 (正交点/静态不变), 公倍数 = 边界 (镜像对偶/曲线)
//   gcd(42,2760,60,12,28,24) = 2   → 全谱系共享中心 (阴阳对偶)
//   lcm(42,2760,60,12,28,24) = 19320 → 全谱系回归同一中心的周期
//   镜像对偶: 值 v 的镜像 = 进制-1-v (对称轴)
//
// 用法:
//   kan42 list               列出全部谱系与维度
//   kan42 find <谱系> <字>    任意谱系定位字 (color/yinyun/jiazi为便捷别名)
//   kan42 color <字>          颜色字→梯度系/行/列/值
//   kan42 yinyun <音节>       音节→(声母,韵母,声调)/值
//   kan42 jiazi <甲子>        甲子→(天干,地支)/值
//   kan42 xh <谱系> <值>      镜像对偶: 进制-1-值
//   kan42 gcd                全谱系最大公约数 (中心)
//   kan42 lcm                全谱系最小公倍数 (周期)
//   kan42 gd <谱系> <值>      梯度系归属查询

use std::collections::HashMap;
use std::env;
use std::fs;
use std::process;

// 谱系: (名称, 说明, 元素列表)
struct Spectrum {
    name: String,
    note: String,
    items: Vec<String>,
}

struct Kan42 {
    color_rows: Vec<Vec<String>>, // 6梯度系 × 7
    color_names: Vec<String>,
    sheng: Vec<String>,
    yun: Vec<String>,
    diao: Vec<String>,
    tian: Vec<String>,
    di: Vec<String>,
    extras: Vec<Spectrum>, // 生态谱系: 生肖/星宿/节气
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
        extras: Vec::new(),
    };
    let color_orders = ["红系", "黄系", "绿系", "蓝系", "泽系", "光系"];
    let extra_names = ["生肖", "星宿", "节气"];
    let mut color_map: HashMap<String, Vec<String>> = HashMap::new();
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
    for (i, n) in extra_names.iter().enumerate() {
        if let Some(v) = color_map.get(*n) {
            k.extras.push(Spectrum {
                name: n.to_string(),
                note: ["生物生态", "天文生态", "气候生态"][i].to_string(),
                items: v.clone(),
            });
        }
    }
    Ok(k)
}

fn gcd(a: u64, b: u64) -> u64 {
    if b == 0 { a } else { gcd(b, a % b) }
}

fn lcm(a: u64, b: u64) -> u64 {
    a / gcd(a, b) * b
}

// 全谱系进制列表: [(名称, 进制)]
fn all_bases(k: &Kan42) -> Vec<(&str, u64)> {
    let mut v: Vec<(&str, u64)> = vec![
        ("颜色", 42),
        ("音韵", (k.sheng.len() * k.yun.len() * k.diao.len()) as u64),
        ("时间", lcm(k.tian.len() as u64, k.di.len() as u64)),
    ];
    for e in &k.extras {
        v.push((e.name.as_str(), e.items.len() as u64));
    }
    v
}

// 定位一个字在任一谱系的位置 (颜色返回 梯度行*7+列; 其他返回索引)
fn find_spec(k: &Kan42, spec: &str, ch: &str) -> Option<(usize, u64, String)> {
    match spec {
        "颜色" => {
            for (i, (n, row)) in k.color_names.iter().zip(&k.color_rows).enumerate() {
                if let Some(c) = row.iter().position(|x| x == ch) {
                    return Some((i * 7 + c, 42, format!("行{}[{}] 列{}", i + 1, n, c + 1)));
                }
            }
            None
        }
        "音韵" => {
            let d1 = k.sheng.len();
            let d2 = k.yun.len();
            for (si, s) in k.sheng.iter().enumerate() {
                for (fi, f) in k.yun.iter().enumerate() {
                    for (di, d) in k.diao.iter().enumerate() {
                        if format!("{}{}{}", s, f, d) == ch {
                            let v = (si * d2 + fi) * k.diao.len() + di;
                            return Some((v, (d1 * d2 * k.diao.len()) as u64, format!("声母{} 韵母{} 声调{}", si, fi, di)));
                        }
                    }
                }
            }
            None
        }
        "时间" => {
            let t60 = lcm(k.tian.len() as u64, k.di.len() as u64);
            for (i, (t, d)) in k.tian.iter().zip(&k.di).enumerate() {
                let mut j = String::new();
                j.push_str(t);
                j.push_str(d);
                if j == ch {
                    return Some((i % 60, t60, format!("天干{} 地支{}", i % 10, i % 12)));
                }
            }
            None
        }
        _ => {
            for e in &k.extras {
                if e.name == spec {
                    if let Some(c) = e.items.iter().position(|x| x == ch) {
                        return Some((c, e.items.len() as u64, format!("{}·{}", e.note, c)));
                    }
                }
            }
            None
        }
    }
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
            let bases = all_bases(&k);
            println!("感知进制链 · 全量化辅助状态变化\n");
            for (name, base) in &bases {
                if *name == "颜色" {
                    println!("颜色谱系 {}进制 ({}梯度系 × 7色):", base, k.color_names.len());
                    for (i, (n, row)) in k.color_names.iter().zip(&k.color_rows).enumerate() {
                        println!("  行{} {}: {}", i + 1, n, row.join(" "));
                    }
                } else if *name == "音韵" {
                    println!("\n音韵谱系 {}进制 (声母{} × 韵母{} × 声调{}):", base, k.sheng.len(), k.yun.len(), k.diao.len());
                    println!("  声母: {}", k.sheng.join(" "));
                    println!("  韵母: {}", k.yun.join(" "));
                    println!("  声调: {}", k.diao.join(" "));
                } else if *name == "时间" {
                    println!("\n时间谱系 {}进制 (天干{} × 地支{} = {}甲子):", base, k.tian.len(), k.di.len(), base);
                    println!("  天干: {}", k.tian.join(" "));
                    println!("  地支: {}", k.di.join(" "));
                } else {
                    for e in &k.extras {
                        if e.name == *name {
                            println!("\n{}谱系 {}进制 ({}):", e.name, base, e.note);
                            println!("  {}: {}", e.name, e.items.join(" "));
                        }
                    }
                }
            }
            let g = bases.iter().skip(1).fold(bases[0].1, |acc, (_, b)| gcd(acc, *b));
            let l = bases.iter().skip(1).fold(bases[0].1, |acc, (_, b)| lcm(acc, *b));
            let names: Vec<String> = bases.iter().map(|(n, _)| n.to_string()).collect();
            let bases_s: Vec<String> = bases.iter().map(|(_, b)| b.to_string()).collect();
            println!("\n层级: 时间(窄/相位) 管 颜色(中) 管 音韵(宽) —— 加法管理乘法");
            println!("公约数(中心/正交点/静态不变) gcd({}) = {}", bases_s.join(","), g);
            println!("公倍数(边界/镜像对偶/周期) lcm({}) = {}", bases_s.join(","), l);
            println!("谱系: {} —— 身份互换: 任一字 ∈ 任一谱系, 均可换到另两谱系 (异置互换)", names.join("/"));
        }
        "find" => {
            let spec = args.get(1).map(|s| s.as_str()).unwrap_or("");
            let ch = args.get(2).map(|s| s.as_str()).unwrap_or("");
            if let Some((v, base, where_)) = find_spec(&k, spec, ch) {
                println!("{} ∈ {} = {} 值{} ({}进制)", ch, spec, where_, v, base);
            } else {
                println!("字 [{}] 不在 {} 谱系", ch, spec);
            }
        }
        "color" => {
            let ch = args.get(1).map(|s| s.as_str()).unwrap_or("");
            if let Some((v, base, where_)) = find_spec(&k, "颜色", ch) {
                println!("{} = {} 值{} ({}进制)", ch, where_, v, base);
                println!("  层级链: 时间(窄) ← 颜色(中) ← 音韵(宽)");
            } else {
                println!("字 [{}] 不在颜色谱系", ch);
            }
        }
        "yinyun" => {
            let s = args.get(1).map(|s| s.as_str()).unwrap_or("");
            if let Some((v, base, where_)) = find_spec(&k, "音韵", s) {
                println!("音节 {} → {} 值{} ({}进制)", s, where_, v, base);
            } else {
                println!("音节 [{}] 无法解析", s);
            }
        }
        "jiazi" => {
            let s = args.get(1).map(|s| s.as_str()).unwrap_or("");
            let t60 = lcm(k.tian.len() as u64, k.di.len() as u64);
            for (i, (t, d)) in k.tian.iter().zip(&k.di).enumerate() {
                let mut jia = String::new();
                jia.push_str(t);
                jia.push_str(d);
                if jia == s {
                    println!("{} = 天干{} 地支{} 值{} ({}甲子)", s, i % 10, i % 12, i % 60, t60);
                    return;
                }
            }
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
            let spec = args.get(1).map(|s| s.as_str()).unwrap_or("颜色");
            let v: u64 = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(0);
            let base: u64 = match spec {
                "颜色" => 42,
                "音韵" => (k.sheng.len() * k.yun.len() * k.diao.len()) as u64,
                "时间" => lcm(k.tian.len() as u64, k.di.len() as u64),
                _ => {
                    k.extras.iter().find(|e| e.name == spec).map(|e| e.items.len() as u64).unwrap_or(42)
                }
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
            let bases = all_bases(&k);
            let g = bases.iter().skip(1).fold(bases[0].1, |acc, (_, b)| gcd(acc, *b));
            let bases_s: Vec<String> = bases.iter().map(|(_, b)| b.to_string()).collect();
            println!("公约数(中心/正交点/静态不变)");
            println!("  gcd({}) = {}", bases_s.join(","), g);
            println!("  中心男人=公约数, 静态固化不变; 所有公倍数受其管辖");
        }
        "lcm" => {
            let bases = all_bases(&k);
            let l = bases.iter().skip(1).fold(bases[0].1, |acc, (_, b)| lcm(acc, *b));
            let bases_s: Vec<String> = bases.iter().map(|(_, b)| b.to_string()).collect();
            println!("公倍数(边界/镜像对偶/全周期)");
            println!("  lcm({}) = {}", bases_s.join(","), l);
            println!("  边界女人=公倍数, 包裹中心; 全谱系回归同一中心的周期");
        }
        "gd" => {
            let spec = args.get(1).map(|s| s.as_str()).unwrap_or("颜色");
            let v: u64 = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(0);
            let base = match spec {
                "颜色" => 42,
                "时间" => lcm(k.tian.len() as u64, k.di.len() as u64),
                _ => k.extras.iter().find(|e| e.name == spec).map(|e| e.items.len() as u64).unwrap_or(0),
            };
            if base == 0 || v >= base {
                println!("gd 越界或谱系不存在: {} 进制{}", spec, base);
                return;
            }
            if spec == "颜色" {
                let (row, col) = ((v / 7) as usize, (v % 7) as usize);
                println!("值{} → 行{}[{}] 列{} {}", v, row + 1, k.color_names[row], col + 1, k.color_rows[row][col]);
            } else if spec == "时间" {
                let t = &k.tian[(v % 10) as usize];
                let d = &k.di[(v % 12) as usize];
                println!("值{} → 甲子 {}{}", v, t, d);
            } else {
                let e = k.extras.iter().find(|e| e.name == spec).unwrap();
                println!("值{} → {}·{} {}", v, e.name, v + 1, e.items[v as usize]);
            }
        }
        other => println!("未知命令: {} (可用: list/find/color/yinyun/jiazi/xh/gcd/lcm/gd)", other),
    }
}
