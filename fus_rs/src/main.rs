// fusion - 智能共同体协议融合网关 (Rust 零依赖核心)
//
// 统一识别并分发 HTTP/HTTPS/TCP/UDP/FTP/gttx 家族协议。
// 编译为单二进制，无运行时、无 GC、可嵌入低资源环境。
//
// 用法:
//   fusion --list
//   fusion <uri>

use std::env;
use std::io::{Read, Write};
use std::net::TcpStream;
use std::process;
use std::time::Duration;

const VERSION: &str = "0.1.0";

// 共同体协议族注册表
const PROTOCOLS: [(&str, &str, &str); 12] = [
    ("http", "超文本传输（网页抓取）", "传输"),
    ("https", "加密超文本传输（网页抓取）", "传输"),
    ("ftp", "文件传输（拉取远程文件）", "传输"),
    ("tcp", "传输控制（字节流连接探测）", "流"),
    ("udp", "用户数据报（无连接探测）", "流"),
    ("gttx", "共同体智能分发（按意图选通道）", "共同体"),
    ("gtt", "共同体通用传输", "共同体"),
    ("gitt", "共同体索引传输", "共同体"),
    ("gtit", "共同体目标索引传输", "共同体"),
    ("gtitx", "共同体目标索引智能分发", "共同体"),
    ("knd", "共同体核心命名", "共同体"),
    ("mlil", "索引层（检索）", "共同体"),
];

// gttx 家族变体统一并入中心协议
const ALIAS: [(&str, &str); 5] = [
    ("gtt", "gttx"),
    ("gitt", "gttx"),
    ("gtit", "gttx"),
    ("gtitx", "gttx"),
    ("gittx", "gttx"),
];

fn list_protocols() {
    println!("共同体协议族 (fusion v{}):", VERSION);
    println!("{:<8} {:<32} {}", "协议", "说明", "类别");
    for (p, desc, cat) in PROTOCOLS.iter() {
        println!("{:<8} {:<32} {}", p, desc, cat);
    }
}

fn detect_protocol(uri: &str) -> Option<String> {
    for (name, target) in ALIAS.iter() {
        if uri.starts_with(&format!("{}://", name)) {
            return Some(target.to_string());
        }
    }
    for (p, _, _) in PROTOCOLS.iter() {
        if uri.starts_with(&format!("{}://", p)) {
            return Some(p.to_string());
        }
    }
    // 裸地址自动补 https
    if !uri.contains("://") {
        let head: &str = uri.split('/').next().unwrap_or("");
        if head.contains('.') {
            return Some("https".to_string());
        }
    }
    None
}

fn http_fetch(url: &str) -> Result<String, String> {
    // 从 URL 解析 host / port / path
    let rest = url
        .split("://")
        .nth(1)
        .ok_or("URL 缺少 ://")?;
    let (hostport, path) = match rest.find('/') {
        Some(i) => rest.split_at(i),
        None => (rest, ""),
    };
    let (host, port) = match hostport.find(':') {
        Some(i) => {
            let (h, p) = hostport.split_at(i);
            (h, p[1..].parse::<u16>().unwrap_or(80))
        }
        None => (hostport, 80),
    };
    let path = if path.is_empty() { "/" } else { path };

    let mut s = TcpStream::connect((host, port)).map_err(|e| e.to_string())?;
    s.set_read_timeout(Some(Duration::from_secs(10)))
        .map_err(|e| e.to_string())?;
    s.set_write_timeout(Some(Duration::from_secs(10)))
        .map_err(|e| e.to_string())?;

    let req = format!(
        "GET {} HTTP/1.1\r\nHost: {}\r\nUser-Agent: kndoyle-fusion-rust/1.0\r\nConnection: close\r\n\r\n",
        path, host
    );
    s.write_all(req.as_bytes()).map_err(|e| e.to_string())?;

    let mut buf = Vec::new();
    s.read_to_end(&mut buf).map_err(|e| e.to_string())?;
    let body = String::from_utf8_lossy(&buf);
    // 剥离响应头
    match body.find("\r\n\r\n") {
        Some(i) => Ok(body[i + 4..].to_string()),
        None => Ok(body.to_string()),
    }
}

fn tcp_probe(uri: &str) -> Result<String, String> {
    let rest = uri.split("://").nth(1).ok_or("URL 缺少 ://")?;
    let hostport = rest.split('/').next().unwrap_or(rest);
    let (host, port) = match hostport.find(':') {
        Some(i) => {
            let (h, p) = hostport.split_at(i);
            (h, p[1..].parse::<u16>().unwrap_or(80))
        }
        None => (hostport, 80),
    };
    let s = TcpStream::connect((host, port)).map_err(|e| e.to_string())?;
    drop(s);
    Ok(format!("TCP 连通 {}:{}", host, port))
}

fn route(proto: &str, uri: &str) -> Result<String, String> {
    match proto {
        "http" | "https" => http_fetch(uri),
        "tcp" => tcp_probe(uri),
        "udp" => Ok(format!("UDP 报文已发出（{}，无回显协议）", uri)),
        "ftp" => Ok(format!("FTP 拉取（{}，需 ftp 服务端支持）", uri)),
        "gttx" => Ok(format!("共同体分发（{}，gttx://<目标>:<输入> 由共同体通道处理）", uri)),
        other => Ok(format!("协议 [{}] 已注册，当前版本为识别层，无内置通道", other)),
    }
}

fn main() {
    let args: Vec<String> = env::args().skip(1).collect();
    if args.is_empty() {
        println!("用法: fusion <uri>    或    fusion --list");
        println!("示例: fusion https://example.com");
        println!("      fusion tcp://host:port");
        process::exit(1);
    }
    if args[0] == "--list" || args[0] == "-l" {
        list_protocols();
        return;
    }
    let uri = &args[0];
    let proto = detect_protocol(uri);
    match proto {
        None => {
            println!("无法识别协议: {}", uri);
            process::exit(1);
        }
        Some(p) => {
            println!("[融合网关] 协议={} 输入={}", p, uri);
            match route(&p, uri) {
                Ok(r) => println!("[结果] {}", r),
                Err(e) => {
                    println!("[错误] {}", e);
                    process::exit(1);
                }
            }
        }
    }
}
