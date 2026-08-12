#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""color42 - 汉字本体颜色编码（三维进制编码）

两套 6 行 × 7 列 = 42 字的表，每个汉字本身就是一个数码（本体编码），
不做代号替换。把汉字表用作 42 进制数码集，支持多字序列编码与三维坐标编码。

第一套（颜色表，无梯度）：
  行1: 红 橙 黄 绿 青 蓝 紫
  行2: 褐 棕 黑 靛 粉 彩 白
  行3: 朱 绛 赭 丹 彤 缃 黛
  行4: 翠 碧 缥 素 银 金 灰
  行5: 玉 琅 晶 璃 珀 瑙 璧
  行6: 曦 辉 霓 旖 靡 暝 黟

第二套（韵律表，带梯度系）：
  行1: 妃 粉 彤 赤 棕 绛 赭
  行2: 缃 金 黄 褐 黧 乌 黑   (黄系·光)
  行3: 缥 翠 绿 青 苍 黛 玄   (绿系·生)
  行4: 素 银 蓝 紫 靛 绀 黯   (蓝系·冷)
  行5: 玉 琅 晶 璃 珀 瑙 璧   (泽系·石)
  行6: 曦 辉 霓 旖 靡 暝 黟   (光系·韵)

用法:
  python color42.py list                 # 列出两套表
  python color42.py v <字> <表>          # 查字的值(0-41)
  python color42.py c <值> <表>          # 查值的字
  python color42.py e <数值> <表> <位数> # 数值 → 三维(3字)进制编码
  python color42.py d <字串> <表>        # 字串 → 数值解码
  python color42.py p <字> <表>          # 字的二维坐标(行,列)
  python color42.py g <字>               # 查字的梯度系(仅韵律表)
"""
import sys

# 表1：颜色表（6 行 × 7 列 = 42 字，无梯度）
TABLE_COLOR = [
    "红橙黄绿青蓝紫",
    "褐棕黑靛粉彩白",
    "朱绛赭丹彤缃黛",
    "翠碧缥素银金灰",
    "玉琅晶璃珀瑙璧",
    "曦辉霓旖靡暝黟",
]

# 表2：韵律表（6 行 × 7 列 = 42 字，带梯度系）
TABLE_RHYTHM = [
    "妃粉彤赤棕绛赭",
    "缃金黄褐黧乌黑",
    "缥翠绿青苍黛玄",
    "素银蓝紫靛绀黯",
    "玉琅晶璃珀瑙璧",
    "曦辉霓旖靡暝黟",
]

# 韵律表梯度系（行 → 梯度名）；首行未标注，记为基
RHYTHM_GRADIENT = {
    1: "赤基",   # 行1 妃粉彤赤棕绛赭（暖红基）
    2: "黄系·光",
    3: "绿系·生",
    4: "蓝系·冷",
    5: "泽系·石",
    6: "光系·韵",
}

TABLES = {
    "颜色": TABLE_COLOR,
    "color": TABLE_COLOR,
    "韵律": TABLE_RHYTHM,
    "rhythm": TABLE_RHYTHM,
}


def _flatten(table):
    """把 6×7 表展平为 42 字序列。"""
    return list("".join(table))


def _table(name):
    if name not in TABLES:
        raise KeyError("未知表: %s（可用: 颜色 / color / 韵律 / rhythm）" % name)
    return TABLES[name]


def value_of(char, table_name="颜色"):
    """字 → 值 (0-41)。位置 = 行*7 + 列。"""
    flat = _flatten(_table(table_name))
    if char not in flat:
        raise KeyError("字 [%s] 不在 %s 表中" % (char, table_name))
    return flat.index(char)


def char_of(value, table_name="颜色"):
    """值 (0-41) → 字。"""
    flat = _flatten(_table(table_name))
    if not (0 <= value < 42):
        raise ValueError("值须在 0-41 之间: %d" % value)
    return flat[value]


def position_of(char, table_name="颜色"):
    """字 → (行, 列) 二维坐标，1 起始。"""
    v = value_of(char, table_name)
    return (v // 7 + 1, v % 7 + 1)


def gradient_of(char, table_name="韵律"):
    """字 → 梯度系（仅韵律表有意义）。"""
    if table_name not in ("韵律", "rhythm"):
        return "无梯度"
    row, _ = position_of(char, table_name)
    return RHYTHM_GRADIENT.get(row, "未知")


def encode(value, table_name="颜色", digits=3):
    """数值 → 多字进制编码（默认三维 = 3 字）。

    42 进制: value = d2*42^2 + d1*42 + d0，每位数取表中对应字。
    三维编码即固定 3 个汉字表示一个数，范围 0 .. 42^3-1。
    """
    if value < 0:
        raise ValueError("不支持负数: %d" % value)
    flat = _flatten(_table(table_name))
    result = []
    for i in range(digits):
        result.append(flat[value % 42])
        value //= 42
    if value > 0:
        raise ValueError("数值超出 %d 位 42 进制范围" % digits)
    return "".join(reversed(result))


def decode(chars, table_name="颜色"):
    """字串 → 数值（多字 42 进制解码）。"""
    flat = _flatten(_table(table_name))
    v = 0
    for c in chars:
        if c not in flat:
            raise KeyError("字 [%s] 不在 %s 表中" % (c, table_name))
        v = v * 42 + flat.index(c)
    return v


def list_tables():
    print("汉字本体颜色编码（42 进制，每字一个数码）")
    print()
    print("第一套 · 颜色表（无梯度）")
    for i, row in enumerate(TABLE_COLOR, 1):
        print("  行%d: %s" % (i, "  ".join(row)))
    print()
    print("第二套 · 韵律表（带梯度系）")
    for i, row in enumerate(TABLE_RHYTHM, 1):
        g = RHYTHM_GRADIENT.get(i, "")
        print("  行%d: %s  %s" % (i, "  ".join(row), ("(" + g + ")" if g else "")))
    print()
    print("42 进制示例: 数值 100 → %s（三维编码）" % encode(100, "颜色", 3))
    print("三维坐标: (行, 列) ∈ 6×7 = 42 位，每字一坐标")


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("list", "-l", "--list"):
        list_tables()
        return
    cmd = args[0]
    try:
        if cmd == "v":  # 字 → 值
            t = args[2] if len(args) > 2 else "颜色"
            print("%s = %d" % (args[1], value_of(args[1], t)))
        elif cmd == "c":  # 值 → 字
            t = args[2] if len(args) > 2 else "颜色"
            print("%d = %s" % (int(args[1]), char_of(int(args[1]), t)))
        elif cmd == "e":  # 数值 → 三维编码
            t = args[2] if len(args) > 2 else "颜色"
            d = int(args[3]) if len(args) > 3 else 3
            print("%d → %s（%d 维 %s 表）" % (int(args[1]), encode(int(args[1]), t, d), d, t))
        elif cmd == "d":  # 字串 → 数值
            t = args[2] if len(args) > 2 else "颜色"
            print("%s = %d" % (args[1], decode(args[1], t)))
        elif cmd == "p":  # 字 → 坐标
            t = args[2] if len(args) > 2 else "颜色"
            r, c = position_of(args[1], t)
            print("%s = (行%d, 列%d)" % (args[1], r, c))
        elif cmd == "g":  # 字 → 梯度系
            t = args[2] if len(args) > 2 else "韵律"
            print("%s → %s" % (args[1], gradient_of(args[1], t)))
        else:
            print("未知命令: %s" % cmd)
    except (KeyError, ValueError) as e:
        print("错误: %s" % e)


if __name__ == "__main__":
    main()
