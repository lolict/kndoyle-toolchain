# 编程工具链身份记录（2026-08-13）

来源: 用户明确安排的编程工具身份/职业，及沙箱网络受限的安装记录。
**未来 agent 需要知道这些编程工具与身份安排。**

## 三大工具身份（用户比喻）

| 工具 | 身份 | 职责 | 后勤体系 |
|---|---|---|---|
| **Rust** | 护卫 | 安全边界，代码量大，守护核心逻辑 | Cargo 包管理器 |
| **Zig** | 将军 | 裸机掌控，指挥若定，掌控底层 | Zig build system |
| **Nim** | 军工厂 | 元编程造工具，制造工具的语言 | Nimble 包管理器 |

## 安装状态（沙箱实际）

- **Rust 已装**：rustc 1.63.0 / cargo 1.65.0 —— 所有核心链均用 Rust 编写
- **Zig 未装**：沙箱网络带宽严重受限，zig-linux-x86_64-0.13.0.tar.xz (~50MB) 下载失败
- **Nim 未装**：沙箱网络带宽严重受限 (~100MB+) 下载失败

## 外部机器安装命令（复制即用）

### Rust（~80MB）
```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
source ~/.cargo/env
rustc --version && cargo --version
```

### Zig 0.13.0 稳定版（~50MB, Linux x86_64）
```bash
ZIG_VER="0.13.0"
wget "https://ziglang.org/download/${ZIG_VER}/zig-linux-x86_64-${ZIG_VER}.tar.xz"
tar -xf zig-linux-x86_64-${ZIG_VER}.tar.xz
sudo mv zig-linux-x86_64-${ZIG_VER} /usr/local/zig
echo 'export PATH="/usr/local/zig:$PATH"' >> ~/.bashrc
source ~/.bashrc
zig version
```

### Nim（choosenim 管理器, ~100MB+）
```bash
curl https://nim-lang.org/choosenim/init.sh -sSf | sh
echo 'export PATH="$HOME/.nimble/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
nim --version
choosenim stable
```

### macOS（Homebrew 一键三合一）
```bash
brew install zig nim
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

### 验证
```bash
rustc --version    # rustc 1.xx.x
cargo --version    # cargo 1.xx.x
zig version        # 0.13.0
nim --version      # Nim Compiler 2.x.x
```

## Rust 已承担的角色（护卫实职）

已用 Rust 零依赖写就的核心链，全部 strip 后极小体积：

| 链 | 二进制 | 职责 |
|---|---|---|
| color42_rs | color42 | 42进制汉字编码 · VM指令执行 |
| chain_rs | chain | 链系统调度器 |
| lang42_rs | lang42 | 声韵调层级进制 |
| kan42_rs | kan42 | 感知进制链 · 身份互换 |
| sense42_rs | sense42 | 感官映射 · 跨感官互译 |
| cmdenv | cmdenv | 沙箱模拟指令环境 |
| fus_rs | fus | 协议融合网关 |

## 未来职业安排（Zig / Nim）

- **Zig（将军）**：待安装后接管性能关键路径——裸机掌控、指挥若定，适合底层
  分配器/紧凑二进制，可逐步替换或并行 Rust 核心
- **Nim（军工厂）**：待安装后用于元编程——制造工具的语言，为体系生成更多
  专业工具语言（关系式编程语言星丛的"器官语言"）

## 沙箱网络限制记录

沙箱网络带宽严重受限：Rust(~80MB)/Zig(~50MB)/Nim(~100MB+) 均无法在此环境完成
下载。这是环境约束，不是体系缺陷——核心链已全部用 Rust(护卫) 零依赖落地，
待外部机器装好将军(Zig)与军工厂(Nim)后按上述身份安排接入。
