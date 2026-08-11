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
