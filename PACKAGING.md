# PACKAGING - 打包治理方案（防重复、防缺失、防冲突）

## 问题

多仓库各自推送同类内容，导致：打包冲突（重复代码）、内容缺失（同步不一致）、
内存占用膨胀、无法合并成一个完整程序。

## 原则（一代码只在一处）

1. **单一事实源**：主仓库 `kenandaoer` 是唯一存代码的地方。
2. **镜像 = 整仓备份**，不是内容复制。镜像用 `git push --mirror`，
   与主仓库字节级一致，不存在"这仓库有、那仓库没有"。
3. **打包只基于主仓库**：产物完整、无重复、无缺失。
4. **未并入主仓库的代码不参与打包**：核心创作仓库（满全法/关系代数/Unicore）
   在用户授权合并前，保持独立，不参与打包。

## 打包流程（主仓库）

```bash
bash package.sh        # 一键打包 → dist/kndoyle-<版本>.tar.gz
```

打包包含：
- 全部 hunyuan 模块（hunyuan.py + 八模块 + CPU/FPGA/tapeout）
- `phoneconv/`（conv.py / gttx.py / install.sh / fetch_all.js）
- `brain/`（build.py / ask.py / docs / kb.json）
- `vendor/`（按需索取的其他仓库功能，含 SOURCE.md 来源标注）
- `COLLAB.md` `REPOS.md` `PACKAGING.md` `kndoyle-symbols.md`

解压后一条命令安装并可用（手机 Termux / Linux 均可）。

**已验证（2026-08-11）**：打包 66 文件 → `dist/kndoyle-56fa3db-20260811.tar.gz`（685K），
sha256 清单逐文件校验全部一致；解压后 `python3 hunyuan.py all` 完整运行
（v1.4 双发射 CPU 全演示）。打包不冲突、不缺失、可复现。

## 整仓镜像同步（替代逐文件复制）

```bash
# 拉取主仓库后，直接整仓推送到镜像
git push --mirror toolchain-gitee
git push --mirror toolchain-gitcode
git push --mirror toolchain-github
```

`--mirror` 保证镜像和主仓库完全一致，杜绝内容偏差与遗漏。

## 按需索取（vendor）—— 缺什么拉什么，不整仓搬运

核心仓库（满全法OS/关系代数/Unicore）**不整仓并入**，缺哪个重要功能拉哪个：

```bash
bash pull.sh yuan-ji-jiu-can hunyuan-rs             # 拉满全法OS的Rust实现
bash pull.sh relational-algebra relational_algebra  # 拉关系代数核心
bash pull.sh Unicore src examples                   # 拉指令集源码与示例
```

产物在 `vendor/<来源仓库>/<路径>/`，**独立目录 + SOURCE.md 标注来源**：
- 可辨：每个 vendor 子目录一眼看出是哪个仓库来的（不混合搅拌）
- 可认：SOURCE.md 记录仓库/commit/日期，未来可核对版本
- 可打：vendor 目录随 package.sh 一起打包，功能完整且来源清晰

**拉取原则**：只拉自己缺的重要功能；不缺的不拉；拉进来的是独立可用模块。

**支撑完整性与重复检测（自动）**：每次 `pull.sh` 拉取后自动运行 `checkdeps.py`：

```bash
python3 checkdeps.py           # 检查全部 vendor
python3 checkdeps.py 仓库名     # 检查指定 vendor
```

检查两项：
1. **支撑完整性**：代码里 `mod`/`import`/`include`/`require` 声明的每个模块文件
   是否都已拉取（防止"局部拉取漏掉支撑文件，代码失去用意"）
2. **重复状态**：sha256 全库比对，vendor 代码是否与主仓库其他文件内容重复
   （防止"拉进来又重复"）

两项均 PASS 才视为可打包。**失败即停止**：缺支撑就补齐支撑文件，
有重复就删除新拉的重复副本。

**兼容补丁（patches/）**：若上游代码自身有 bug（如 relational-algebra 的
`__init__.py` 引用了模块里不存在的 `selection`/`projection`/`FusionState`
等符号），用独立补丁修复，不改动源仓库风格：

```bash
bash apply_patch.sh relational-algebra   # 应用兼容补丁并验证可运行
```

- 补丁放 `patches/`，应用后写进 vendor（记录于 SOURCE.md）
- vendor 保持来源纯净、可再拉取；重拉后需重新应用补丁
- 补丁验证到"能导入 + 能运算"，而非仅静态检查

## 未来核心合并路径（待用户授权后执行）

1. 将核心创作仓库按模块并入主仓库子目录（如 `core/os/`、`core/relalg/`、`core/uniisa/`）
2. 原仓库转为 `--mirror` 镜像
3. 打包范围扩展到全模块，一个命令产出完整程序
4. 更新本文件"打包包含"清单

## 风险登记

| 风险 | 现状 | 对策 |
|---|---|---|
| 代码重复 | 无（仅主仓库存代码） | 单一事实源 |
| 内容缺失 | 无（镜像整仓同步） | `--mirror` |
| 打包冲突 | 无（未重复推核心代码） | 按归属层推送（REPOS.md） |
| 核心仓库未并入 | 存在（待授权） | 合并前不参与打包 |
