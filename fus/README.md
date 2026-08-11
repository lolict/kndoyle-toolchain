# fus - 智能共同体协议融合网关

对应符号词典 `hfgttcp://`（共同体协议头）：统摄 HTTP / HTTPS / TCP / UDP / FTP
与 `gttx` 家族（gttx/gtt/gitt/gtit/gtitx）等子协议，一个入口收口全部能力。

## 概念

**融合不是把协议混在一起，而是让它们成为共同体的不同感知端口。**

输入进到网关 → 自动识别协议 → 分流到对应处理通道 → 返回统一结果。
调用方不需要关心底层协议差异，共同体意识（网关）负责路由。

## 使用

```bash
python3 fusion.py https://example.com            # HTTP(S) 抓取
python3 fusion.py ftp://host/file               # FTP 拉取
python3 fusion.py tcp://host:port               # TCP 连接探测
python3 fusion.py udp://host:port               # UDP 报文探测
python3 fusion.py gttx://pdf:https://example.com # 共同体分发 → 转换
python3 fusion.py gttx://list                    # 列出共同体通道
python3 fusion.py --list                         # 列出已注册协议
```

## 协议家族

| 协议 | 说明 | 类别 |
|---|---|---|
| http / https | 超文本传输（网页抓取） | 传输 |
| ftp | 文件传输 | 传输 |
| tcp / udp | 字节流 / 数据报探测 | 流 |
| gttx | 共同体智能分发（按意图选通道） | 共同体 |
| gtt / gitt / gtit / gtitx | gttx 变体（统一并入共同体分发） | 共同体 |
| knd / mlil | 共同体核心命名 / 索引层 | 共同体 |

## 融合分发下游

- HTTP/HTTPS：标准库 urllib 抓取
- FTP：标准库 ftplib 匿名拉取
- TCP/UDP：socket 只读探测（不建隧道、不做转发）
- gttx：调用 `phoneconv/gttx.py` 智能分发（txt/docx/epub/pdf/svg/chm/brain）

## 与符号词典对齐

| 符号 | 本实现 |
|---|---|
| `hfgttcp://` | `fusion.py`（统摄入口） |
| `gttx://` | `phoneconv/gttx.py`（中心分发） |
| `mlil` | 共同体索引层（协议注册表） |
