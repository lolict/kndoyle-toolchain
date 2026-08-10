# PhoneConv - 手机网页/文档万能格式转换器

没有电脑，用手机 Termux 跑一个替代电脑的网页存档转换程序。把链接、MHT、HTML、ZIP 一键转成
**TXT / DOCX / EPUB / PDF / SVG / CHM(项目)**，覆盖主流浏览器不支持"网页存为这些格式"的空缺。

## 一、手机安装（只需 3 步）

1. **装 Termux**：从 F-Droid 或官方源安装 Termux（一个在 Android 上跑 Linux 命令行的 App）。
2. **把这 3 个文件放到手机**：`conv.py`、`install.sh`、`README.md`。
   放好后用文件管理器移动到 `~/storage/downloads/phoneconv/`，
   或在 Termux 里执行（需已授权存储）：
   ```bash
   termux-setup-storage
   cd ~/storage/downloads/phoneconv
   ```
3. **运行安装脚本**（一次性，自动装好所有依赖）：
   ```bash
   bash install.sh
   ```

## 二、使用（手机上执行）

把链接或文件转成全部格式：

```bash
python conv.py https://example.com/某网页
```

转成部分格式：

```bash
python conv.py /sdcard/Download/某文件.mht --fmt txt,docx,pdf
```

解压 ZIP 里自动找 MHT/HTML 再转换：

```bash
python conv.py /sdcard/Download/offlines.zip
```

输出默认在 `~/conv_out/`，可指定目录：

```bash
python conv.py 输入 --outdir ~/conv_out
```

## 三、支持清单

| 输入 | 说明 |
|---|---|
| URL (http/https) | 直接抓网页正文 |
| .html / .htm | 本地网页文件 |
| .mht | 网页存档单文件（含图片资源） |
| .zip | 自动解包并找第一个 MHT/HTML |

| 输出 | 生成方式 |
|---|---|
| txt | html2text 提取纯文本 |
| docx | pandoc 转换，可用 Word/WPS 打开 |
| epub | pandoc 转换，可导入阅读器 |
| pdf | wkhtmltopdf 渲染 |
| svg | HTML 内嵌 foreignObject 的矢量封装，浏览器可打开 |
| chm | 生成 CHM 项目文件(project.hhp)，在 Windows 用 hhc 编译出 .chm |
| html | 还原纯 HTML |

## 四、注意

- 深色/动态网页（JS 渲染）用 `curl` 只能抓到框架。此时先在手机浏览器里
  **保存网页为 .mht（或"网页，仅 HTML"）**，再用本工具转，资源不丢。
- CHM 编译器（hhc）只能在 Windows 上跑，手机端生成的是完整 CHM 工程源码，
  拷到电脑双击 `project.hhp` 即可编译出最终 .chm。
- 全部工具均为命令行：python + pandoc + wkhtmltopdf，无成品软件、无广告、可离线。

## 五、把格式转出目录（Termux 里打开文件）

```bash
cd ~/conv_out
```

文件会出现在手机存储的 `~/storage/downloads/conv_out/` 下，可直接用手机文档 App 打开。
