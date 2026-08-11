#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""外置大脑 - 知识库构建器

扫描 docs/*.txt，标题化 / 字数统计 / 标签提取 / 三维坐标 / 中文倒排索引，
输出 kb.json（检索用）与 index.md（人读用）。
"""
import glob
import json
import math
import os
import re

import jieba

BASE = os.path.dirname(os.path.abspath(__file__))
DOC_DIR = os.path.join(BASE, "docs")

TAG_KEYWORDS = {
    "娱乐追星": ["刘楚恬", "凝灯", "拍摄时间", "精神锚点"],
    "诗歌创作": ["押韵", "格律", "韵脚", "古风", "意象表达", "情绪感染力"],
    "排版符号": ["破折号", "Unicode", "长横线", "全角长横"],
    "创业融资": ["创业团队", "孵化", "商业计划书", "筹钱", "入局"],
    "文件转换": ["MHT", "Termux", "DOCX", "offlines", "wget"],
    "AI工具": ["WorkBuddy", "autoclaw", "pocketpal", "赠送积分", "云端打包", "查重"],
    "离线模型": ["离线模型", "大语言模型", "本地模型", "小龙虾", "GGUF"],
    "手机硬件": ["运存", "RAM", "12GB", "物理内存"],
    "范畴论": ["范畴论", "函子", "态射", "智能电路"],
    "本地部署": ["云端AI", "本地智能", "下载模型", "部署本地"],
    "内容创作": ["思维树", "固态坐标", "世界观", "符号体系", "规则流"],
    "协议融合": ["融合网关", "共同体协议", "智能共同体", "gttx", "协议融合", "感知端口"],
    "按需打包": ["按需索取", "支撑文件", "拉取代码", "重复检测", "按需打包", "vendor"],
    "感知语言": ["gkhtml", "梅花桩", "感知标记", "自定义标签", "感知前端"],
    "语言选型": ["风评", "排行榜", "编程语言选择", "语言选型", "Zig、Nim"],
}

TAG_VECTOR = {
    "娱乐追星": (0, 0, 0),
    "诗歌创作": (1, 1, 1),
    "排版符号": (5, 3, 4),
    "创业融资": (4, 2, 7),
    "文件转换": (8, 2, 9),
    "AI工具": (6, 8, 6),
    "离线模型": (8, 9, 5),
    "手机硬件": (7, 5, 3),
    "范畴论": (9, 7, 2),
    "本地部署": (7, 8, 6),
    "内容创作": (2, 2, 3),
    "协议融合": (6, 7, 8),
    "按需打包": (5, 5, 8),
    "感知语言": (8, 6, 5),
    "语言选型": (3, 6, 4),
}

CATEGORIES = {
    "AI 与本地智能": ["离线模型", "本地部署", "AI工具"],
    "技术教程": ["文件转换", "排版符号", "范畴论"],
    "内容创作": ["诗歌创作", "内容创作", "娱乐追星"],
    "商业与创业": ["创业融资"],
    "硬件指南": ["手机硬件"],
    "智能共同体": ["协议融合", "按需打包", "感知语言", "语言选型"],
}

STOP = set("的了是在和与有就都不我这你他她它们？。，！、；：\"'()（）【】[]…—·「」")


def parse(path):
    raw = open(path, encoding="utf-8", errors="ignore").read()
    url = re.search(r"^URL: (\S+)", raw, re.M)
    title = re.search(r"^TITLE: (.*?)(?:\s*-\s*豆包)?$", raw, re.M)
    body = re.sub(r"^(URL|TITLE):.*$\n?", "", raw, flags=re.M)
    return (url.group(1) if url else "",
            (title.group(1).strip() if title else os.path.basename(path)),
            body)


def extract_tags(body):
    return [t for t, kws in TAG_KEYWORDS.items() if any(k in body for k in kws)]


def category_of(tags):
    scores = {}
    for cat, members in CATEGORIES.items():
        scores[cat] = sum(1 for m in members if m in tags)
    if not scores:
        return "未分类"
    return max(scores, key=scores.get)


def position(tags):
    vs = [TAG_VECTOR[t] for t in tags if t in TAG_VECTOR]
    if not vs:
        return (5, 5, 5)
    return tuple(round(sum(v[i] for v in vs) / len(vs), 2) for i in range(3))


def tokenize(text):
    return [w for w in jieba.lcut(text) if len(w.strip()) > 1 and w.strip() not in STOP]


def build_inverted(docs):
    inv = {}
    for d in docs:
        for pos, word in enumerate(d["tokens"]):
            inv.setdefault(word, {}).setdefault(d["id"], []).append(pos)
    return inv


def main():
    docs = []
    for path in sorted(glob.glob(os.path.join(DOC_DIR, "*.txt"))):
        url, title, body = parse(path)
        tokens = tokenize(body)
        tags = extract_tags(body)
        pos = position(tags)
        docs.append({
            "id": os.path.basename(path),
            "url": url,
            "title": title,
            "chars": len(re.sub(r"\s+", "", body)),
            "tags": tags,
            "category": category_of(tags),
            "pos": pos,
            "text": body,
            "tokens": tokens,
        })
    for d in docs:
        d.pop("tokens")

    inv = build_inverted([{**d, "tokens": tokenize(d["text"])} for d in docs])
    kb = {"docs": docs, "inverted": inv}
    with open(os.path.join(BASE, "kb.json"), "w", encoding="utf-8") as f:
        json.dump(kb, f, ensure_ascii=False)
    print("知识库构建完成：%d 篇，%d 个索引词" % (len(docs), len(inv)))
    for d in docs:
        print("  %-30s %6d字 %s" % (d["title"], d["chars"], d["pos"]))


if __name__ == "__main__":
    main()
