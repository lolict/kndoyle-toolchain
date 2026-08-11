# COLLAB - 多 AI 协作机制（单一事实源 + 镜像）

本仓库由多个平台、多个人工智能共同维护。为避免重复开发与冲突，
所有参与者必须遵守以下协作规则。

## 治理公约

**所有防风险规则（按需索取/支撑检查/重复检测/补丁/打包）统一在
[GOVERNANCE.md](GOVERNANCE.md)**。任何仓库的任何 AI 接手前必读。
本文件管协作流程，GOVERNANCE.md 管防风险规则。

## 核心原则

- **单一事实源**：`gitee.com/lolict/kenandaoer`（origin）是唯一的开发主仓库，
  所有代码改动只在这里提交。
- **其他仓库是镜像**：`toolchain-gitee`、`toolchain-gitcode`、`toolchain-github`
  只读同步主仓库，不参与开发、不直接提交。镜像 = 备份 + 分发。

## 工作流程

1. **接手先看**：`git pull origin master` 拉最新代码。
2. **改动只提交到 origin**，不要往镜像 remote 直接 push 开发分支。
3. **提交后用一条命令同步全部镜像**：

```bash
for r in origin toolchain-gitee toolchain-gitcode toolchain-github; do git push "$r" master; done
```

4. **每次提交说明你改了哪个模块**，保持历史清晰，方便其他 AI 接手。

## 模块职责

| 目录 | 职责 | 入口 |
|---|---|---|
| `cpu/` | CPU 验证链 (v1.4) | `verify_pipeline.py`, `verify_v14.py` |
| `phoneconv/` | 手机文档转换器 | `conv.py`, `gttx.py`, `install.sh`, `fetch_all.js` |
| `brain/` | 外置大脑知识库 | `build.py` 建索引, `ask.py` 提问 |
| `fus/` | 智能共同体协议融合网关 | `fusion.py`（统一收口 HTTP/TCP/UDP/FTP/gttx） |

## 新增记忆的规范流程

1. 新文档放入 `brain/docs/`（首行写 `TITLE: 标题`）
2. 运行 `python3 brain/build.py` 重建索引
3. 提交时确保 `brain/kb.json` 同步更新
4. 再执行第 3 条的镜像同步

## 禁忌

- 不要往镜像仓库直接推开发分支
- 不要私自删除文档（需先备份移动）
- 不要修改镜像 remote URL 中的凭据（令牌需向用户确认后轮换）
- 不要在聊天或代码中明文暴露令牌

## 新增入口工具后

1. 写清用法到模块 README
2. 更新本文件"模块职责"表
3. 提交 + 镜像同步

## 换新 AI 接手的检查清单

- [ ] `git pull origin master`
- [ ] 确认 `phoneconv/conv.py gttx.py install.sh fetch_all.js` 存在
- [ ] 确认 `brain/build.py ask.py` 存在且 `python3 brain/ask.py "测试词"` 能检索
- [ ] 三平台镜像与 origin 同步（`git log origin/master..toolchain-github/master` 应为空）
