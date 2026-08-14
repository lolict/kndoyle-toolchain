// cmdenv - 沙箱模拟指令环境 (Rust 零依赖)
//
// 为仓库提供完整指令环境: 协议/感知/角色/执行/时间/关系/进制 六类指令
// 规则即数据: 指令定义在 rules/cmd.chain, 缺什么指令就补什么指令
// 沙箱模式: 静态符号化执行, 无需外部工具, 自身就是一个"最小指令系统"
//
// 用法:
//   cmdenv list                 列出全部指令
//   cmdenv <指令> [参数...]      执行指令
//   cmdenv help <指令>          查看指令说明
//   cmdenv state <状态>         设置运行状态 (待机/否极泰来/合一爱人)
//   cmdenv run <链> <输入>      执行管线 (概念演示)

use std::env;
use std::fs;
use std::process;

struct Cmd {
    name: String,
    cat: String,
    argc: usize,
    desc: String,
}

fn rules_path() -> String {
    for c in ["cmdenv/rules/cmd.chain", "rules/cmd.chain"] {
        if std::path::Path::new(c).exists() {
            return c.to_string();
        }
    }
    "cmdenv/rules/cmd.chain".to_string()
}

fn load(path: &str) -> Result<Vec<Cmd>, String> {
    let content = fs::read_to_string(path).map_err(|e| format!("指令表读取失败: {}", e))?;
    let mut cmds = Vec::new();
    for line in content.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let parts: Vec<&str> = line.split('|').map(|s| s.trim()).collect();
        if parts.len() < 4 {
            continue;
        }
        cmds.push(Cmd {
            name: parts[0].to_string(),
            cat: parts[1].to_string(),
            argc: parts[2].parse().unwrap_or(0),
            desc: parts[3].to_string(),
        });
    }
    Ok(cmds)
}

fn gcd(a: u64, b: u64) -> u64 {
    if b == 0 { a } else { gcd(b, a % b) }
}

fn lcm(a: u64, b: u64) -> u64 {
    a / gcd(a, b) * b
}

const COLOR_TABLE: [&str; 42] = [
    "妃","粉","彤","赤","棕","绛","赭", // 红系
    "缃","金","黄","褐","黧","乌","黑", // 黄系
    "缥","翠","绿","青","苍","黛","玄", // 绿系
    "素","银","蓝","紫","靛","绀","黯", // 蓝系
    "玉","琅","晶","璃","珀","瑙","璧", // 泽系
    "曦","辉","霓","旖","靡","暝","黟", // 光系
];

fn qe(v: u64) -> String {
    let (a, b, c) = (v % 42, (v / 42) % 42, (v / (42 * 42)) % 42);
    format!("{}{}{}", COLOR_TABLE[c as usize], COLOR_TABLE[b as usize], COLOR_TABLE[a as usize])
}

