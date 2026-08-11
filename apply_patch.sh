#!/bin/bash
# apply_patch.sh - 把本地兼容补丁应用到 vendor 代码（保持 vendor 来源纯净、可再拉取）
# 用法: bash apply_patch.sh <仓库名>
# 说明: 补丁是本地适配层，独立于源仓库代码；重拉 vendor 后需重新应用。

set -euo pipefail
cd "$(dirname "$0")"

NAME="${1:?用法: bash apply_patch.sh <仓库名>}"
PKG="vendor/$NAME"

# 关系代数补丁：core 缺 selection/projection/natural_join/union/difference/SemiJoin
if [ "$NAME" = "relational-algebra" ]; then
    SRC="patches/relational-algebra-core-compat.py"
    DST="$PKG/relational_algebra/core_compat.py"
    cp "$SRC" "$DST"
    echo "  已复制: $SRC -> $DST"

    INIT="$PKG/relational_algebra/__init__.py"
    grep -q "core_compat" "$INIT" || {
        python3 - "$INIT" << 'PYEOF'
import re, sys
init = sys.argv[1]
src = open(init, encoding="utf-8").read()

# 原导入块
old_block = "from relational_algebra.core import (\n    Relation,\n    selection,\n    projection,\n    natural_join,\n    union,\n    difference,\n    SemiJoin,\n)"

# 替换为: Relation 从 core 取，其余从 core_compat 补齐
new_block = ("from relational_algebra.core import Relation\n"
             "from relational_algebra.core_compat import (\n"
             "    selection,\n    projection,\n    natural_join,\n"
             "    union,\n    difference,\n    SemiJoin,\n)")

if old_block in src:
    src = src.replace(old_block, new_block)
    open(init, "w", encoding="utf-8").write(src)
    print("  已修补: __init__.py 缺失符号改为从 core_compat 补齐")
else:
    print("  [跳过] __init__.py 未匹配原导入块（可能已被修补）")
PYEOF
    }

    # 修复 attribution 的 ContributionType: 移除死导出
    python3 - "$INIT" << 'PYEOF'
import sys
init = sys.argv[1]
src = open(init, encoding="utf-8").read()
old = "from relational_algebra.attribution import (\n    AttributionEngine,\n    AttributionReport,\n    ContributionType,\n)"
new = "from relational_algebra.attribution import (\n    AttributionEngine,\n    AttributionReport,\n)"
if old in src:
    src = src.replace(old, new)
    print("  已修补: attribution 移除不存在的 ContributionType")
else:
    # 也支持非标准缩进版本
    import re
    pat = re.compile(r"from relational_algebra\.attribution import \(\s*\n(.*?)ContributionType,?\s*\n(.*?)\)", re.S)
    def repl(m):
        return f"from relational_algebra.attribution import (\n{m.group(1)}{m.group(2)})"
    src2, n = pat.subn(repl, src)
    if n:
        src = src2
        print("  已修补: attribution 移除不存在的 ContributionType (regex)")
open(init, "w", encoding="utf-8").write(src)

# 修复 observer 的 FusionState: 从 observer 导入块移除（monoidal 已导入 FusionState）
src = open(init, encoding="utf-8").read()
pat = re.compile(r"(from relational_algebra\.observer import \(\s*\n(?:.*?\n)*?.*?)FusionState,?\s*\n(.*?\))", re.S)
src, n = pat.subn(r"\1\2", src)
if n:
    # 确保 monoidal 导入里有 FusionState
    if "from relational_algebra.monoidal import FusionState" not in src:
        if "FusionState" not in src.split("from relational_algebra.monoidal", 1)[-1].split(")", 1)[0]:
            src = src.replace("from relational_algebra.monoidal import (", "from relational_algebra.monoidal import (\n    FusionState,", 1)
    print("  已修补: observer 的 FusionState 从导入块移除")
    open(init, "w", encoding="utf-8").write(src)
PYEOF
    echo "==> 验证导入:"
    ( cd "$PKG" && python3 -c "
from relational_algebra import Relation, selection, projection, natural_join, union, difference, SemiJoin
from relational_algebra import AttributionEngine, AttributionReport, FusionState
print('全部符号导入成功，关系代数包可运行')" )
    exit 0
fi

echo "未知仓库: $NAME（暂无补丁）"
