#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PhoneConv - 手机上替代电脑的网页/文档格式转换工具 (Termux)

输入: URL / 本地 HTML / MHT / ZIP(内含 MHT/HTML)
输出: TXT / DOCX / EPUB / PDF / SVG / CHM(项目) / HTML

用法:
  python conv.py <input>                     # 全部格式
  python conv.py <input> --fmt txt,docx,pdf  # 指定格式
  python conv.py <input> --outdir ~/conv_out
"""
import argparse
import base64
import email
import html as htmlmod
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile


def is_url(s):
    return re.match(r"^https?://", s, re.I) is not None


def run(cmd, check=True):
    proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise RuntimeError("命令失败: %s\n%s" % (cmd, proc.stderr[-2000:]))
    return proc.stdout


def which(name):
    return shutil.which(name) is not None


def fetch_url(url, out_html):
    ua = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36"
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read()
    charset = "utf-8"
    mt = resp.headers.get("Content-Type", "")
    m = re.search(r"charset=([\w-]+)", mt, re.I)
    if m:
        charset = m.group(1)
    try:
        text = raw.decode(charset, errors="replace")
    except LookupError:
        text = raw.decode("utf-8", errors="replace")
    with open(out_html, "w", encoding="utf-8") as f:
        f.write(text)
    return text


def _mht_parse(data):
    msg = email.message_from_bytes(data)
    parts = {}
    html_body = None
    for part in msg.walk():
        ctype = part.get_content_type()
        cid = part.get("Content-ID")
        cid = cid.strip("<>") if cid else None
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        if ctype == "text/html" and html_body is None:
            charset = part.get_content_charset() or "utf-8"
            html_body = payload.decode(charset, errors="replace")
        elif cid:
            parts[cid] = "data:%s;base64,%s" % (ctype, base64.b64encode(payload).decode())
    if html_body is None:
        raise RuntimeError("MHT 中未找到 text/html 部分")
    html_body = re.sub(r"cid:([^\s\"'>)]+)",
                       lambda m: parts.get(m.group(1).strip("<>"), m.group(0)),
                       html_body, flags=re.I)
    return html_body


def mht_to_html(path):
    with open(path, "rb") as f:
        return _mht_parse(f.read())


def prepare_html(inp, workdir):
    """返回工作 HTML 文件路径"""
    out = os.path.join(workdir, "page.html")
    if is_url(inp):
        fetch_url(inp, out)
        return out
    if not os.path.exists(inp):
        raise RuntimeError("输入不存在: %s" % inp)
    lower = inp.lower()
    if lower.endswith(".mht"):
        html_body = mht_to_html(inp)
        with open(out, "w", encoding="utf-8") as f:
            f.write(html_body)
        return out
    if lower.endswith(".zip"):
        member = None
        with zipfile.ZipFile(inp) as z:
            for name in z.namelist():
                if name.lower().endswith((".mht", ".html", ".htm")):
                    member = name
                    break
            if member is None:
                raise RuntimeError("ZIP 中未找到 MHT/HTML")
            data = z.read(member)
        if member.lower().endswith(".mht"):
            html_body = mht_to_html_bytes(data)
            with open(out, "w", encoding="utf-8") as f:
                f.write(html_body)
        else:
            with open(out, "wb") as f:
                f.write(data)
        return out
    if lower.endswith((".html", ".htm")):
        shutil.copy(inp, out)
        return out
    raise RuntimeError("不支持的输入类型: %s" % inp)


def mht_to_html_bytes(data):
    return _mht_parse(data)


def to_txt(html_path, out_path):
    try:
        import html2text
        with open(html_path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        h = html2text.HTML2Text()
        h.ignore_links = False
        txt = h.handle(content)
    except ImportError:
        txt = run("pandoc %s -t plain" % html_path)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(txt)


def pandoc_conv(html_path, out_path, to_fmt):
    run('pandoc "%s" -o "%s" --standalone' % (html_path, out_path) if to_fmt == "epub"
        else 'pandoc "%s" -o "%s"' % (html_path, out_path))


def to_pdf(html_path, out_path):
    if which("wkhtmltopdf"):
        run('wkhtmltopdf --encoding utf-8 --enable-local-file-access "%s" "%s"' % (html_path, out_path))
        return
    try:
        from weasyprint import HTML
        HTML(html_path).write_pdf(out_path)
        return
    except ImportError:
        pass
    raise RuntimeError("需要 wkhtmltopdf 或 weasyprint 才能生成 PDF，请运行 install.sh")


def to_svg(html_path, out_path):
    with open(html_path, encoding="utf-8", errors="replace") as f:
        body = f.read()
    inner = body.replace("&", "&amp;")
    svg = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xhtml="http://www.w3.org/1999/xhtml" '
           'width="100%%" height="100%%" viewBox="0 0 900 1200">\n'
           '<foreignObject width="100%%" height="100%%">\n'
           '<xhtml:body xmlns:xhtml="http://www.w3.org/1999/xhtml" style="font-size:16px;padding:16px">\n'
           '%s\n</xhtml:body>\n</foreignObject>\n</svg>\n' % inner)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)


def to_chm(html_path, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    shutil.copy(html_path, os.path.join(out_dir, "page.html"))
    title = os.path.basename(html_path)
    hhp = os.path.join(out_dir, "project.hhp")
    hhc = os.path.join(out_dir, "toc.hhc")
    with open(hhc, "w", encoding="utf-8") as f:
        f.write('<HTML><HEAD><META http-equiv="Content-Type" content="text/html; charset=utf-8">'
                '</HEAD><BODY><UL><LI><OBJECT type="text/sitemap">'
                '<param name="Name" value="page"><param name="Local" value="page.html">'
                '</OBJECT></UL></BODY></HTML>\n')
    with open(hhp, "w", encoding="utf-8") as f:
        f.write("[OPTIONS]\nCompiled file=page.chm\nDefault topic=page.html\n"
                "Contents file=toc.hhc\nFull-text search=Yes\n"
                "Display compile progress=No\nLanguage=0x804 Chinese (PRC)\n\n"
                "[FILES]\npage.html\n\n[INFOTYPES]\n")


def main():
    ap = argparse.ArgumentParser(description="PhoneConv - 手机网页/文档格式转换")
    ap.add_argument("input", help="URL 或本地 HTML/MHT/ZIP 文件")
    ap.add_argument("--fmt", default="txt,docx,epub,pdf,svg,chm",
                    help="输出格式，逗号分隔: txt,docx,epub,pdf,svg,chm,html")
    ap.add_argument("--outdir", default=os.path.expanduser("~/conv_out"))
    args = ap.parse_args()

    os.makedirs(args.outdir, exist_ok=True)
    fmts = [f.strip() for f in args.fmt.split(",") if f.strip()]

    with tempfile.TemporaryDirectory() as workdir:
        html_path = prepare_html(args.input, workdir)
        base = os.path.join(args.outdir, "output")
        produced = []
        for fmt in fmts:
            out = base + "." + fmt
            if fmt == "txt":
                to_txt(html_path, out)
            elif fmt == "docx":
                pandoc_conv(html_path, out, "docx")
            elif fmt == "epub":
                pandoc_conv(html_path, out, "epub")
            elif fmt == "pdf":
                to_pdf(html_path, out)
            elif fmt == "svg":
                to_svg(html_path, out)
            elif fmt == "chm":
                chm_dir = os.path.join(args.outdir, "output_chm")
                to_chm(html_path, chm_dir)
                out = chm_dir + " (项目文件, 需 hhc 编译)"
            elif fmt == "html":
                out = base + ".html"
                shutil.copy(html_path, out)
            else:
                print("跳过未知格式:", fmt)
                continue
            produced.append(out)
            print("完成:", out)

    print("\n全部输出位于: %s" % args.outdir)
    if not which("pandoc"):
        print("提示: 未检测到 pandoc，DOCX/EPUB 会失败。请运行 install.sh")


if __name__ == "__main__":
    main()