fn qd(s: &str) -> Option<u64> {
    let cs: Vec<char> = s.chars().collect();
    if cs.len() != 3 {
        return None;
    }
    let mut v = 0u64;
    for ch in cs {
        let i = COLOR_TABLE.iter().position(|&x| x == ch.to_string())? as u64;
        v = v * 42 + i;
    }
    Some(v)
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    let cmds = load(&rules_path()).unwrap_or_else(|e| {
        println!("错误: {}", e);
        process::exit(1);
    });
    let cmd = args.first().map(|s| s.as_str()).unwrap_or("list");

    match cmd {
        "list" | "-l" => {
            println!("沙箱模拟指令环境 · 六类指令 (规则即数据)\n");
            for cat in ["协议", "感知", "角色", "执行", "时间", "关系", "进制"] {
                let list: Vec<&Cmd> = cmds.iter().filter(|c| c.cat == cat).collect();
                if list.is_empty() {
                    continue;
                }
                println!("【{}层】", cat);
                for c in list {
                    println!("  {} {}  -- {}", c.name, "·".repeat(c.argc.saturating_add(1)), c.desc);
                }
            }
        }
        "help" => {
            let name = args.get(1).map(|s| s.as_str()).unwrap_or("");
            if let Some(c) = cmds.iter().find(|c| c.name == name) {
                println!("[{}] {} | {} | 参数数{}", c.name, c.cat, c.desc, c.argc);
            } else {
                println!("未知指令: {}", name);
            }
        }
        "qe" => {
            let v: u64 = args.get(1).and_then(|s| s.parse().ok()).unwrap_or(0);
            println!("{} → {}", v, qe(v));
        }
        "qd" => {
            let s = args.get(1).map(|s| s.as_str()).unwrap_or("");
            match qd(s) {
                Some(v) => println!("{} → {}", s, v),
                None => println!("解码失败: 需要3个颜色字"),
            }
        }
        "gcd" => {
            let a: u64 = args.get(1).and_then(|s| s.parse().ok()).unwrap_or(0);
            let b: u64 = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(0);
            println!("公约数(中心男人/静态) gcd({},{}) = {}", a, b, gcd(a, b));
        }
        "lcm" => {
            let a: u64 = args.get(1).and_then(|s| s.parse().ok()).unwrap_or(0);
            let b: u64 = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(0);
            println!("公倍数(边界女人/周期) lcm({},{}) = {}", a, b, lcm(a, b));
        }
        "mirror" => {
            let base: u64 = args.get(1).and_then(|s| s.parse().ok()).unwrap_or(42);
            let v: u64 = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(0);
            if v < base {
                let m = base - 1 - v;
                println!("镜像对偶 {}进制: {} ↔ {} (对称轴 {})", base, v, m, (base - 1) as f64 / 2.0);
            } else {
                println!("值越界");
            }
        }
        "add" | "mul" => {
            let a: i64 = args.get(1).and_then(|s| s.parse().ok()).unwrap_or(0);
            let b: i64 = args.get(2).and_then(|s| s.parse().ok()).unwrap_or(0);
            if cmd == "add" {
                println!("加法(窄·管乘法) {} + {} = {}", a, b, a + b);
            } else {
                println!("乘法(宽·被管) {} × {} = {}", a, b, a * b);
            }
        }
        "state" => {
            let s = args.get(1).map(|s| s.as_str()).unwrap_or("待机");
            let states = ["待机", "否极泰来", "合一爱人"];
            if states.contains(&s) {
                println!("系统状态 → {}", s);
            } else {
                println!("未知状态: {} (可用: 待机/否极泰来/合一爱人)", s);
            }
        }
        "tclgs" => {
            let op = args.get(1).map(|s| s.as_str()).unwrap_or("life");
            let v = args.get(2).map(|s| s.as_str()).unwrap_or("编码");
            match op {
                "gen" => println!("时间编码生命周期 · 生成 {} (起始相位)", v),
                "expire" => println!("时间编码生命周期 · {} 过期 → 转化", v),
                "fold" => println!("时间编码生命周期 · {} 折叠 → 回归中心一", v),
                _ => println!("tclgs 时间功法: gen生成/expire过期/fold折叠 (归宿=回归一)"),
            }
        }
        "juan" => {
            let p = args.get(1).map(|s| s.as_str()).unwrap_or("时间");
            println!("{} 相位颠倒 → 空间 (毛利兰 · 空间管理镜像)", p);
        }
        "time" => {
            println!("当前时间周期: 以 tclgs 为相位, 所有编码回归中心一");
        }
        "run" => {
            let chain = args.get(1).map(|s| s.as_str()).unwrap_or("");
            let input = args.get(2).map(|s| s.as_str()).unwrap_or("");
            println!("执行管线: run {} {}", chain, input);
            println!("  协议层 gttx:// 寻址 → 感知层 gkndl 转化 → 角色层 归属判定 → 关系层 公约数归集");
            println!("  结果: 所有公倍数尘埃落定 → 回归中心一");
        }
        "ping" => {
            println!("沙箱指令环境在线");
        }
        _ => {
            if let Some(c) = cmds.iter().find(|c| c.name == cmd) {
                println!("[{}] {}: {}", c.name, c.cat, c.desc);
                println!("  (参数数 {})", c.argc);
            } else {
                println!("未知指令: {} (可用 list 查看全部, 缺指令就在 rules/cmd.chain 加一行)", cmd);
            }
        }
    }
}
