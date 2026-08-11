#!/bin/bash
# pull.sh - 按需索取：只拉其他仓库里缺的重要功能，不整仓搬运
# 用法: bash pull.sh <仓库名> <路径...>
#   例: bash pull.sh yuan-ji-jiu-can hunyuan-rs        # 拉满全法OS的Rust实现
#        bash pull.sh relational-algebra relational_algebra  # 拉关系代数核心
#        bash pull.sh Unicore src examples              # 拉指令集源码与示例
# 产物: vendor/<仓库名>/<路径...>  +  vendor/<仓库名>/SOURCE.md 标注来源
# 原则: 独立目录、来源可辨、按需拉取，绝不混合搅拌。

set -euo pipefail
cd "$(dirname "$0")"

# 已知仓库注册表（名称 → 远程地址 + 分支）
declare -A REPO_URL=(
  [yuan-ji-jiu-can]="https://github.com/lolict/yuan-ji-jiu-can.git"
  [relational-algebra]="https://github.com/lolict/relational-algebra.git"
  [Unicore]="https://github.com/lolict/Unicore.git"
)

NAME="${1:?用法: bash pull.sh <仓库名> <路径...>}"
shift || true
[ $# -eq 0 ] && { echo "错误: 至少指定一个要拉取的路径"; exit 1; }

URL="${REPO_URL[$NAME]:-}"
if [ -z "$URL" ]; then
    echo "错误: 未知仓库 '$NAME'。已知: ${!REPO_URL[@]}"
    exit 1
fi

TMP="/tmp/opencode/pullsrc"
rm -rf "$TMP"
git clone --depth 1 --filter=blob:none --sparse "$URL" "$TMP" 2>/dev/null

# 稀疏检出指定路径
( cd "$TMP" && git sparse-checkout set --no-cone "${@}" )

DST="vendor/$NAME"
rm -rf "$DST"
mkdir -p "$DST"

# 拉取每个路径
MISSING=0
for p in "$@"; do
    if [ -e "$TMP/$p" ]; then
        mkdir -p "$DST/$(dirname "$p")"
        cp -r "$TMP/$p" "$DST/$p"
        echo "  已拉取: $p"
    else
        echo "  警告: 路径不存在: $p"
        MISSING=1
    fi
done

# 移除符号链接（指向本机系统库/绝对路径，不可分发，非源码）
find "$DST" -type l -delete

[ $MISSING -eq 1 ] && { echo "存在缺失路径，请核对后重试"; exit 1; }

# 记录来源（仓库 / commit / 日期）
COMMIT=$(git -C "$TMP" rev-parse HEAD)
{
    echo "# SOURCE - 本目录内容来源"
    echo
    echo "来源仓库: $NAME"
    echo "远程地址: $URL"
    echo "commit:   $COMMIT"
    echo "拉取时间: $(date +%F)"
    echo "拉取路径:"
    for p in "$@"; do echo "  - $p"; done
    echo
    echo "说明: 按需索取的功能代码，保持独立目录，不混入主仓库其他内容。"
} > "$DST/SOURCE.md"

rm -rf "$TMP"
echo "==> 完成: vendor/$NAME/  (来源已记录在 SOURCE.md)"
