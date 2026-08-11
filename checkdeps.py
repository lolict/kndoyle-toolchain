#!/usr/bin/env python3
# checkdeps.py - 检查按需拉取代码的"支撑完整性"与"重复状态"
# 用法:
#   python3 checkdeps.py                 # 检查所有 vendor 子目录
#   python3 checkdeps.py yuan-ji-jiu-can # 检查指定 vendor 目录
# 检查项:
#   1. 支撑完整性: mod/import/include/require 声明的文件是否都存在
#   2. 外部依赖:   是否引用本机/远程资源（缺失则无法独立运行）
#   3. 重复检测:   vendor 代码与主仓库其他代码是否内容重复

import json
import os
import re
import sys
import hashlib

ROOT = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.join(ROOT, "vendor")

LANG_CHECKS = {
    ".rs": {
        # 只有分号结尾的 `mod x;` 才引用外部文件；`mod x { ... }` 是内联模块块
        "mod": [r'^\s*(?:pub\s+)?mod\s+([a-zA-Z0-9_]+)\s*;'],
        "use": [r'^\s*use\s+[a-zA-Z0-9_:]+::([a-zA-Z0-9_]+)'],
        "ext": [r'(?:include!|include_bytes!|include_str!)\("([^"]+)"\)'],
    },
    ".py": {
        "import": [r'^\s*(?:from\s+([a-zA-Z0-9_\.]+)\s+import|import\s+([a-zA-Z0-9_\.]+))'],
        "ext": [],
    },
    ".c": {"include": [r'#include\s*[<"]([^>"]+)[>"]'], "ext": []},
    ".h": {"include": [r'#include\s*[<"]([^>"]+)[>"]'], "ext": []},
    ".v": {"include": [r'`include\s*"([^"]+)"'], "ext": []},
    ".js": {"require": [r"require\(['\"]([^'\"]+)['\"]\)"], "ext": []},
}

def file_sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def scan_deps(tree):
    mods = {}
    uses = set()
    ext = set()
    for root, _, files in os.walk(tree):
        for fn in files:
            p = os.path.join(root, fn)
            extn = os.path.splitext(fn)[1].lower()
            rules = LANG_CHECKS.get(extn)
            if not rules:
                continue
            try:
                text = open(p, "r", errors="ignore").read()
            except OSError:
                continue
            for kind, patterns in rules.items():
                for pat in patterns:
                    for m in re.finditer(pat, text, re.MULTILINE):
                        name = next((g for g in m.groups() if g), "")
                        if not name:
                            continue
                        if kind in ("mod", "use", "import", "include", "require"):
                            mods.setdefault(kind, set()).add((name, os.path.relpath(p, tree)))
                        elif kind == "ext":
                            ext.add(name)
    return mods, ext

# Python 标准库（import 这些不算缺失支撑）
PY_STDLIB = {
    "__future__", "abc", "argparse", "asyncio", "base64", "collections", "copy", "csv",
    "ctypes", "dataclasses", "datetime", "enum", "functools", "glob",
    "hashlib", "heapq", "importlib", "io", "itertools", "json", "logging",
    "math", "multiprocessing", "os", "pathlib", "pickle", "queue", "random",
    "re", "shutil", "signal", "socket", "sqlite3", "statistics", "string",
    "struct", "subprocess", "sys", "tempfile", "threading", "time",
    "traceback", "typing", "unittest", "urllib", "uuid", "warnings",
    "weakref", "xml", "zipfile", "sysconfig", "types",
}

def is_stdlib(mod_name):
    top = mod_name.split(".")[0]
    return top in PY_STDLIB

def check_support(name):
    tree = os.path.join(VENDOR, name)
    if not os.path.isdir(tree):
        print(f"[错误] vendor/{name} 不存在")
        return False
    mods, ext = scan_deps(tree)
    problems = []
    # 检查模块文件是否存在
    for kind, entries in mods.items():
        for mod_name, ref_file in entries:
            base = mod_name.rsplit(".", 1)[-1]
            found = False
            for root, _, files in os.walk(tree):
                if any(f == f"{base}.rs" or f == f"{base}.py" or f == f"{base}.c" or f == f"{base}.h" or f == f"{base}.v" for f in files):
                    found = True
                    break
                for f in files:
                    if f == "mod.rs" and os.path.basename(root) == base:
                        found = True
            if not found and kind in ("mod", "import") and not mod_name.startswith(("std", "crate", "super", "self")) and not is_stdlib(mod_name):
                problems.append(f"  [缺失支撑] {kind} '{mod_name}' (引用自 {ref_file}) 在 vendor/{name} 内找不到对应文件")
    # 外部依赖提示
    for e in sorted(ext):
        problems.append(f"  [外部依赖] {e} —— 指向 vendor/{name} 之外，需确认目标环境可用")
    if problems:
        print(f"== {name}: 支撑检查发现问题 ==")
        for p in problems:
            print(p)
        return False
    print(f"== {name}: 支撑完整（全部 mod/import/include 均在仓库内）==")
    return True

def check_dup(name):
    tree = os.path.join(VENDOR, name)
    hashes = {}
    for root, _, files in os.walk(ROOT):
        if ".git" in root or "dist" in root or "__pycache__" in root or "/vendor" in root:
            continue
        for fn in files:
            if fn.endswith((".pyc", ".zip", ".hex", ".png", ".jpg")):
                continue
            p = os.path.join(root, fn)
            try:
                h = file_sha256(p)
            except OSError:
                continue
            hashes.setdefault(h, []).append(p)
    # 补丁源与已应用补丁属同一文件的两处存放，豁免
    patch_srcs = set()
    patch_dir = os.path.join(ROOT, "patches")
    if os.path.isdir(patch_dir):
        for root, _, files in os.walk(patch_dir):
            for fn in files:
                p = os.path.join(root, fn)
                try:
                    patch_srcs.add(file_sha256(p))
                except OSError:
                    pass
    dup_found = False
    for root, _, files in os.walk(tree):
        for fn in files:
            p = os.path.join(root, fn)
            try:
                h = file_sha256(p)
            except OSError:
                continue
            for other in hashes.get(h, []):
                if other != p and not other.startswith(VENDOR) and h not in patch_srcs:
                    print(f"  [重复] {os.path.relpath(p, ROOT)} == {os.path.relpath(other, ROOT)} (sha256 相同)")
                    dup_found = True
    if not dup_found:
        print(f"== {name}: 与主仓库无重复文件 ==")
    return not dup_found

def main():
    if len(sys.argv) > 1:
        names = [sys.argv[1]]
    else:
        if not os.path.isdir(VENDOR):
            print("vendor/ 目录不存在")
            return
        names = sorted(os.listdir(VENDOR))
    for n in names:
        if not os.path.isdir(os.path.join(VENDOR, n)):
            continue
        ok1 = check_support(n)
        ok2 = check_dup(n)
        print()
        status = "PASS" if (ok1 and ok2) else "FAIL"
        print(f"== {n}: 总体 {status} ==")
        print()

if __name__ == "__main__":
    main()
