#!/bin/bash
# package.sh - 从主仓库打包成一个自包含完整程序
# 产物: dist/kndoyle-<版本>.tar.gz + dist/kndoyle-<版本>.sha256
# 保证: 完整(全部代码) / 无重复(单一事实源) / 可校验(清单签名)

set -euo pipefail
cd "$(dirname "$0")"

VERSION="$(git describe --tags 2>/dev/null || git rev-parse --short HEAD 2>/dev/null || echo 'dev')"
VERSION="$(echo "$VERSION" | tr -d '[:space:]')-$(date +%Y%m%d)"
OUT="dist/kndoyle-${VERSION}.tar.gz"
STAGE="dist/stage"

echo "==> 版本: ${VERSION}"

rm -rf "$STAGE"
mkdir -p "$STAGE/kndoyle"

# 收集文件清单（排除 git 元数据 / 缓存 / 构建产物）
mapfile -t FILES < <(git ls-files -co --exclude-standard | grep -v -E '^(dist/|build/|__pycache__/)')

if [ "${#FILES[@]}" -eq 0 ]; then
    echo "错误: 主仓库没有可打包文件"
    exit 1
fi

# 同步到 staging
for f in "${FILES[@]}"; do
    mkdir -p "$STAGE/kndoyle/$(dirname "$f")"
    cp "$f" "$STAGE/kndoyle/$f"
done

echo "==> 纳入文件数: ${#FILES[@]}"

# 生成完整校验清单（内容完整性证明）
( cd "$STAGE/kndoyle" && find . -type f | sort | xargs sha256sum ) > "dist/kndoyle-${VERSION}.sha256"
wc -l < "dist/kndoyle-${VERSION}.sha256" > /dev/null

# 打包
tar -czf "$OUT" -C "$STAGE" kndoyle
rm -rf "$STAGE"

echo "==> 产物: $OUT"
ls -lh "$OUT" "dist/kndoyle-${VERSION}.sha256"

# 校验：解包并对比清单，确认无缺失、无损坏
CHECK_DIR="dist/check"
rm -rf "$CHECK_DIR"
mkdir -p "$CHECK_DIR"
tar -xzf "$OUT" -C "$CHECK_DIR"
( cd "$CHECK_DIR/kndoyle" && sha256sum -c "../../kndoyle-${VERSION}.sha256" ) > /dev/null
rm -rf "$CHECK_DIR"

echo "==> 校验: 通过 (清单 ${#FILES[@]} 文件全部一致)"
echo "==> 使用: 解压后 python3 hunyuan.py all 即可运行完整程序"
