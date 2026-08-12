# fus_rs - 智能共同体协议融合网关（Rust 核心）

与 `fus/fusion.py` 同功能，但用 **Rust 零依赖核心** 实现：
编译为单二进制，无运行时、无 GC、可嵌入低资源环境（MCU/FPGA/嵌入式）。

## 为什么是 Rust

| 对比 | Rust 版 | Python 版 |
|---|---|---|
| 产物 | 单二进制（strip 后约 375K） | 解释器 + 依赖 |
| 运行时 | 无 | CPython 解释器 |
| GC | 无 | 无（Python 自身有 GC） |
| 启动 | 微秒级 | 百毫秒级 |
| 可嵌入 | 可 | 难 |

## 编译

```bash
cd fus_rs && cargo build --release
./target/release/fusion --list
```

无需网络依赖（零 crate），Rust 标准库即可编译。

## 使用

```bash
./target/release/fusion --list                          # 列出协议族
./target/release/fusion http://example.com              # HTTP 抓取
./target/release/fusion https://example.com             # HTTPS（需 TLS 库，见下）
./target/release/fusion tcp://host:port                 # TCP 连接探测
./target/release/fusion gtt://x                          # gttx 家族识别
./target/release/fusion gittx://x                        # gittx 变体识别
./target/release/fusion 裸地址.com/a                     # 裸地址自动补 https
```

## 协议边界

- **HTTP / TCP / UDP**：Rust 标准库直接支持（本实现已内置）
- **HTTPS / FTP**：需要 TLS/FTPS 库（如 rustls/openssl）。零依赖设计下
  本核心保留为识别 + 路由层，抓取能力交由 `fus/fusion.py`（Python 标准库
  自带 urllib TLS）。这正是"核心低开销、工具补能力"的分工。

## 分层

| 层 | 实现 | 职责 |
|---|---|---|
| 核心 | `fus_rs`（Rust） | 协议识别、路由、TCP/HTTP 低开销处理 |
| 能力 | `fus/fusion.py`（Python） | TLS 抓取、gttx 共同体分发、转换 |
