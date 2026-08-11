#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""gttx:// 智能分发器 - 共同体协议最小可运行版

根据目标自动选择通道，不走无关范畴，全部命令由智能分发完成。

用法:
  python gttx.py "gttx://pdf:https://example.com"   # 指定格式
  python gttx.py "gttx://all:本地文件.mht"            # 全部格式
  python gttx.py "gttx://brain:https://example.com"  # 存入外置大脑
  python gttx.py "gttx://list"                       # 列出通道
"""
import os
import re
import subprocess
import sys
import tempfile
import time

import conv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BRAIN_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "brain"))
OUT_DIR = os.path.expanduser("~/conv_out")

CHANNELS = {
    "txt":   {"desc": "纯文本",   "tool": "html2text",     "cat": "文本"},
    "docx":  {"desc": "Word文档", "tool": "pandoc",        "cat": "文档"},
    "epub":  {"desc": "电子书",   "tool": "pandoc",        "cat": "阅读"},
    "pdf":   {"desc": "PDF",      "tool": "wkhtmltopdf",   "cat": "打印"},
    "svg":   {"desc": "矢量封装", "tool": "内置",          "cat": "矢量"},
    "chm":   {"desc": "CHM工程",  "tool": "内置",          "cat": "帮助"},
    "brain": {"desc": "存入外置大脑", "tool": "内置",      "cat": "记忆"},
}


INTENT_KEYWORDS = {
    "brain": ["记住", "记忆", "存入", "收录", "学习", "记住它", "收纳", "归档"],
    "docx": ["word", "文档", "编辑", "改写"],
    "epub": ["阅读", "电子书", "kindle"],
    "pdf": ["pdf", "打印", "存档", "备份"],
    "txt": ["文本", "纯文本", "提取文字"],
    "svg": ["矢量", "图形"],
    "chm": ["帮助", "chm", "手册"],
}


def parse_uri(uri):
    m = re.match(r"^gttx://([^:]+):(.+)$", uri)
    if m:
        return m.group(1), m.group(2)
    m2 = re.match(r"^gttx://(.+)$", uri)
    if m2:
        return "all", m2.group(1)
    return None, None


def extract_source(text):
    m = re.search(r"https?://\S+", text)
    if m:
        return m.group(0)
    m = re.search(r"[\w-]+(\.[\w-]+)+", text)
    if m:
        return "https://" + m.group(0)
    if os.path.exists(text.strip()):
        return text.strip()
    return None


def infer_intent(text):
    for ch, kws in INTENT_KEYWORDS.items():
        for kw in kws:
            if kw.lower() in text.lower():
                return ch
    return "all"


def resolve_channel(target):
    if target == "all":
        return [c for c in CHANNELS if c != "brain"]
    if target in CHANNELS:
        return [target]
    return []


def to_brain(src, workdir):
    html_path = conv.prepare_html(src, workdir)
    txt_path = os.path.join(workdir, "page.txt")
    conv.to_txt(html_path, txt_path)
    with open(txt_path, encoding="utf-8", errors="replace") as f:
        txt = f.read()
    title = src if not conv.is_url(src) else src.split("//")[1].split("/")[0]
    fname = "gttx_%d.txt" % int(time.time())
    os.makedirs(os.path.join(BRAIN_DIR, "docs"), exist_ok=True)
    with open(os.path.join(BRAIN_DIR, "docs", fname), "w", encoding="utf-8") as f:
        f.write("URL: %s\nTITLE: %s\n\n%s" % (src, title, txt))
    build = os.path.join(BRAIN_DIR, "build.py")
    if os.path.exists(build):
        subprocess.run([sys.executable, build], check=False)
    return fname


def main():
    args = sys.argv[1:]
    if not args:
        print("用法:")
        print('  python gttx.py "gttx://pdf:https://example.com"')
        print('  python gttx.py "gttx://all:本地文件.mht"')
        print('  python gttx.py "gttx://brain:https://example.com"')
        print('  python gttx.py "gttx://intent:记住 https://example.com"')
        print('  python gttx.py "gttx://list"')
        return
    uri = args[0]
    if uri == "gttx://list":
        print("可用通道（gttx://<目标>:<输入>）:")
        for k, v in CHANNELS.items():
            print("  %-8s %-12s %s" % (k, v["desc"], v["tool"]))
        return
    target, src = parse_uri(uri)
    if target is None:
        print("URI 无法解析:", uri)
        return
    if target == "intent":
        intent = infer_intent(src)
        src = extract_source(src) or src
        print("意图推断: %s" % intent)
        target = intent
    channels = resolve_channel(target)
    if not channels:
        print("未知目标 [%s]。可用: %s" % (target, ", ".join(CHANNELS)))
        return
    print("分发: 目标=%s 输入=%s 通道=%s" % (target, src, ",".join(channels)))

    os.makedirs(OUT_DIR, exist_ok=True)
    with tempfile.TemporaryDirectory() as workdir:
        for ch in channels:
            try:
                if ch == "brain":
                    fname = to_brain(src, workdir)
                    print("  [brain] 已存入外置大脑: docs/%s" % fname)
                    continue
                html_path = conv.prepare_html(src, workdir)
                out = os.path.join(OUT_DIR, "output." + ch)
                if ch == "txt":
                    conv.to_txt(html_path, out)
                elif ch == "docx":
                    conv.pandoc_conv(html_path, out, "docx")
                elif ch == "epub":
                    conv.pandoc_conv(html_path, out, "epub")
                elif ch == "pdf":
                    conv.to_pdf(html_path, out)
                elif ch == "svg":
                    conv.to_svg(html_path, out)
                elif ch == "chm":
                    d = os.path.join(OUT_DIR, "output_chm")
                    conv.to_chm(html_path, d)
                    out = d + " (CHM工程)"
                print("  [%s] 完成: %s" % (ch, out))
            except Exception as e:
                print("  [%s] 失败: %s" % (ch, e))
    print("输出目录: %s" % OUT_DIR)


if __name__ == "__main__":
    main()
