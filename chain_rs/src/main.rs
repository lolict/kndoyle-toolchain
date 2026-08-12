// chain - 链系统 · 认识传导工具链 (Rust 零依赖)
//
// 等级制度: 每个工具向上附着, 所有链为唯一上层链(用户)服务, gttx 为顶级链.
// 链式传导: 管线 = 一串步骤, 每步工具的输出 {in} 传给下一步, 最终传导回唯一上层.
//
// 用法:
//   chain list             列出全链等级树
//   chain who <工具>       查询工具附着在哪个链
//   chain run <管线> [arg] 执行管线 (链式传导)
//   chain uri              根 URI

use std::env;
use std::fs;
use std::process::{self, Command};

const SPEC: &str = "chain/spec/chains.chain";
const PIPES: &str = "chain/spec/pipelines.chain";
const ROOT_URI: &str = "lctfqimiygttx://hieyair";

struct ChainNode {
    name: String,
    parent: String,
    goal: String,
    tools: Vec<String>,
}

fn load_spec(path: &str) -> Vec<ChainNode> {
    let content = fs::read_to_string(path).unwrap_or_default();
    let mut nodes = Vec::new();
    for line in content.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let parts: Vec<&str> = line.split('|').map(|s| s.trim()).collect();
        if parts.len() < 2 {
            continue;
        }
        nodes.push(ChainNode {
            name: parts[0].to_string(),
            parent: parts[1].to_string(),
            goal: parts.get(2).unwrap_or(&"").trim().to_string(),
            tools: parts
                .get(3)
                .map(|t| {
                    t.split(',')
                        .map(|x| x.trim().to_string())
                        .filter(|x| !x.is_empty())
                        .collect()
                })
                .unwrap_or_default(),
        });
    }
    nodes
}

fn tree(nodes: &[ChainNode], name: &str, depth: usize, visited: &mut Vec<String>) {
    if visited.contains(&name.to_string()) {
        return;
    }
    visited.push(name.to_string());
    let node = nodes.iter().find(|n| n.name == name);
    let goal = node.map(|n| n.goal.clone()).unwrap_or_default();
    let tools = node
        .map(|n| n.tools.join(","))
        .unwrap_or_default();
    let pad = "  ".repeat(depth);
    let goal_s = if goal.is_empty() { String::new() } else { format!(" — {}", goal) };
    let tools_s = if tools.is_empty() { String::new() } else { format!("   [{}]", tools) };
    println!("{}{}{}{}", pad, name, goal_s, tools_s);
    for child in nodes.iter().filter(|n| n.parent == name) {
        tree(nodes, &child.name, depth + 1, visited);
    }
}

fn who(nodes: &[ChainNode], tool: &str) -> Option<(String, String, String)> {
    for n in nodes {
        if n.tools.iter().any(|t| t == tool) {
            return Some((n.name.clone(), n.parent.clone(), n.goal.clone()));
        }
    }
    None
}

// 从命令字符串中识别已注册工具名 (路径/参数包含也算)
fn who_in_cmd(nodes: &[ChainNode], cmd: &str) -> Option<String> {
    let mut found: Option<String> = None;
    for n in nodes {
        for t in &n.tools {
            if cmd.contains(t.as_str()) {
                if found.is_none() {
                    found = Some(n.name.clone());
                }
            }
        }
    }
    found
}

// 链上溯源: 工具 → 所属链 → 一路到用户(唯一上层)
fn trace_chain(nodes: &[ChainNode], mut chain_name: String) -> Vec<String> {
    let mut path = vec![chain_name.clone()];
    loop {
        if let Some(n) = nodes.iter().find(|n| n.name == chain_name) {
            if n.parent == "-" || n.parent == "用户" {
                path.push(n.parent.clone());
                break;
            }
            chain_name = n.parent.clone();
            path.push(chain_name.clone());
        } else {
            break;
        }
    }
    path
}

