#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fusion.py - 智能共同体协议融合网关

把 HTTP / HTTPS / TCP / UDP / FTP / gttx / gtt / gitt / gtit / gtitx 等协议
统一收口到一个入口，自动识别协议类型并路由到对应处理通道。

"融合"的含义：多种协议能力不各自为政，而是通过一个共同体内核调度——
每个协议是一个"感知端口"，网关是共同体意识，输入进来自动被识别、分流、
分发，不需要调用方关心底层协议差异。

用法:
  python fusion.py "https://example.com"           # HTTP(S) 抓取
  python fusion.py "ftp://host/file"               # FTP 拉取
  python fusion.py "gttx://pdf:https://example.com" # 共同体协议 → 转换分发
  python fusion.py "tcp://host:port"               # TCP 连接（只读探测）
  python fusion.py "udp://host:port"               # UDP 探测（无回显）
  python fusion.py --list                           # 列出已注册协议
"""
import os
import re
import sys
import socket
import tempfile
import urllib.parse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 复用 phoneconv 转换能力作为"融合分发"的下游
GTTX = os.path.join(BASE_DIR, "..", "phoneconv", "gttx.py")


# ---------- 协议注册表（共同体协议家族） ----------
# 每个协议 = 一个感知端口，说明 + 类别
PROTOCOLS = {
    "http":    {"desc": "超文本传输（网页抓取）",            "cat": "传输"},
    "https":   {"desc": "加密超文本传输（网页抓取）",        "cat": "传输"},
    "ftp":     {"desc": "文件传输（拉取远程文件）",          "cat": "传输"},
    "tcp":     {"desc": "传输控制（字节流连接探测）",        "cat": "流"},
    "udp":     {"desc": "用户数据报（无连接探测）",          "cat": "流"},
    "gttx":    {"desc": "共同体智能分发（按意图选通道）",    "cat": "共同体"},
    "gtt":     {"desc": "共同体通用传输",                    "cat": "共同体"},
    "gitt":    {"desc": "共同体索引传输",                    "cat": "共同体"},
    "gtit":    {"desc": "共同体目标索引传输",                "cat": "共同体"},
    "gtitx":   {"desc": "共同体目标索引智能分发",            "cat": "共同体"},
    "knd":     {"desc": "共同体核心命名",                    "cat": "共同体"},
    "mlil":    {"desc": "索引层（检索）",                    "cat": "共同体"},
}


# ---------- 协议别名合并（同一协议多写法） ----------
ALIAS = {
    "gtt": "gttx",
    "gitt": "gttx",
    "gtit": "gttx",
    "gtitx": "gttx",
}


def list_protocols():
    print("共同体协议族（fusion://<协议>:<输入>）:")
    print("%-8s %-32s %s" % ("协议", "说明", "类别"))
    for k, v in PROTOCOLS.items():
        print("%-8s %-32s %s" % (k, v["desc"], v["cat"]))


def detect_protocol(uri):
    """从 URI 识别协议。gttx/gtt/gitt/gtit/gtitx 归入共同体家族。"""
    if uri.startswith(("http://", "https://", "ftp://", "tcp://", "udp://")):
        return uri.split("://", 1)[0].lower()
    m = re.match(r"^([a-z]+)://", uri)
    if m:
        proto = m.group(1).lower()
        if proto in ALIAS:
            return ALIAS[proto]
        if proto in PROTOCOLS:
            return proto
    # 无协议头的裸地址
    if uri.startswith("gttx://"):
        return "gttx"
    if "://" not in uri and "." in uri.split("/")[0]:
        return "https"
    return None


def http_fetch(url):
    """HTTP/HTTPS 抓取：用 python 标准库，返回文本。"""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "kndoyle-fusion/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def ftp_fetch(url):
    """FTP 拉取：解析 host/path，下载为字节。"""
    import ftplib
    parsed = urllib.parse.urlparse(url)
    ftp = ftplib.FTP(parsed.hostname)
    ftp.login()  # 匿名
    fname = os.path.basename(parsed.path) or "ftp_download.bin"
    out = os.path.join(tempfile.gettempdir(), fname)
    with open(out, "wb") as f:
        ftp.retrbinary("RETR " + parsed.path, f.write)
    ftp.quit()
    return out


def tcp_probe(uri):
    """TCP 连接探测：尝试建立连接并回读问候（安全只读）。"""
    parsed = urllib.parse.urlparse(uri)
    host, port = parsed.hostname, parsed.port or 80
    with socket.create_connection((host, port), timeout=5) as s:
        s.sendall(b"")
        return "TCP 连通 %s:%d" % (host, port)


def udp_probe(uri):
    """UDP 探测：发送空报文探测可达性（无回显等待）。"""
    parsed = urllib.parse.urlparse(uri)
    host, port = parsed.hostname, parsed.port or 53
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(3)
    s.sendto(b"", (host, port))
    s.close()
    return "UDP 报文已发送 %s:%d（无回显协议）" % (host, port)


def gttx_dispatch(uri):
    """共同体智能分发：交给 gttx.py 处理。"""
    import subprocess
    r = subprocess.run([sys.executable, GTTX, uri],
                       capture_output=True, text=True, timeout=60)
    return r.stdout or r.stderr


def route(proto, uri):
    """融合路由：按协议分发到处理通道。"""
    handlers = {
        "http": http_fetch,
        "https": http_fetch,
        "ftp": ftp_fetch,
        "tcp": tcp_probe,
        "udp": udp_probe,
        "gttx": gttx_dispatch,
    }
    if proto not in handlers:
        return "协议 [%s] 已注册但无处理通道，仅能识别" % proto
    return handlers[proto](uri)


def main():
    args = sys.argv[1:]
    if not args:
        print("用法: python fusion.py <uri>   或   python fusion.py --list")
        print("示例: python fusion.py https://example.com")
        print("      python fusion.py gttx://pdf:https://example.com")
        print("      python fusion.py tcp://host:port")
        return
    if args[0] in ("--list", "-l"):
        list_protocols()
        return
    uri = args[0]
    proto = detect_protocol(uri)
    if proto is None:
        print("无法识别协议: %s" % uri)
        return
    print("[融合网关] 协议=%s 输入=%s" % (proto, uri))
    try:
        result = route(proto, uri)
        print("[结果] %s" % result)
    except Exception as e:
        print("[错误] %s" % e)


if __name__ == "__main__":
    main()
