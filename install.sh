#!/bin/bash
# install.sh - 一条命令寄生安装 gttx 工具链
#
# 用法 (在别人的服务器上执行):
#   curl -sSL https://gitee.com/lolict/kndoyle-toolchain/raw/master/install.sh | bash
#
# 或本地执行:
#   bash install.sh [目标目录]
#
# 做什么:
#   1. 克隆工具链仓库 (默认 gitee, 失败自动切 github/gitcode 镜像)
#   2. 编译 Rust 核心 (color42_rs / chain_rs / fus_rs), 无 cargo 则跳过
#   3. 启动 web 显示链服务 (python3 http.server)
#   4. 打印访问地址与自检结果

set -e

MIRRORS=(
    "https://gitee.com/lolict/kndoyle-toolchain.git"
    "https://github.com/lolict/kndoyle-toolchain.git"
    "https://gitcode.com/lolict/kndoyle-toolchain.git"
)
DEST="${1:-$HOME/gttx-toolchain}"
PORT="${PORT:-8000}"

echo "== gttx 工具链安装器 =="
echo "目标目录: $DEST"

# 依赖检查
have() { command -v "$1" >/dev/null 2>&1; }

if have git && [ ! -d "$DEST/.git" ]; then
    echo "[1/4] 克隆仓库..."
    for m in "${MIRRORS[@]}"; do
        echo "  尝试: $m"
        if git clone --depth 1 "$m" "$DEST" 2>/dev/null; then
            echo "  成功: $m"
            break
        fi
    done
    [ -d "$DEST/.git" ] || { echo "✗ 所有镜像克隆失败, 请检查网络或手动上传仓库到 $DEST"; exit 1; }
elif [ -d "$DEST/.git" ]; then
    echo "[1/4] 目录已存在, 拉取更新..."
    git -C "$DEST" pull --rebase 2>/dev/null || true
else
    echo "✗ 缺少 git 且目录不存在, 请先安装 git 或手动上传仓库"
    exit 1
fi

cd "$DEST"

# 编译 Rust 核心
echo "[2/4] 编译 Rust 核心..."
if have cargo; then
    for d in color42_rs chain_rs fus_rs; do
        if [ -f "$d/Cargo.toml" ]; then
            echo "  build: $d"
            (cd "$d" && cargo build --release 2>/dev/null || echo "  ! $d 编译失败(继续)")
        fi
    done
else
    echo "  ! 未检测到 cargo, 跳过 Rust 核心编译 (仅提供 web 静态显示链)"
fi

# 自检: 二进制可执行
echo "[3/4] 自检..."
if [ -x "color42_rs/target/release/color42" ]; then
    echo "  color42 核心: OK  ($("color42_rs/target/release/color42" e 100 颜色 3))"
else
    echo "  color42 核心: 未编译 (可用 cargo 编译)"
fi
if [ -x "chain_rs/target/release/chain" ]; then
    echo "  chain 调度器: OK"
else
    echo "  chain 调度器: 未编译"
fi
if [ -d "web" ] && [ -f "web/index.html" ]; then
    echo "  web 显示链: OK (浏览器端运行时, 零服务器解析)"
else
    echo "  ✗ web 目录缺失"
fi

# 启动 web 服务
echo "[4/4] 启动显示链服务 端口 $PORT..."
if have python3; then
    cd "$DEST/web"
    nohup python3 -m http.server "$PORT" >"$DEST/web/server.log" 2>&1 &
    echo "  已启动 (PID $!)"
    echo ""
    echo "== 完成 =="
    echo "  访问: http://<服务器IP>:$PORT  (浏览器自己解析我们的标签, 服务器只传文件)"
    echo "  日志: $DEST/web/server.log"
    echo "  停止: kill $(pgrep -f "http.server $PORT" | head -1)"
    echo "  根 URI: lctfqimiygttx://hieyair"
else
    echo "  ✗ 缺少 python3, 无法启动 web 服务 (可手动把 web/ 托管到任意静态服务器)"
fi