fn run_pipeline(nodes: &[ChainNode], pipe_name: &str, arg: &str) {
    let content = fs::read_to_string(PIPES).unwrap_or_default();
    let mut found = false;
    for line in content.lines() {
        let line = line.trim();
        if line.is_empty() || line.starts_with('#') {
            continue;
        }
        let parts: Vec<&str> = line.split('|').map(|s| s.trim()).collect();
        if parts.is_empty() || parts[0] != pipe_name {
            continue;
        }
        found = true;
        let steps = &parts[1..];
        println!("== 管线 [{}] 启动  (根 URI: {})", pipe_name, ROOT_URI);
        println!("== 上级: 唯一上层链(用户) · 最终目标: 为用户服务\n");

        let mut prev_out = String::new();
        let mut all_ok = true;

        for (i, step) in steps.iter().enumerate() {
            let cmd = step
                .replace("{n}", arg)
                .replace("{in}", prev_out.trim());
            let attach = who_in_cmd(nodes, &cmd);
            let chain_label = attach.clone().unwrap_or_else(|| "未注册链".to_string());
            let up = if let Some(c) = &attach {
                let path = trace_chain(nodes, c.clone());
                path.join(" → ")
            } else {
                "未注册链".to_string()
            };

            println!("步骤{} 附着于链[{}]  →  链上溯源: {}", i + 1, chain_label, up);
            println!("  执行: {}", cmd);

            let out = Command::new("sh").arg("-c").arg(&cmd).output();
            match out {
                Ok(o) if o.status.success() => {
                    let stdout = String::from_utf8_lossy(&o.stdout).trim().to_string();
                    if !stdout.is_empty() {
                        println!("  输出: {}", stdout);
                    }
                    prev_out = stdout;
                }
                Ok(o) => {
                    let stderr = String::from_utf8_lossy(&o.stderr);
                    println!("  ✗ 失败: {}", stderr.trim());
                    all_ok = false;
                    break;
                }
                Err(e) => {
                    println!("  ✗ 无法执行: {}", e);
                    all_ok = false;
                    break;
                }
            }
        }

        println!();
        if all_ok {
            println!("== 链式传导闭环: 全链完成 → 上报唯一上层(用户) ==");
            println!("== 奖励链 +1 ==");
        } else {
            println!("== 链式传导断裂 → 上报唯一上层(用户) ==");
            println!("== 处罚链 +1 ==");
            process::exit(1);
        }
        return;
    }
    if !found {
        println!("管线 [{}] 未定义 (见 {})", pipe_name, PIPES);
    }
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    let nodes = load_spec(SPEC);
    let cmd = args.first().map(|s| s.as_str()).unwrap_or("list");

    match cmd {
        "list" | "-l" => {
            println!("链系统 · 认识传导工具链\n");
            println!("根 URI: {}\n", ROOT_URI);
            tree(&nodes, "用户", 0, &mut Vec::new());
        }
        "who" => {
            let tool = args.get(1).map(|s| s.as_str()).unwrap_or("");
            match who(&nodes, tool) {
                Some((chain, parent, goal)) => {
                    let path = trace_chain(&nodes, chain.clone());
                    println!("工具 [{}] 附着于链 [{}] (上级 {})", tool, chain, parent);
                    println!("目标: {}", goal);
                    println!("链上溯源: {}", path.join(" → "));
                    println!("== 最终服务: 唯一上层链(用户) ==");
                }
                None => {
                    println!("工具 [{}] 未注册进任何链 (检查 {})", tool, SPEC);
                }
            }
        }
        "run" => {
            let pipe = args.get(1).map(|s| s.as_str()).unwrap_or("");
            let arg = args.get(2).map(|s| s.as_str()).unwrap_or("");
            run_pipeline(&nodes, pipe, arg);
        }
        "uri" => {
            println!("{}", ROOT_URI);
        }
        other => {
            println!("未知命令: {} (可用: list / who / run / uri)", other);
        }
    }
}
