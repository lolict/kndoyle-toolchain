#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""外置大脑 - 提问接口

用法:
  python ask.py "关键词"        # 单次提问
  python ask.py                 # 进入交互对话，Ctrl+D 退出

检索 = 倒排命中得分 + 三维坐标邻近加成 + 同分类加成，
返回命中文档的标题、坐标距离与上下文片段。
"""
import json
import math
import os
import re
import sys

import jieba

BASE = os.path.dirname(os.path.abspath(__file__))

STOP = set("的了是在和与有就都不我这你他她它们？。，！、；：\"'()（）【】[]…—·「」")


def load():
    with open(os.path.join(BASE, "kb.json"), encoding="utf-8") as f:
        return json.load(f)


def tokenize(text):
    return [w for w in jieba.lcut(text) if len(w.strip()) > 1 and w.strip() not in STOP]


def dist(a, b):
    return round(math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3))), 2)


def snippet(text, term, width=90):
    idx = text.find(term)
    if idx == -1:
        for w in tokenize(term):
            idx = text.find(w)
            if idx != -1:
                break
    if idx == -1:
        return re.sub(r"\s+", " ", text)[:width * 2]
    start = max(0, idx - width)
    end = min(len(text), idx + width)
    return re.sub(r"\s+", " ", text[start:end])


def ask(kb, query):
    q = tokenize(query)
    if not q:
        return []
    inv = kb["inverted"]
    hits = {}
    for w in q:
        for doc_id, positions in inv.get(w, {}).items():
            hits.setdefault(doc_id, {"score": 0, "words": set(), "pos_hint": positions[0]})
            hits[doc_id]["score"] += 10 + len(positions)
            hits[doc_id]["words"].add(w)
    if not hits:
        return []
    docs = {d["id"]: d for d in kb["docs"]}
    results = []
    for doc_id, h in hits.items():
        d = docs[doc_id]
        distance = dist(d["pos"], kb.get("_q_pos", (5, 5, 5)))
        results.append({
            "doc": d,
            "score": h["score"],
            "distance": distance,
            "hit_words": h["words"],
        })
    results.sort(key=lambda r: (-r["score"], r["distance"]))
    return results[:3]


def render(results, query):
    if not results:
        print("没有命中。试试换个词，或先运行 build.py 重建索引。")
        return
    print("命中 %d 条，与坐标距离排序：" % len(results))
    for r in results:
        d = r["doc"]
        print("-" * 60)
        print("标题: %s" % d["title"])
        print("坐标: %s | %d 字 | 分类: %s | 标签: %s" %
              (d["pos"], d["chars"], d["category"], "、".join(d["tags"]) or "无"))
        print("命中词: %s" % "、".join(sorted(r["hit_words"])))
        print("片段: %s" % snippet(d["text"], query))
    print("-" * 60)


def main():
    kb = load()
    if len(sys.argv) > 1:
        render(ask(kb, sys.argv[1]), sys.argv[1])
        return
    print("外置大脑交互模式。输入问题，Ctrl+D 退出。")
    while True:
        try:
            q = input("你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        if q in ("quit", "exit"):
            break
        render(ask(kb, q), q)


if __name__ == "__main__":
    main()
