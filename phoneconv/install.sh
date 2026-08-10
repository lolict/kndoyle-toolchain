#!/data/data/com.termux/files/usr/bin/bash
# PhoneConv 一键安装脚本（Termux 环境执行）

echo "[1/3] 更新软件源..."
pkg update -y && pkg upgrade -y

echo "[2/3] 安装核心工具..."
pkg install -y python pandoc curl wkhtmltopdf unzip

echo "[3/3] 安装 Python 库..."
pip install html2text

echo ""
echo "PhoneConv 安装完成！"
echo "用法: python conv.py <URL 或文件路径> [--fmt txt,docx,pdf,epub,svg] [--outdir 输出目录]"
