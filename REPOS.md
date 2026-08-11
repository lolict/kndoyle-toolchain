# REPOS - 仓库目的地图与边界规则

本文件是整套仓库网络的"说明书"。任何 AI 或人在往任一仓库推送前，
必须先读本文件，确认代码的**归属层**，避免对仓库造成冲击。

## 一、仓库总表（基于实际阅读 README/结构）

| 平台 | 仓库 | 目的 | 层级 |
|---|---|---|---|
| gitee | `lolict/kenandaoer` | **主开发仓库**：hunyuan CPU 验证链 + phoneconv 工具链 + 外置大脑 | 开发源 |
| gitee | `lolict/kndoyle-toolchain` | 工具链镜像（kenandaoer 子集同步） | 镜像 |
| github | `lolict/yuan-ji-jiu-can` | 满全法·夫妻共同体 OS（姓名即协议、灵犀协议 P2P、封神台、含 hunyuan-rs） | 核心 OS |
| github | `lolict/relational-algebra` | 主体间关系代数编程范式（认知隔离舱、漏斗编译、几何范畴论） | 编程范式 |
| github | `lolict/Unicore` | 自主统一指令集架构（UniISA、Zig 虚拟机、二进制翻译器） | 指令集 |
| github | `lolict/ddck` | 空仓库（未定内容） | 待定 |
| github | `lolict/mycode` | 私有/不可读（404），归属未知 | 未知 |
| github | `lolict/residual-aid` | 私有/不可读（404），描述为分布式算力调度 | 未知 |
| github | `lolict/kndoyle-toolchain` | 工具链镜像（github 侧） | 镜像 |
| gitcode | `lolict/kndoyle-toolchain` | 工具链镜像（gitcode 侧） | 镜像 |
| gitcode | `lolict/kndoyle-gtxt` | 已有仓库，README 为空 | 未知 |
| gitcode | `yuanji-jiucan/kndoyle-dict` | 柯南倒尔·字典 | 词库 |

## 二、体系结构（思想一体的三层）

```
核心 OS 层     yuan-ji-jiu-can (满全法/灵犀协议/封神台/hunyuan-rs)
                  │
编程范式层       relational-algebra (关系代数)  +  Unicore (自主指令集 UniISA)
                  │
工具链层        kenandaoer (hunyuan CPU + phoneconv + brain)
                  │
镜像层          kndoyle-toolchain × gitee/github/gitcode
```

**关键关联线**：`kenandaoer/cpu`（hunyuan CPU 验证链）与
`yuan-ji-jiu-can/hunyuan-rs`（Rust 实现）同属 hunyuan 体系——
同一思路在不同仓库的两端。任何一边的改动，另一边都应知晓。

## 三、边界规则（防冲击）

1. **未读必不推**：往任何仓库推送前，先读该仓库 README 与本文件。
   读不到（404/私有）的仓库视为未知，不推送。
2. **核心仓库慎动**：`yuan-ji-jiu-can`、`relational-algebra`、`Unicore`
   是核心创作，改动前必须读 ARCHITECTURE/PROTOCOL/SPEC，且确认作者意图。
3. **工具链只在固定两处**：phoneconv / brain / 协作文档只进
   `kenandaoer`（开发源）与 `kndoyle-toolchain`（镜像）。
4. **未知仓库不建不推**：ddck、mycode、residual-aid、kndoyle-gtxt
   目的未确认前，不往里面塞代码。
5. **每次推送自检**：这次代码属于哪个层？该层的仓库是哪个？读过了吗？

## 四、历史推送冲击审计

已完成的推送全部落在安全区：

- `kenandaoer`：本仓库（主开发源）—— CPU 验证链、phoneconv、brain、
  COLLAB.md、kndoyle-symbols.md 均属工具链/文档层，符合归属
- `kndoyle-toolchain`（gitee/github/gitcode 镜像）：仅同步 kenandaoer
  的工具链内容，未混入核心 OS 代码

**未触碰**任何核心创作仓库与未知仓库，无冲击。
